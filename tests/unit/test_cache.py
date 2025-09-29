"""Tests for the cache module"""

import asyncio
import json
import tempfile
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp

from pydhis2.core.cache import CacheEntry, HTTPCache, ResumableDownloader, CachedSession


class TestCacheEntry:
    """Test CacheEntry class"""
    
    def test_init(self):
        """Test cache entry initialization"""
        entry = CacheEntry(url="http://example.com")
        assert entry.url == "http://example.com"
        assert entry.etag is None
        assert entry.last_modified is None
        assert entry.content_length is None
        assert entry.timestamp == 0.0
        assert entry.data is None
        assert entry.file_path is None
    
    def test_init_with_data(self):
        """Test cache entry initialization with data"""
        entry = CacheEntry(
            url="http://example.com",
            etag="abc123",
            last_modified="Mon, 01 Jan 2024 00:00:00 GMT",
            content_length=1024,
            timestamp=1234567890.0,
            data={"key": "value"},
            file_path="/tmp/cache.json"
        )
        assert entry.url == "http://example.com"
        assert entry.etag == "abc123"
        assert entry.last_modified == "Mon, 01 Jan 2024 00:00:00 GMT"
        assert entry.content_length == 1024
        assert entry.timestamp == 1234567890.0
        assert entry.data == {"key": "value"}
        assert entry.file_path == "/tmp/cache.json"
    
    def test_is_expired_false(self):
        """Test is_expired returns False for fresh entry"""
        entry = CacheEntry(url="http://example.com", timestamp=time.time())
        assert not entry.is_expired(ttl=3600)
    
    def test_is_expired_true(self):
        """Test is_expired returns True for old entry"""
        entry = CacheEntry(url="http://example.com", timestamp=time.time() - 7200)
        assert entry.is_expired(ttl=3600)
    
    def test_to_dict(self):
        """Test to_dict conversion"""
        entry = CacheEntry(
            url="http://example.com",
            etag="abc123",
            last_modified="Mon, 01 Jan 2024 00:00:00 GMT",
            content_length=1024,
            timestamp=1234567890.0,
            file_path="/tmp/cache.json"
        )
        
        result = entry.to_dict()
        expected = {
            'url': "http://example.com",
            'etag': "abc123",
            'last_modified': "Mon, 01 Jan 2024 00:00:00 GMT",
            'content_length': 1024,
            'timestamp': 1234567890.0,
            'file_path': "/tmp/cache.json"
        }
        assert result == expected
    
    def test_from_dict(self):
        """Test from_dict creation"""
        data = {
            'url': "http://example.com",
            'etag': "abc123",
            'last_modified': "Mon, 01 Jan 2024 00:00:00 GMT",
            'content_length': 1024,
            'timestamp': 1234567890.0,
            'file_path': "/tmp/cache.json"
        }
        
        entry = CacheEntry.from_dict(data)
        assert entry.url == "http://example.com"
        assert entry.etag == "abc123"
        assert entry.last_modified == "Mon, 01 Jan 2024 00:00:00 GMT"
        assert entry.content_length == 1024
        assert entry.timestamp == 1234567890.0
        assert entry.file_path == "/tmp/cache.json"
    
    def test_from_dict_minimal(self):
        """Test from_dict with minimal data"""
        data = {'url': "http://example.com"}
        entry = CacheEntry.from_dict(data)
        assert entry.url == "http://example.com"
        assert entry.etag is None
        assert entry.timestamp == 0.0


class TestHTTPCache:
    """Test HTTPCache class"""
    
    def setup_method(self):
        """Setup test cache with temporary directory"""
        self.temp_dir = tempfile.mkdtemp()
        self.cache = HTTPCache(cache_dir=self.temp_dir, ttl=3600, max_size=5)
    
    def teardown_method(self):
        """Cleanup test cache"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_init(self):
        """Test cache initialization"""
        assert self.cache.cache_dir == Path(self.temp_dir)
        assert self.cache.ttl == 3600
        assert self.cache.max_size == 5
        assert self.cache._memory_cache == {}
        assert self.cache.index_file == Path(self.temp_dir) / "cache_index.json"
    
    def test_get_cache_key_simple(self):
        """Test cache key generation without parameters"""
        url = "http://example.com/api/test"
        key = self.cache._get_cache_key(url)
        assert isinstance(key, str)
        assert len(key) == 32  # MD5 hash length
    
    def test_get_cache_key_with_params(self):
        """Test cache key generation with parameters"""
        url = "http://example.com/api/test"
        params = {"param1": "value1", "param2": "value2"}
        key = self.cache._get_cache_key(url, params)
        assert isinstance(key, str)
        assert len(key) == 32
    
    def test_get_file_path(self):
        """Test file path generation"""
        cache_key = "abc123"
        file_path = self.cache._get_file_path(cache_key)
        expected = Path(self.temp_dir) / "abc123.json"
        assert file_path == expected
    
    async def test_get_cache_miss(self):
        """Test cache get with no cached entry"""
        result = await self.cache.get("http://example.com")
        assert result is None
    
    async def test_set_and_get_memory_cache(self):
        """Test setting and getting from memory cache"""
        url = "http://example.com"
        data = {"test": "data"}
        
        await self.cache.set(url, data, use_file_cache=False)
        
        result = await self.cache.get(url)
        assert result is not None
        assert result.url == url
        assert result.data == data
    
    async def test_set_and_get_file_cache(self):
        """Test setting and getting from file cache"""
        url = "http://example.com"
        data = {"test": "data"}
        etag = "abc123"
        last_modified = "Mon, 01 Jan 2024 00:00:00 GMT"
        
        await self.cache.set(url, data, etag=etag, last_modified=last_modified)
        
        result = await self.cache.get(url)
        assert result is not None
        assert result.url == url
        assert result.etag == etag
        assert result.last_modified == last_modified
        assert result.data == data
    
    async def test_cache_expiration(self):
        """Test cache entry expiration"""
        # Create cache with very short TTL
        short_cache = HTTPCache(cache_dir=self.temp_dir, ttl=1)
        
        url = "http://example.com"
        data = {"test": "data"}
        
        await short_cache.set(url, data, use_file_cache=False)
        
        # Immediately should be available
        result = await short_cache.get(url)
        assert result is not None
        
        # Wait for expiration
        await asyncio.sleep(1.1)
        
        # Should be expired now
        result = await short_cache.get(url)
        assert result is None
    
    async def test_cache_size_limit(self):
        """Test cache size limitation"""
        # Fill cache to max size
        for i in range(self.cache.max_size):
            url = f"http://example.com/{i}"
            data = {"index": i}
            await self.cache.set(url, data, use_file_cache=False)
        
        assert len(self.cache._memory_cache) == self.cache.max_size
        
        # Add one more entry, should evict oldest
        url = f"http://example.com/{self.cache.max_size}"
        data = {"index": self.cache.max_size}
        await self.cache.set(url, data, use_file_cache=False)
        
        assert len(self.cache._memory_cache) == self.cache.max_size
        
        # First entry should be evicted
        result = await self.cache.get("http://example.com/0")
        assert result is None
    
    def test_get_conditional_headers_no_cache(self):
        """Test conditional headers with no cached entry"""
        headers = self.cache.get_conditional_headers("http://example.com")
        assert headers == {}
    
    async def test_get_conditional_headers_with_etag(self):
        """Test conditional headers with ETag"""
        url = "http://example.com"
        data = {"test": "data"}
        etag = "abc123"
        
        await self.cache.set(url, data, etag=etag, use_file_cache=False)
        
        headers = self.cache.get_conditional_headers(url)
        assert headers == {'If-None-Match': etag}
    
    async def test_get_conditional_headers_with_last_modified(self):
        """Test conditional headers with Last-Modified"""
        url = "http://example.com"
        data = {"test": "data"}
        last_modified = "Mon, 01 Jan 2024 00:00:00 GMT"
        
        await self.cache.set(url, data, last_modified=last_modified, use_file_cache=False)
        
        headers = self.cache.get_conditional_headers(url)
        assert headers == {'If-Modified-Since': last_modified}
    
    async def test_get_conditional_headers_with_both(self):
        """Test conditional headers with both ETag and Last-Modified"""
        url = "http://example.com"
        data = {"test": "data"}
        etag = "abc123"
        last_modified = "Mon, 01 Jan 2024 00:00:00 GMT"
        
        await self.cache.set(url, data, etag=etag, last_modified=last_modified, use_file_cache=False)
        
        headers = self.cache.get_conditional_headers(url)
        assert headers == {
            'If-None-Match': etag,
            'If-Modified-Since': last_modified
        }
    
    async def test_clear_cache(self):
        """Test cache clearing"""
        # Add some entries
        for i in range(3):
            url = f"http://example.com/{i}"
            data = {"index": i}
            await self.cache.set(url, data, use_file_cache=False)
        
        assert len(self.cache._memory_cache) == 3
        
        await self.cache.clear()
        
        assert len(self.cache._memory_cache) == 0
        assert not self.cache.index_file.exists()
    
    @patch('pydhis2.core.cache.logger')
    async def test_load_cache_index_error(self, mock_logger):
        """Test loading cache index with error"""
        # Create invalid JSON file
        with open(self.cache.index_file, 'w') as f:
            f.write("invalid json")
        
        HTTPCache(cache_dir=self.temp_dir)
        
        mock_logger.warning.assert_called_once()
        assert "Failed to load cache index" in mock_logger.warning.call_args[0][0]
    
    @patch('pydhis2.core.cache.logger')
    async def test_save_cache_index_error(self, mock_logger):
        """Test saving cache index with error"""
        # Make cache directory read-only to trigger error
        with patch('builtins.open', side_effect=PermissionError("Permission denied")):
            self.cache._save_cache_index()
        
        mock_logger.warning.assert_called_once()
        assert "Failed to save cache index" in mock_logger.warning.call_args[0][0]


class TestResumableDownloader:
    """Test ResumableDownloader class"""
    
    def setup_method(self):
        """Setup test downloader"""
        self.session = MagicMock(spec=aiohttp.ClientSession)
        self.downloader = ResumableDownloader(self.session)
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """Cleanup test files"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    async def test_download_success(self):
        """Test successful download"""
        # Mock response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.headers = {'Content-Length': '100'}
        
        async def mock_iter_chunked(chunk_size):
            yield b'test data chunk'
        
        mock_response.content.iter_chunked = mock_iter_chunked
        
        # Create proper async context manager
        mock_context = AsyncMock()
        mock_context.__aenter__.return_value = mock_response
        mock_context.__aexit__.return_value = None
        self.session.get.return_value = mock_context
        
        file_path = Path(self.temp_dir) / "test_file.txt"
        
        # Mock aiofiles.open properly
        mock_file = AsyncMock()
        mock_file_context = AsyncMock()
        mock_file_context.__aenter__.return_value = mock_file
        mock_file_context.__aexit__.return_value = None
        
        with patch('aiofiles.open', return_value=mock_file_context), \
             patch.object(Path, 'rename') as mock_rename:
            result = await self.downloader.download("http://example.com/file", file_path)
        
        assert result is True
        self.session.get.assert_called_once()
        mock_rename.assert_called_once()
    
    async def test_download_with_resume(self):
        """Test download with resume capability"""
        file_path = Path(self.temp_dir) / "test_file.txt"
        temp_path = file_path.with_suffix(file_path.suffix + '.tmp')
        
        # Create partial file
        temp_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path.write_bytes(b'partial')
        
        # Mock response for partial content
        mock_response = AsyncMock()
        mock_response.status = 206
        mock_response.headers = {
            'Content-Length': '50',
            'Content-Range': 'bytes 7-56/57'
        }
        
        async def mock_iter_chunked(chunk_size):
            yield b' remaining data'
        
        mock_response.content.iter_chunked = mock_iter_chunked
        
        # Create proper async context manager
        mock_context = AsyncMock()
        mock_context.__aenter__.return_value = mock_response
        mock_context.__aexit__.return_value = None
        self.session.get.return_value = mock_context
        
        # Mock aiofiles.open properly
        mock_file = AsyncMock()
        mock_file_context = AsyncMock()
        mock_file_context.__aenter__.return_value = mock_file
        mock_file_context.__aexit__.return_value = None
        
        with patch('aiofiles.open', return_value=mock_file_context):
            result = await self.downloader.download("http://example.com/file", file_path, resume=True)
        
        assert result is True
        # Should request with Range header
        call_args = self.session.get.call_args
        assert 'headers' in call_args[1]
        assert 'Range' in call_args[1]['headers']
    
    async def test_download_range_not_satisfiable(self):
        """Test download when range request is not satisfiable"""
        file_path = Path(self.temp_dir) / "test_file.txt"
        temp_path = file_path.with_suffix(file_path.suffix + '.tmp')
        
        # Create partial file
        temp_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path.write_bytes(b'complete file content')
        
        # Mock 416 response
        mock_response = AsyncMock()
        mock_response.status = 416
        
        self.session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        self.session.get.return_value.__aexit__ = AsyncMock(return_value=None)
        
        result = await self.downloader.download("http://example.com/file", file_path, resume=True)
        
        assert result is True
        assert file_path.exists()
    
    async def test_download_error_status(self):
        """Test download with error status"""
        mock_response = AsyncMock()
        mock_response.status = 404
        
        self.session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        self.session.get.return_value.__aexit__ = AsyncMock(return_value=None)
        
        file_path = Path(self.temp_dir) / "test_file.txt"
        
        with patch('pydhis2.core.cache.logger') as mock_logger:
            result = await self.downloader.download("http://example.com/file", file_path)
        
        assert result is False
        mock_logger.error.assert_called_once()
    
    async def test_download_exception(self):
        """Test download with exception"""
        self.session.get.side_effect = Exception("Network error")
        
        file_path = Path(self.temp_dir) / "test_file.txt"
        
        with patch('pydhis2.core.cache.logger') as mock_logger:
            result = await self.downloader.download("http://example.com/file", file_path)
        
        assert result is False
        mock_logger.error.assert_called_once()
    
    async def test_download_with_progress_callback(self):
        """Test download with progress callback"""
        progress_calls = []
        
        def progress_callback(downloaded, total):
            progress_calls.append((downloaded, total))
        
        # Mock response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.headers = {'Content-Length': '20'}
        
        async def mock_iter_chunked(chunk_size):
            yield b'chunk1'
            yield b'chunk2'
        
        mock_response.content.iter_chunked = mock_iter_chunked
        
        # Create proper async context manager
        mock_context = AsyncMock()
        mock_context.__aenter__.return_value = mock_response
        mock_context.__aexit__.return_value = None
        self.session.get.return_value = mock_context
        
        file_path = Path(self.temp_dir) / "test_file.txt"
        
        # Mock aiofiles.open properly
        mock_file = AsyncMock()
        mock_file_context = AsyncMock()
        mock_file_context.__aenter__.return_value = mock_file
        mock_file_context.__aexit__.return_value = None
        
        with patch('aiofiles.open', return_value=mock_file_context), \
             patch.object(Path, 'rename') as mock_rename:
            result = await self.downloader.download(
                "http://example.com/file", 
                file_path, 
                progress_callback=progress_callback
            )
        
        assert result is True
        assert len(progress_calls) == 2  # One call per chunk
        mock_rename.assert_called_once()


class TestCachedSession:
    """Test CachedSession class"""
    
    def setup_method(self):
        """Setup test session"""
        self.session = MagicMock(spec=aiohttp.ClientSession)
        self.temp_dir = tempfile.mkdtemp()
        self.cache = HTTPCache(cache_dir=self.temp_dir, ttl=3600)
        self.cached_session = CachedSession(
            session=self.session,
            cache=self.cache,
            enable_cache=True
        )
    
    def teardown_method(self):
        """Cleanup test files"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_init(self):
        """Test cached session initialization"""
        assert self.cached_session.session == self.session
        assert self.cached_session.cache == self.cache
        assert self.cached_session.enable_cache is True
        assert self.cached_session.use_etag is True
        assert self.cached_session.use_last_modified is True
        assert isinstance(self.cached_session.downloader, ResumableDownloader)
    
    def test_init_with_default_cache(self):
        """Test initialization with default cache"""
        session = CachedSession(self.session)
        assert isinstance(session.cache, HTTPCache)
    
    async def test_get_without_cache(self):
        """Test GET request without cache"""
        cached_session = CachedSession(self.session, enable_cache=False)
        
        mock_response = AsyncMock()
        
        # Mock session.get as async function
        async def mock_get(*args, **kwargs):
            return mock_response
        
        self.session.get = mock_get
        
        result = await cached_session.get("http://example.com")
        
        assert result == mock_response
    
    async def test_get_cache_disabled_for_request(self):
        """Test GET request with cache disabled for specific request"""
        mock_response = AsyncMock()
        
        # Mock session.get as async function
        async def mock_get(*args, **kwargs):
            return mock_response
        
        self.session.get = mock_get
        
        result = await self.cached_session.get("http://example.com", use_cache=False)
        
        assert result == mock_response
    
    async def test_get_cache_miss(self):
        """Test GET request with cache miss"""
        url = "http://example.com"
        
        # Mock successful response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.headers = {'ETag': 'abc123'}
        
        async def mock_json():
            return {"data": "test"}
        
        mock_response.json = mock_json
        
        # Mock session.get as async function
        async def mock_get(*args, **kwargs):
            return mock_response
        
        self.session.get = mock_get
        
        result = await self.cached_session.get(url)
        
        assert result == mock_response
        
        # Check that response was cached
        cached_entry = await self.cache.get(url)
        assert cached_entry is not None
        assert cached_entry.etag == "abc123"
    
    async def test_get_cache_hit_304(self):
        """Test GET request with 304 Not Modified response"""
        url = "http://example.com"
        
        # First, cache a response
        await self.cache.set(url, {"data": "cached"}, etag="abc123")
        
        # Mock 304 response
        mock_response = AsyncMock()
        mock_response.status = 304
        
        # Track call arguments
        call_args_list = []
        
        async def mock_get(*args, **kwargs):
            call_args_list.append((args, kwargs))
            return mock_response
        
        self.session.get = mock_get
        
        result = await self.cached_session.get(url)
        
        assert result == mock_response
        # Should have sent conditional headers
        assert len(call_args_list) == 1
        _, kwargs = call_args_list[0]
        assert 'headers' in kwargs
        assert 'If-None-Match' in kwargs['headers']
    
    async def test_download_file(self):
        """Test file download delegation"""
        file_path = Path(self.temp_dir) / "test.txt"
        
        with patch.object(self.cached_session.downloader, 'download', return_value=True) as mock_download:
            result = await self.cached_session.download_file("http://example.com/file", file_path)
        
        assert result is True
        mock_download.assert_called_once_with(
            url="http://example.com/file",
            file_path=file_path,
            resume=True,
            progress_callback=None
        )
    
    async def test_clear_cache(self):
        """Test cache clearing delegation"""
        with patch.object(self.cache, 'clear') as mock_clear:
            await self.cached_session.clear_cache()
        
        mock_clear.assert_called_once()
    
    @patch('pydhis2.core.cache.logger')
    async def test_cache_response_json_error(self, mock_logger):
        """Test caching response with JSON parsing error"""
        url = "http://example.com"
        
        # Mock response that fails to parse JSON
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.headers = {'ETag': 'abc123'}
        
        async def mock_json():
            raise json.JSONDecodeError("Invalid JSON", "", 0)
        
        mock_response.json = mock_json
        
        # Mock session.get as async function
        async def mock_get(*args, **kwargs):
            return mock_response
        
        self.session.get = mock_get
        
        result = await self.cached_session.get(url)
        
        assert result == mock_response
        mock_logger.warning.assert_called_once()
        assert "Failed to cache response" in mock_logger.warning.call_args[0][0]

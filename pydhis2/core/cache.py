"""Cache module - Support for ETag/Last-Modified caching and resumable downloads"""

import asyncio
import hashlib
import json
import time
from pathlib import Path
from typing import Any, Dict, Optional, Union
from urllib.parse import urlparse, urlencode
import aiofiles
import aiohttp
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Cache entry"""
    url: str
    etag: Optional[str] = None
    last_modified: Optional[str] = None
    content_length: Optional[int] = None
    timestamp: float = 0.0
    data: Optional[Dict[str, Any]] = None
    file_path: Optional[str] = None
    
    def is_expired(self, ttl: int) -> bool:
        """Check if expired"""
        return (time.time() - self.timestamp) > ttl
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'url': self.url,
            'etag': self.etag,
            'last_modified': self.last_modified,
            'content_length': self.content_length,
            'timestamp': self.timestamp,
            'file_path': self.file_path,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CacheEntry':
        """Create from dictionary"""
        return cls(
            url=data['url'],
            etag=data.get('etag'),
            last_modified=data.get('last_modified'),
            content_length=data.get('content_length'),
            timestamp=data.get('timestamp', 0.0),
            file_path=data.get('file_path'),
        )


class HTTPCache:
    """HTTP cache manager"""
    
    def __init__(
        self,
        cache_dir: Union[str, Path] = ".pydhis2_cache",
        ttl: int = 3600,  # Default 1 hour TTL
        max_size: int = 100,  # Maximum number of cache entries
    ):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.ttl = ttl
        self.max_size = max_size
        
        # In-memory cache
        self._memory_cache: Dict[str, CacheEntry] = {}
        
        # Cache index file
        self.index_file = self.cache_dir / "cache_index.json"
        
        # Load existing cache
        self._load_cache_index()
    
    def _load_cache_index(self) -> None:
        """Load cache index"""
        if self.index_file.exists():
            try:
                with open(self.index_file, 'r', encoding='utf-8') as f:
                    index_data = json.load(f)
                
                for url, entry_data in index_data.items():
                    entry = CacheEntry.from_dict(entry_data)
                    if not entry.is_expired(self.ttl):
                        self._memory_cache[url] = entry
                    else:
                        # Clean up expired files
                        if entry.file_path and Path(entry.file_path).exists():
                            Path(entry.file_path).unlink()
                            
            except Exception as e:
                logger.warning(f"Failed to load cache index: {e}")
    
    def _save_cache_index(self) -> None:
        """Save cache index"""
        try:
            index_data = {
                url: entry.to_dict()
                for url, entry in self._memory_cache.items()
                if not entry.is_expired(self.ttl)
            }
            
            with open(self.index_file, 'w', encoding='utf-8') as f:
                json.dump(index_data, f, indent=2)
                
        except Exception as e:
            logger.warning(f"Failed to save cache index: {e}")
    
    def _get_cache_key(self, url: str, params: Optional[Dict[str, Any]] = None) -> str:
        """Generate cache key"""
        if params:
            # Add parameters to the URL
            url_parts = urlparse(url)
            query = urlencode(params, safe='')
            if url_parts.query:
                query = f"{url_parts.query}&{query}"
            full_url = f"{url_parts.scheme}://{url_parts.netloc}{url_parts.path}?{query}"
        else:
            full_url = url
        
        # Use MD5 of the URL as the cache key
        return hashlib.md5(full_url.encode()).hexdigest()
    
    def _get_file_path(self, cache_key: str) -> Path:
        """Get cache file path"""
        return self.cache_dir / f"{cache_key}.json"
    
    async def get(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Optional[CacheEntry]:
        """Get a cache entry"""
        cache_key = self._get_cache_key(url, params)
        
        # Check in-memory cache
        if cache_key in self._memory_cache:
            entry = self._memory_cache[cache_key]
            if not entry.is_expired(self.ttl):
                # If it's a file cache, load the data
                if entry.file_path and Path(entry.file_path).exists():
                    try:
                        async with aiofiles.open(entry.file_path, 'r', encoding='utf-8') as f:
                            content = await f.read()
                            entry.data = json.loads(content)
                    except Exception as e:
                        logger.warning(f"Failed to load cached file {entry.file_path}: {e}")
                        return None
                
                return entry
            else:
                # Clean up expired entry
                del self._memory_cache[cache_key]
                if entry.file_path and Path(entry.file_path).exists():
                    Path(entry.file_path).unlink()
        
        return None
    
    async def set(
        self,
        url: str,
        data: Dict[str, Any],
        etag: Optional[str] = None,
        last_modified: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
        use_file_cache: bool = True,
    ) -> None:
        """Set a cache entry"""
        cache_key = self._get_cache_key(url, params)
        
        # Limit cache size
        if len(self._memory_cache) >= self.max_size:
            # Delete the oldest entry
            oldest_key = min(
                self._memory_cache.keys(),
                key=lambda k: self._memory_cache[k].timestamp
            )
            old_entry = self._memory_cache.pop(oldest_key)
            if old_entry.file_path and Path(old_entry.file_path).exists():
                Path(old_entry.file_path).unlink()
        
        entry = CacheEntry(
            url=url,
            etag=etag,
            last_modified=last_modified,
            timestamp=time.time(),
        )
        
        if use_file_cache:
            # Save to file
            file_path = self._get_file_path(cache_key)
            try:
                async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
                    await f.write(json.dumps(data, ensure_ascii=False, indent=2))
                entry.file_path = str(file_path)
            except Exception as e:
                logger.warning(f"Failed to save cache file: {e}")
                entry.data = data
        else:
            # Save to memory
            entry.data = data
        
        self._memory_cache[cache_key] = entry
        self._save_cache_index()
    
    def get_conditional_headers(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, str]:
        """Get conditional request headers"""
        cache_key = self._get_cache_key(url, params)
        headers = {}
        
        if cache_key in self._memory_cache:
            entry = self._memory_cache[cache_key]
            if entry.etag:
                headers['If-None-Match'] = entry.etag
            if entry.last_modified:
                headers['If-Modified-Since'] = entry.last_modified
        
        return headers
    
    async def clear(self) -> None:
        """Clear the cache"""
        for entry in self._memory_cache.values():
            if entry.file_path and Path(entry.file_path).exists():
                Path(entry.file_path).unlink()
        
        self._memory_cache.clear()
        
        if self.index_file.exists():
            self.index_file.unlink()


class ResumableDownloader:
    """Resumable downloader"""
    
    def __init__(self, session: aiohttp.ClientSession):
        self.session = session
    
    async def download(
        self,
        url: str,
        file_path: Union[str, Path],
        chunk_size: int = 8192,
        resume: bool = True,
        progress_callback: Optional[callable] = None,
    ) -> bool:
        """Download a file with resumable support"""
        file_path = Path(file_path)
        temp_path = file_path.with_suffix(file_path.suffix + '.tmp')
        
        # Check if resume is supported
        start_byte = 0
        if resume and temp_path.exists():
            start_byte = temp_path.stat().st_size
        
        headers = {}
        if start_byte > 0:
            headers['Range'] = f'bytes={start_byte}-'
        
        try:
            async with self.session.get(url, headers=headers) as response:
                # Check status code
                if start_byte > 0 and response.status == 416:
                    # Range request not satisfiable, file may be complete
                    if temp_path.exists():
                        temp_path.rename(file_path)
                    return True
                
                if response.status not in [200, 206]:
                    logger.error(f"Download failed with status {response.status}")
                    return False
                
                # Get total file size
                content_length = None
                if 'Content-Length' in response.headers:
                    content_length = int(response.headers['Content-Length'])
                
                if response.status == 206:  # Partial content
                    content_range = response.headers.get('Content-Range', '')
                    if content_range.startswith('bytes '):
                        # Parse "bytes start-end/total"
                        range_part = content_range[6:]  # remove "bytes "
                        if '/' in range_part:
                            total_size = int(range_part.split('/')[-1])
                            content_length = total_size - start_byte
                
                total_size = (content_length + start_byte) if content_length else None
                downloaded = start_byte
                
                # Ensure directory exists
                file_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Write to file
                mode = 'ab' if start_byte > 0 else 'wb'
                async with aiofiles.open(temp_path, mode) as f:
                    async for chunk in response.content.iter_chunked(chunk_size):
                        await f.write(chunk)
                        downloaded += len(chunk)
                        
                        if progress_callback:
                            progress_callback(downloaded, total_size)
                
                # Download complete, rename file
                temp_path.rename(file_path)
                
                logger.info(f"Download completed: {file_path}")
                return True
                
        except Exception as e:
            logger.error(f"Download failed: {e}")
            return False


class CachedSession:
    """HTTP session with caching"""
    
    def __init__(
        self,
        session: aiohttp.ClientSession,
        cache: Optional[HTTPCache] = None,
        enable_cache: bool = True,
        use_etag: bool = True,
        use_last_modified: bool = True,
    ):
        self.session = session
        self.cache = cache or HTTPCache()
        self.enable_cache = enable_cache
        self.use_etag = use_etag
        self.use_last_modified = use_last_modified
        
        # Resumable downloader
        self.downloader = ResumableDownloader(session)
    
    async def get(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        use_cache: bool = True,
        **kwargs
    ) -> aiohttp.ClientResponse:
        """GET request with cache support"""
        if not self.enable_cache or not use_cache:
            return await self.session.get(url, params=params, **kwargs)
        
        # Check cache
        cached_entry = await self.cache.get(url, params)
        
        # Prepare conditional request headers
        headers = kwargs.get('headers', {}).copy()
        if self.use_etag or self.use_last_modified:
            conditional_headers = self.cache.get_conditional_headers(url, params)
            headers.update(conditional_headers)
        
        kwargs['headers'] = headers
        
        # Make the request
        response = await self.session.get(url, params=params, **kwargs)
        
        # Handle 304 Not Modified
        if response.status == 304 and cached_entry:
            logger.debug(f"Cache hit (304): {url}")
            # Create a mock response
            # Note: This is a simplified handling, real applications may need more complex response mocking
            return response
        
        # Check if response should be cached
        if response.status == 200:
            try:
                data = await response.json()
                
                # Extract cache-related headers
                etag = response.headers.get('ETag') if self.use_etag else None
                last_modified = response.headers.get('Last-Modified') if self.use_last_modified else None
                
                # Save to cache
                await self.cache.set(
                    url=url,
                    data=data,
                    etag=etag,
                    last_modified=last_modified,
                    params=params,
                )
                
                logger.debug(f"Cached response: {url}")
                
            except Exception as e:
                logger.warning(f"Failed to cache response: {e}")
        
        return response
    
    async def download_file(
        self,
        url: str,
        file_path: Union[str, Path],
        resume: bool = True,
        progress_callback: Optional[callable] = None,
        **kwargs
    ) -> bool:
        """Download file with resumable support"""
        return await self.downloader.download(
            url=url,
            file_path=file_path,
            resume=resume,
            progress_callback=progress_callback,
        )
    
    async def clear_cache(self) -> None:
        """Clear the cache"""
        await self.cache.clear()

"""Structured logging configuration"""

import logging
import json
import sys
from typing import Any, Dict, Optional
from datetime import datetime


class StructuredFormatter(logging.Formatter):
    """Structured log formatter"""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        log_data = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        
        # Add exception information
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        # Add extra fields
        if hasattr(record, 'extra_fields'):
            log_data.update(record.extra_fields)
        
        return json.dumps(log_data, ensure_ascii=False)


class SensitiveDataFilter(logging.Filter):
    """Sensitive data filter"""
    
    SENSITIVE_PATTERNS = [
        'password', 'token', 'key', 'secret', 'auth', 'credential'
    ]
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Filter sensitive data"""
        message = record.getMessage().lower()
        
        # Check if contains sensitive keywords
        for pattern in self.SENSITIVE_PATTERNS:
            if pattern in message:
                # Replace sensitive information
                record.msg = record.msg.replace(
                    str(record.args) if record.args else '',
                    '[REDACTED]'
                )
                break
        
        return True


def setup_logging(
    level: str = "INFO",
    structured: bool = True,
    filter_sensitive: bool = True,
    log_file: Optional[str] = None
) -> None:
    """Setup logging configuration"""
    
    # 设置日志级别
    log_level = getattr(logging, level.upper(), logging.INFO)
    
    # 创建根日志器
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # 清除现有处理器
    root_logger.handlers.clear()
    
    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    
    if structured:
        console_handler.setFormatter(StructuredFormatter())
    else:
        console_handler.setFormatter(
            logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
        )
    
    if filter_sensitive:
        console_handler.addFilter(SensitiveDataFilter())
    
    root_logger.addHandler(console_handler)
    
    # 文件处理器（如果指定）
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(log_level)
        file_handler.setFormatter(StructuredFormatter())
        
        if filter_sensitive:
            file_handler.addFilter(SensitiveDataFilter())
        
        root_logger.addHandler(file_handler)
    
    # 第三方库日志级别
    logging.getLogger('aiohttp').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)


def get_logger(name: str, **extra_fields) -> logging.Logger:
    """获取带额外字段的日志器"""
    logger = logging.getLogger(name)
    
    # 创建适配器来添加额外字段
    class ExtraFieldsAdapter(logging.LoggerAdapter):
        def process(self, msg, kwargs):
            # 合并额外字段
            if 'extra' not in kwargs:
                kwargs['extra'] = {}
            kwargs['extra']['extra_fields'] = {**extra_fields, **kwargs['extra'].get('extra_fields', {})}
            return msg, kwargs
    
    return ExtraFieldsAdapter(logger, extra_fields)


# 便利函数
def log_request(logger: logging.Logger, method: str, url: str, status: Optional[int] = None, **kwargs):
    """记录HTTP请求"""
    extra_fields = {
        'http_method': method,
        'http_url': url,
        'event_type': 'http_request'
    }
    
    if status:
        extra_fields['http_status'] = status
    
    extra_fields.update(kwargs)
    
    logger.info(
        f"{method} {url}" + (f" -> {status}" if status else ""),
        extra={'extra_fields': extra_fields}
    )


def log_retry(logger: logging.Logger, attempt: int, max_attempts: int, delay: float, **kwargs):
    """记录重试"""
    extra_fields = {
        'retry_attempt': attempt,
        'retry_max_attempts': max_attempts,
        'retry_delay': delay,
        'event_type': 'retry'
    }
    
    extra_fields.update(kwargs)
    
    logger.warning(
        f"Retry attempt {attempt}/{max_attempts}, waiting {delay}s",
        extra={'extra_fields': extra_fields}
    )


def log_rate_limit(logger: logging.Logger, current_rate: float, limit: float, wait_time: float, **kwargs):
    """记录限流"""
    extra_fields = {
        'rate_current': current_rate,
        'rate_limit': limit,
        'rate_wait_time': wait_time,
        'event_type': 'rate_limit'
    }
    
    extra_fields.update(kwargs)
    
    logger.info(
        f"Rate limited: {current_rate:.2f}/{limit:.2f} rps, waiting {wait_time:.2f}s",
        extra={'extra_fields': extra_fields}
    )

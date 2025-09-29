"""OpenTelemetry integration module"""

from typing import Optional
from contextlib import contextmanager
import logging

logger = logging.getLogger(__name__)

# OpenTelemetry components
try:
    from opentelemetry import trace, metrics
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
    from opentelemetry.sdk.metrics.export import ConsoleMetricExporter, PeriodicExportingMetricReader
    from opentelemetry.exporter.jaeger.thrift import JaegerExporter
    from opentelemetry.exporter.prometheus import PrometheusMetricReader
    from opentelemetry.instrumentation.aiohttp_client import AioHttpClientInstrumentor
    from opentelemetry.trace.status import Status, StatusCode
    
    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False
    logger.info("OpenTelemetry not available. Install 'pydhis2[otel]' for telemetry support.")


class TelemetryManager:
    """Telemetry Manager"""
    
    def __init__(
        self,
        service_name: str = "pydhis2",
        service_version: str = "0.2.0",
        enable_traces: bool = True,
        enable_metrics: bool = True,
        jaeger_endpoint: Optional[str] = None,
        prometheus_port: Optional[int] = None,
    ):
        self.service_name = service_name
        self.service_version = service_version
        self.enable_traces = enable_traces and OTEL_AVAILABLE
        self.enable_metrics = enable_metrics and OTEL_AVAILABLE
        self.jaeger_endpoint = jaeger_endpoint
        self.prometheus_port = prometheus_port
        
        # Telemetry components
        self.tracer = None
        self.meter = None
        self._initialized = False
        
        # Metrics
        self._request_counter = None
        self._request_duration = None
        self._retry_counter = None
        self._rate_limit_counter = None
        
        if OTEL_AVAILABLE:
            self._setup_telemetry()
    
    def _setup_telemetry(self) -> None:
        """Set up telemetry"""
        try:
            # Set up tracing
            if self.enable_traces:
                self._setup_tracing()
            
            # Set up metrics
            if self.enable_metrics:
                self._setup_metrics()
            
            # Auto-instrumentation
            self._setup_auto_instrumentation()
            
            self._initialized = True
            logger.info("Telemetry initialized successfully")
            
        except Exception as e:
            logger.warning(f"Failed to initialize telemetry: {e}")
    
    def _setup_tracing(self) -> None:
        """Set up tracing"""
        # Create TracerProvider
        tracer_provider = TracerProvider(
            resource=self._create_resource()
        )
        
        # Add exporters
        if self.jaeger_endpoint:
            # Jaeger exporter
            jaeger_exporter = JaegerExporter(
                agent_host_name="localhost",
                agent_port=14268,
                collector_endpoint=self.jaeger_endpoint,
            )
            span_processor = BatchSpanProcessor(jaeger_exporter)
        else:
            # Console exporter (for development)
            console_exporter = ConsoleSpanExporter()
            span_processor = BatchSpanProcessor(console_exporter)
        
        tracer_provider.add_span_processor(span_processor)
        
        # Set global TracerProvider
        trace.set_tracer_provider(tracer_provider)
        
        # Get tracer
        self.tracer = trace.get_tracer(
            self.service_name,
            self.service_version
        )
    
    def _setup_metrics(self) -> None:
        """Set up metrics"""
        # Create exporters
        metric_readers = []
        
        if self.prometheus_port:
            # Prometheus exporter
            prometheus_reader = PrometheusMetricReader(port=self.prometheus_port)
            metric_readers.append(prometheus_reader)
        else:
            # Console exporter (for development)
            console_reader = PeriodicExportingMetricReader(
                ConsoleMetricExporter(),
                export_interval_millis=30000,  # 30 seconds
            )
            metric_readers.append(console_reader)
        
        # Create MeterProvider
        meter_provider = MeterProvider(
            resource=self._create_resource(),
            metric_readers=metric_readers
        )
        
        # Set global MeterProvider
        metrics.set_meter_provider(meter_provider)
        
        # Get meter
        self.meter = metrics.get_meter(
            self.service_name,
            self.service_version
        )
        
        # Create metrics
        self._create_metrics()
    
    def _create_resource(self):
        """Create a resource"""
        from opentelemetry.sdk.resources import Resource
        
        return Resource.create({
            "service.name": self.service_name,
            "service.version": self.service_version,
        })
    
    def _create_metrics(self) -> None:
        """Create metrics"""
        if not self.meter:
            return
        
        # HTTP request counter
        self._request_counter = self.meter.create_counter(
            name="pydhis2_http_requests_total",
            description="Total number of HTTP requests",
            unit="1"
        )
        
        # HTTP request duration
        self._request_duration = self.meter.create_histogram(
            name="pydhis2_http_request_duration_seconds",
            description="HTTP request duration in seconds",
            unit="s"
        )
        
        # Retry counter
        self._retry_counter = self.meter.create_counter(
            name="pydhis2_retries_total",
            description="Total number of retries",
            unit="1"
        )
        
        # Rate limit counter
        self._rate_limit_counter = self.meter.create_counter(
            name="pydhis2_rate_limits_total",
            description="Total number of rate limits hit",
            unit="1"
        )
    
    def _setup_auto_instrumentation(self) -> None:
        """Set up auto-instrumentation"""
        try:
            # Instrument aiohttp client
            AioHttpClientInstrumentor().instrument()
        except Exception as e:
            logger.warning(f"Failed to setup auto instrumentation: {e}")
    
    @contextmanager
    def trace_operation(self, operation_name: str, **attributes):
        """Trace operation context manager"""
        if not self.tracer:
            yield None
            return
        
        with self.tracer.start_as_current_span(operation_name) as span:
            # Add attributes
            for key, value in attributes.items():
                span.set_attribute(key, value)
            
            try:
                yield span
                span.set_status(Status(StatusCode.OK))
            except Exception as e:
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.record_exception(e)
                raise
    
    def record_http_request(
        self,
        method: str,
        url: str,
        status_code: int,
        duration: float,
        **labels
    ) -> None:
        """Record HTTP request metrics"""
        if not self._initialized:
            return
        
        try:
            # Prepare labels
            request_labels = {
                "method": method,
                "status_code": str(status_code),
                **labels
            }
            
            # Record counter
            if self._request_counter:
                self._request_counter.add(1, request_labels)
            
            # Record duration
            if self._request_duration:
                self._request_duration.record(duration, request_labels)
                
        except Exception as e:
            logger.warning(f"Failed to record HTTP request metrics: {e}")
    
    def record_retry(self, operation: str, attempt: int, **labels) -> None:
        """Record retry metrics"""
        if not self._retry_counter:
            return
        
        try:
            retry_labels = {
                "operation": operation,
                "attempt": str(attempt),
                **labels
            }
            self._retry_counter.add(1, retry_labels)
        except Exception as e:
            logger.warning(f"Failed to record retry metrics: {e}")
    
    def record_rate_limit(self, endpoint: str, **labels) -> None:
        """Record rate limit metrics"""
        if not self._rate_limit_counter:
            return
        
        try:
            rate_limit_labels = {
                "endpoint": endpoint,
                **labels
            }
            self._rate_limit_counter.add(1, rate_limit_labels)
        except Exception as e:
            logger.warning(f"Failed to record rate limit metrics: {e}")
    
    def is_enabled(self) -> bool:
        """Check if telemetry is enabled"""
        return self._initialized


# Global telemetry manager instance
_telemetry_manager: Optional[TelemetryManager] = None


def setup_telemetry(
    service_name: str = "pydhis2",
    service_version: str = "0.2.0",
    enable_traces: bool = True,
    enable_metrics: bool = True,
    jaeger_endpoint: Optional[str] = None,
    prometheus_port: Optional[int] = None,
) -> TelemetryManager:
    """Set up global telemetry"""
    global _telemetry_manager
    
    _telemetry_manager = TelemetryManager(
        service_name=service_name,
        service_version=service_version,
        enable_traces=enable_traces,
        enable_metrics=enable_metrics,
        jaeger_endpoint=jaeger_endpoint,
        prometheus_port=prometheus_port,
    )
    
    return _telemetry_manager


def get_telemetry() -> Optional[TelemetryManager]:
    """Get the global telemetry manager"""
    return _telemetry_manager


def trace_operation(operation_name: str, **attributes):
    """Decorator: trace an operation"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            if _telemetry_manager and _telemetry_manager.is_enabled():
                with _telemetry_manager.trace_operation(operation_name, **attributes):
                    return func(*args, **kwargs)
            else:
                return func(*args, **kwargs)
        return wrapper
    return decorator


def record_http_request(
    method: str,
    url: str,
    status_code: int,
    duration: float,
    **labels
) -> None:
    """Record an HTTP request"""
    if _telemetry_manager:
        _telemetry_manager.record_http_request(
            method=method,
            url=url,
            status_code=status_code,
            duration=duration,
            **labels
        )


def record_retry(operation: str, attempt: int, **labels) -> None:
    """Record a retry"""
    if _telemetry_manager:
        _telemetry_manager.record_retry(
            operation=operation,
            attempt=attempt,
            **labels
        )


def record_rate_limit(endpoint: str, **labels) -> None:
    """Record a rate limit event"""
    if _telemetry_manager:
        _telemetry_manager.record_rate_limit(endpoint=endpoint, **labels)


class TelemetryConfig:
    """Telemetry configuration"""
    
    def __init__(
        self,
        enable: bool = False,
        service_name: str = "pydhis2",
        service_version: str = "0.2.0",
        traces: bool = True,
        metrics: bool = True,
        jaeger_endpoint: Optional[str] = None,
        prometheus_port: Optional[int] = None,
    ):
        self.enable = enable
        self.service_name = service_name
        self.service_version = service_version
        self.traces = traces
        self.metrics = metrics
        self.jaeger_endpoint = jaeger_endpoint
        self.prometheus_port = prometheus_port
    
    def setup(self) -> Optional[TelemetryManager]:
        """Set up telemetry based on configuration"""
        if not self.enable:
            return None
        
        return setup_telemetry(
            service_name=self.service_name,
            service_version=self.service_version,
            enable_traces=self.traces,
            enable_metrics=self.metrics,
            jaeger_endpoint=self.jaeger_endpoint,
            prometheus_port=self.prometheus_port,
        )

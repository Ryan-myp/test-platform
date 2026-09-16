"""OpenTelemetry instrumentation"""
import os
from typing import Optional
from loguru import logger


class TelemetryClient:
    """遥测客户端 - OpenTelemetry"""
    
    def __init__(self):
        self._enabled = os.getenv("OTEL_ENABLED", "false").lower() == "true"
        self._tracer = None
        self._meter = None
        
        if self._enabled:
            self._setup()
        else:
            logger.info("ℹ️ OpenTelemetry disabled (set OTEL_ENABLED=true to enable)")
    
    def _setup(self):
        """初始化 OpenTelemetry"""
        try:
            from opentelemetry import trace, metrics
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.metrics import MeterProvider
            from opentelemetry.sdk.trace.export import BatchSpanProcessor
            from opentelemetry.exporter.jaeger.thrift import JaegerExporter
            
            # 配置 Tracer
            provider = TracerProvider()
            exporter = JaegerExporter(
                agent_host_name=os.getenv("JAEGER_HOST", "localhost"),
                agent_port=int(os.getenv("JAEGER_PORT", 6831))
            )
            provider.add_span_processor(BatchSpanProcessor(exporter))
            trace.set_tracer_provider(provider)
            self._tracer = trace.get_tracer("testpilot")
            
            # 配置 Meter
            meter_provider = MeterProvider()
            metrics.set_meter_provider(meter_provider)
            self._meter = metrics.get_meter("testpilot")
            
            logger.info("✅ OpenTelemetry initialized")
            
        except ImportError:
            logger.warning("⚠️ OpenTelemetry not installed, skipping instrumentation")
            self._enabled = False
        except Exception as e:
            logger.error(f"❌ OpenTelemetry setup failed: {e}")
            self._enabled = False
    
    def start_span(self, name: str, **kwargs):
        """开始一个 span"""
        if not self._enabled or not self._tracer:
            return None
        return self._tracer.start_span(name, **kwargs)
    
    def record_counter(self, name: str, value: int = 1, **kwargs):
        """记录计数器"""
        if not self._enabled or not self._meter:
            return
        counter = self._meter.create_counter(name)
        counter.add(value, kwargs)
    
    def record_histogram(self, name: str, value: float, **kwargs):
        """记录直方图"""
        if not self._enabled or not self._meter:
            return
        histogram = self._meter.create_histogram(name)
        histogram.record(value, kwargs)
    
    def record_gauge(self, name: str, value: float, **kwargs):
        """记录仪表盘"""
        if not self._enabled or not self._meter:
            return
        gauge = self._meter.create_up_down_counter(name)
        gauge.add(value, kwargs)


# 全局单例
telemetry = TelemetryClient()


class Metrics:
    """指标工具类"""
    
    @staticmethod
    def api_request(endpoint: str, duration_ms: float, status_code: int):
        """记录 API 请求指标"""
        telemetry.record_counter(
            "api.requests.total",
            labels={"endpoint": endpoint, "status": str(status_code)}
        )
        telemetry.record_histogram(
            "api.requests.duration",
            duration_ms,
            labels={"endpoint": endpoint}
        )
    
    @staticmethod
    def test_execution(case_id: int, duration_ms: float, passed: bool):
        """记录测试执行指标"""
        telemetry.record_counter(
            "tests.executed.total",
            labels={"passed": str(passed).lower()}
        )
        telemetry.record_histogram(
            "tests.execution.duration",
            duration_ms
        )
    
    @staticmethod
    def ai_call(model: str, duration_ms: float, success: bool):
        """记录 AI 调用指标"""
        telemetry.record_counter(
            "ai.calls.total",
            labels={"model": model, "success": str(success).lower()}
        )
        telemetry.record_histogram(
            "ai.calls.duration",
            duration_ms,
            labels={"model": model}
        )


# 快捷导入
from app.telemetry.instrumentation import telemetry, Metrics
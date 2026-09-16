"""Prometheus metrics exporter"""
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CollectorRegistry
from prometheus_client import make_asgi_app
import time
from typing import Dict, Any


class MetricsCollector:
    """Prometheus 指标收集器"""
    
    def __init__(self):
        self.registry = CollectorRegistry()
        
        # API 指标
        self.api_requests_total = Counter(
            'api_requests_total',
            'Total API requests',
            ['endpoint', 'method', 'status'],
            registry=self.registry
        )
        
        self.api_request_duration = Histogram(
            'api_request_duration_seconds',
            'API request duration',
            ['endpoint'],
            registry=self.registry
        )
        
        # 测试指标
        self.test_executions_total = Counter(
            'test_executions_total',
            'Total test executions',
            ['case_type', 'status'],
            registry=self.registry
        )
        
        self.test_duration_seconds = Histogram(
            'test_duration_seconds',
            'Test execution duration',
            ['case_type'],
            registry=self.registry
        )
        
        # 业务指标
        self.active_users = Gauge(
            'active_users',
            'Currently active users',
            registry=self.registry
        )
        
        self.pending_tasks = Gauge(
            'pending_tasks',
            'Number of pending tasks',
            registry=self.registry
        )
        
        self.knowledge_items = Gauge(
            'knowledge_items',
            'Number of knowledge items',
            ['category'],
            registry=self.registry
        )
    
    def record_api_request(self, endpoint: str, method: str, status: int, duration: float):
        """记录 API 请求"""
        self.api_requests_total.labels(endpoint=endpoint, method=method, status=str(status)).inc()
        self.api_request_duration.labels(endpoint=endpoint).observe(duration)
    
    def record_test_execution(self, case_type: str, status: str, duration: float):
        """记录测试执行"""
        self.test_executions_total.labels(case_type=case_type, status=status).inc()
        self.test_duration_seconds.labels(case_type=case_type).observe(duration)
    
    def get_metrics_app(self):
        """获取 Prometheus metrics ASGI app"""
        return make_asgi_app(self.registry)
    
    def collect(self) -> bytes:
        """收集指标数据"""
        return generate_latest(self.registry).decode('utf-8')


# 全局单例
metrics = MetricsCollector()
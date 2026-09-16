"""Multi-tenancy support"""
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from loguru import logger


@dataclass
class TenantConfig:
    """租户配置"""
    tenant_id: str
    name: str
    database_url: Optional[str] = None
    max_users: int = 100
    max_test_cases: int = 10000
    features: List[str] = field(default_factory=lambda: [
        "api_testing", "sql_testing", "browser_testing",
        "knowledge_base", "bug_tracking", "reports"
    ])
    is_active: bool = True


class TenantManager:
    """租户管理器"""
    
    def __init__(self):
        self._tenants: Dict[str, TenantConfig] = {}
        self._default_tenant = TenantConfig(
            tenant_id="default",
            name="Default Tenant",
            features=["all"]
        )
    
    def register_tenant(self, config: TenantConfig):
        """注册租户"""
        self._tenants[config.tenant_id] = config
        logger.info(f"🏢 Tenant registered: {config.name} (id: {config.tenant_id})")
    
    def get_tenant(self, tenant_id: str) -> Optional[TenantConfig]:
        """获取租户配置"""
        if tenant_id == "default" or tenant_id not in self._tenants:
            return self._default_tenant
        return self._tenants.get(tenant_id)
    
    def list_tenants(self) -> List[TenantConfig]:
        """列出所有租户"""
        return list(self._tenants.values())
    
    def check_feature(self, tenant_id: str, feature: str) -> bool:
        """检查租户是否启用某功能"""
        tenant = self.get_tenant(tenant_id)
        if not tenant:
            return False
        
        if "all" in tenant.features:
            return True
        
        return feature in tenant.features


# 全局单例
tenant_manager = TenantManager()

# 预注册默认租户
tenant_manager.register_tenant(TenantConfig(
    tenant_id="acme-corp",
    name="Acme Corporation",
    max_users=50,
    features=["api_testing", "sql_testing", "browser_testing", "reports"]
))

tenant_manager.register_tenant(TenantConfig(
    tenant_id="globex",
    name="Globex Industries",
    max_users=20,
    features=["api_testing", "knowledge_base"]
))
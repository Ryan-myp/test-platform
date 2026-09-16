"""TestPilot Pro — 应用配置"""

import os
from pathlib import Path
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv(Path(__file__).parent.parent / ".env")


class Settings(BaseSettings):
    app_name: str = "TestPilot Pro"
    version: str = "2.0.0"
    database_url: str = f"sqlite+aiosqlite:///{Path(__file__).parent.parent / 'testpilot.db'}"

    # AI 配置（支持 OpenAI / DeepSeek / 通义千问 / Azure 等）
    ai_model: str = "gpt-4o"
    ai_api_key: str = ""
    ai_base_url: str = "https://api.openai.com/v1"

    # 系统对接
    jira_base_url: str = ""
    jira_token: str = ""
    kibana_base_url: str = ""
    kibana_api_key: str = ""

    # 通知
    webhook_url: str = ""  # 企业微信 / Slack webhook
    
    # 认证
    jwt_secret_key: str = "testpilot-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    
    # Redis 配置
    redis_url: str = ""
    
    # Celery 配置
    celery_broker_url: str = ""
    celery_result_backend: str = ""
    
    # 租户配置
    default_tenant: str = "default"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()

"""TestPilot Pro — AI 测试工作台（自动化执行版）

三层架构:
  PPART 01  知识库（历史用例、Bug记录、日志规范、Schema、需求）
  PPART 02  六大入口（表单驱动、固定输出格式）
  PPART 03  自动化执行引擎（API测试、SQL执行、用例执行、多入口联动流水线）
"""

import os
from pathlib import Path
from pydantic_settings import BaseSettings

# 加载 .env 文件
from dotenv import load_dotenv
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

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()

# TestPilot Pro - 企业级自动化测试平台

![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

## 🚀 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 配置 AI API Key

# 启动服务
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# 访问
# Web UI: http://localhost:8000
# API 文档: http://localhost:8000/docs
# 默认账号: admin / admin123
```

## 🐳 Docker 部署

```bash
docker-compose up -d
```

## 📊 核心功能

| 功能 | 描述 |
|------|------|
| 🧪 AI 测试用例生成 | 基于需求描述自动生成测试用例 |
| 🐛 Bug 根因分析 | 现象描述 → 日志查询 → 根因推断 |
| 📋 日志智能排查 | 日志片段 + TraceID → 链路分析 |
| 🗄️ SQL 性能分析 | SQL 语句 → 执行验证 → 优化建议 |
| 📊 报告生成导出 | JSON / CSV / JUnit 格式 |
| 🔄 回归验证 | 代码变更 → 影响分析 → 测试清单 |
| 🌐 Web UI 自动化 | Playwright 浏览器测试 |
| 🔐 JWT 认证 | 用户管理 + RBAC 权限 |
| 📋 异步任务队列 | asyncio 并发处理 |
| 💬 消息通知 | Slack / 企业微信 |

## 🏗️ 技术架构

```
┌─────────────────────────────────────────────────────┐
│                   Web UI (HTML/CSS/JS)              │
├─────────────────────────────────────────────────────┤
│              FastAPI + REST API                     │
├──────────┬──────────┬──────────┬───────────────────┤
│  API层   │  Auth层  │ Service层│  Task Queue       │
│  (65+)   │  (JWT)   │ (CRUD)   │  (asyncio)        │
├──────────┴──────────┴──────────┴───────────────────┤
│              SQLAlchemy + SQLite                    │
├─────────────────────────────────────────────────────┤
│         AI: OpenAI / DeepSeek / 通义千问            │
│      Browser: Playwright                           │
└─────────────────────────────────────────────────────┘
```

## 🔒 安全特性

- ✅ JWT 认证 + RBAC 权限
- ✅ 速率限制 (100 req/min, auth 5 req/min)
- ✅ SQL 参数化查询 (防注入)
- ✅ 密码 bcrypt 哈希
- ✅ 请求审计日志
- ✅ 统一错误响应格式

## 📈 性能优化

- ✅ 异步数据库操作 (aiosqlite)
- ✅ 连接池管理
- ✅ 缓存层 (Redis 可选)
- ✅ 异步任务队列

## 🧪 测试

```bash
# 运行测试
pytest tests/ -v

# 测试覆盖率
pytest tests/ --cov=app --cov-report=html
```

## 📁 项目结构

```
testpilot-pro/
├── app/
│   ├── api/           # API 路由 (19 模块)
│   ├── auth/          # 认证模块
│   ├── middleware/    # 中间件 (速率限制/审计)
│   ├── schemas/       # Pydantic 模型
│   ├── models/        # 数据模型
│   ├── services/      # 业务逻辑层
│   ├── test_runner.py # 测试执行引擎
│   ├── async_tasks.py # 异步任务队列
│   └── exceptions.py  # 异常处理
├── tests/             # 单元测试
├── templates/         # Web UI
└── docker-compose.yml # Docker 部署
```

## 🔗 API 端点

### 认证
- `POST /api/auth/register` - 注册用户
- `POST /api/auth/login` - 登录获取 Token
- `GET /api/auth/users` - 用户列表 (admin)

### 测试用例
- `GET /api/test-cases` - 用例列表
- `POST /api/test-cases` - 创建用例
- `GET /api/test-cases/{id}` - 用例详情
- `PATCH /api/test-cases/{id}` - 更新用例
- `DELETE /api/test-cases/{id}` - 删除用例
- `POST /api/executions/run-case` - 执行用例

### Bug 管理
- `GET /api/bugs` - Bug 列表
- `POST /api/bugs` - 创建 Bug
- `PATCH /api/bugs/{id}` - 更新 Bug

### 知识库
- `GET /api/knowledge` - 知识库列表
- `POST /api/knowledge` - 添加知识
- `PATCH /api/knowledge/{id}` - 更新知识

### 报告
- `GET /api/reports/export/json` - 导出 JSON
- `GET /api/reports/export/csv` - 导出 CSV

### CI/CD
- `POST /api/ci/github/push` - GitHub webhook
- `POST /api/ci/gitlab/push` - GitLab webhook
- `POST /api/ci/jenkins/build` - Jenkins webhook
- `POST /api/ci/notify/slack` - Slack 通知
- `POST /api/ci/notify/wecom` - 企业微信通知

## 📝 环境变量

```env
# AI 配置
AI_API_KEY=your-api-key
AI_BASE_URL=https://api.openai.com/v1
AI_MODEL=gpt-4o

# 认证
JWT_SECRET_KEY=your-secret-key

# 数据库
DATABASE_URL=sqlite+aiosqlite:///testpilot.db

# Redis (可选)
REDIS_URL=redis://localhost:6379/0
```

## 🤝 贡献

1. Fork 项目
2. 创建特性分支
3. 提交更改
4. 推送分支
5. 创建 Pull Request

## 📄 License

MIT License

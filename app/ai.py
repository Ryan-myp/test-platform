"""AI 层：Prompt 模板 + 知识检索 + LLM 调用"""
import re
import json
import openai
from datetime import datetime, timezone
from loguru import logger
from app.config import settings
from app.database import AsyncSessionLocal
from sqlalchemy import text as sa_text


async def get_prompt_template(entry_type: str) -> str:
    """获取 Prompt 模板"""
    async with AsyncSessionLocal() as session:
        result = await session.execute(sa_text("SELECT value FROM configs WHERE key = 'prompts'"))
        row = result.fetchone()
        if not row:
            return ""
        prompts = json.loads(row[0])
        return prompts.get(entry_type, "")


async def search_knowledge(entry_type: str, input_data: dict, limit: int = 5) -> str:
    """从知识库检索相关内容作为上下文"""
    async with AsyncSessionLocal() as session:
        keywords = [str(v) for v in input_data.values() if isinstance(v, str)][:3]
        if not keywords:
            return ""

        conditions = " OR ".join([
            f"title LIKE '%' || :k{i} || '%' OR content LIKE '%' || :k{i} || '%'"
            for i in range(len(keywords))
        ])
        params = {f"k{i}": k for i, k in enumerate(keywords)}

        result = await session.execute(
            sa_text(f"SELECT category, title, content FROM knowledge WHERE {conditions} LIMIT :limit"),
            {**params, "limit": limit}
        )
        rows = result.fetchall()
        if rows:
            return "\n\n".join([
                f"【{r[0]}】{r[1]}\n{r[2][:300]}" for r in rows
            ])
    return ""


async def call_ai(entry_type: str, input_data: dict) -> dict:
    """调用 AI 生成输出"""
    template = await get_prompt_template(entry_type)
    if not template:
        return {"error": f"No prompt template for {entry_type}", "status": "error"}

    # 注入知识库上下文
    context = await search_knowledge(entry_type, input_data)
    if context:
        template += f"\n\n【相关历史经验】\n{context}"

    # 自动提取模板占位符并为缺失的提供空字符串默认值
    placeholders = set(re.findall(r'\{(\w+)\}', template))
    filled_data = {k: input_data.get(k, '') for k in placeholders}
    prompt = template.format(**filled_data)

    result = {
        "input_data": input_data,
        "prompt": prompt,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model_used": settings.ai_model,
        "has_api_key": bool(settings.ai_api_key),
        "context_found": bool(context)
    }

    if settings.ai_api_key:
        client = openai.AsyncOpenAI(
            api_key=settings.ai_api_key,
            base_url=settings.ai_base_url or "https://api.openai.com/v1"
        )
        try:
            resp = await client.chat.completions.create(
                model=settings.ai_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )
            result["output"] = resp.choices[0].message.content
            result["status"] = "success"
        except Exception as e:
            logger.opt(exception=True).error(f"AI 调用失败: {e}")
            result["error"] = str(e)
            result["status"] = "error"
    else:
        # 演示模式
        result["output"] = _demo_output(entry_type, input_data)
        result["status"] = "demo"

    return result


def _demo_output(entry_type: str, data: dict) -> str:
    """演示输出（未配置 API Key 时使用）"""
    demos = {
        "generate_cases": f"""## 测试用例生成结果

基于需求「{data.get('requirement', 'N/A')}」，生成以下测试用例：

| 编号 | 前置条件 | 操作步骤 | 预期结果 | 优先级 |
|------|----------|----------|----------|--------|
| TC001 | 用户已注册 | 输入正确手机号和验证码 | 登录成功，跳转首页 | P0 |
| TC002 | 用户已注册 | 输入错误验证码 | 提示验证码错误 | P1 |
| TC003 | 用户已注册 | 输入已过期验证码 | 提示验证码已过期 | P1 |
| TC004 | 用户已注册 | 输入非法手机号格式 | 提示手机号格式错误 | P2 |
| TC005 | 用户已注册 | 并发发送相同验证码 | 只响应第一个请求 | P1 |
| TC006 | 用户未注册 | 尝试登录 | 提示账号不存在 | P0 |
| TC007 | 用户已登录 | 切换账号后操作 | 权限正确隔离 | P0 |
| TC008 | 网络中断 | 提交过程中断网 | 提示网络异常，数据不丢失 | P1 |

共 8 条用例，覆盖正常/异常/边界/安全场景。""",

        "analyze_bug": f"""## Bug 分析报告

**现象还原：** {data.get('description', 'N/A')}
**错误日志：** `{data.get('error_log', '无')}`
**TraceID：** {data.get('trace_id', '无')}
**环境：** {data.get('environment', 'Staging')}

**根因推断：**
高并发场景下，支付回调更新订单状态时数据库连接超时，导致部分请求状态不一致。

**验证方案：**
1. 复现：在支付成功后立即检查订单状态
2. 观察：Kibana 搜索 ConnectionTimeout + 订单表事务日志
3. 验证：模拟并发支付回调，确认状态一致性

**修复建议：**
- 引入分布式锁保证幂等
- 添加补偿任务处理超时重试
- 优化 DB 连接池配置（max_idle → 20）

**相似历史 Bug：**
- #BUG-2024-0312：支付回调订单状态不一致
- #BUG-2024-0108：高并发下数据更新丢失""",

        "troubleshoot_logs": f"""## 日志排查报告

**TraceID：** {data.get('trace_id', 'N/A')}
**时间范围：** {data.get('time_range', 'last_15min')}

**调用链路：**
```
客户端 → API Gateway → OrderService → PaymentService → DB
                                    ↓ ConnectionTimeout
                                    [问题定位点]
```

**根因：** 数据库连接池耗尽

**排查建议：**
1. 检查 `max_connections` 配置
2. 查看慢查询日志
3. 监控连接泄漏""",

        "analyze_sql": f"""## SQL 分析报告

**SQL：**
```sql
{data.get('sql', 'N/A')}
```

**问题：**
1. 性能风险：缺少索引，全表扫描
2. 规范问题：SELECT * 返回不必要字段
3. 安全风险：无 LIMIT 限制

**优化建议：**
```sql
SELECT id, status, amount, create_time
FROM orders
WHERE create_time > '2024-01-01'
  AND status = 'paid'
ORDER BY create_time DESC
LIMIT 100;
```
新增索引：`CREATE INDEX idx_orders_ct_status ON orders(create_time, status);`""",

        "generate_report": f"""## 测试报告 - {data.get('round', 'P0')} 轮

| 指标 | 数值 |
|------|------|
| 总用例数 | {data.get('total_cases', 'N/A')} |
| 通过 | {data.get('passed', 'N/A')} |
| 失败 | {data.get('failed', 'N/A')} |
| 通过率 | {int(data.get('passed',0))/max(int(data.get('total_cases',1)),1)*100:.1f}% |

**Bug 统计：** {data.get('bug_stats', 'N/A')}

**风险评估：** 支付模块存在 2 个 P0 Bug 未修复，建议延期上线。
**结论：** 不建议上线""",

        "regression": f"""## 回归测试清单

**变更：** {data.get('change_description', 'N/A')}
**影响范围：** {data.get('impact_scope', 'N/A')}

| 用例编号 | 所属模块 | 用例名称 | 优先级 | 是否新增 |
|----------|----------|----------|--------|----------|
| TC-PAY-001 | 支付模块 | 支付回调处理 | P0 | 否 |
| TC-PAY-002 | 支付模块 | 支付超时重试 | P0 | 否 |
| TC-PAY-003 | 支付模块 | 并发支付幂等性 | P0 | **是** |
| TC-ORD-001 | 订单模块 | 订单状态同步 | P0 | 否 |
| TC-ORD-002 | 订单模块 | 订单超时无限 | P1 | 否 |

**新增用例建议：**
- 并发回调同一订单的幂等性验证
- 数据库连接中断后的补偿机制验证"""
    }
    return demos.get(entry_type, "Demo output")

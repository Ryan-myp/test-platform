"""Entry points API."""
from fastapi import APIRouter
from typing import Any, Dict

router = APIRouter(prefix="/api", tags=["入口"])


@router.get("/entries")
async def get_entries() -> Dict[str, Any]:
    """Get all entry points."""
    return {
        "generate_cases": {
            "name": "生成用例",
            "icon": "📝",
            "desc": "根据需求描述自动生成测试用例，支持表格和思维导图格式",
            "input": ["需求描述", "功能模块"],
            "output": "测试用例表格"
        },
        "analyze_bug": {
            "name": "分析Bug",
            "icon": "🐛",
            "desc": "分析缺陷描述，定位根因并给出修复建议",
            "input": ["Bug 描述", "重现步骤"],
            "output": "根因分析报告"
        },
        "troubleshoot_logs": {
            "name": "排查日志",
            "icon": "📋",
            "desc": "关联 Kibana 日志，智能分析异常模式",
            "input": ["日志片段", "时间范围"],
            "output": "异常分析报告"
        },
        "analyze_sql": {
            "name": "分析 SQL",
            "icon": "🗄️",
            "desc": "分析慢 SQL，提供优化建议和执行计划",
            "input": ["SQL 语句"],
            "output": "优化建议报告"
        },
        "write_report": {
            "name": "写报告",
            "icon": "📊",
            "desc": "根据测试结果自动生成测试报告",
            "input": ["测试数据", "报告模板"],
            "output": "测试报告文档"
        },
        "regression": {
            "name": "回归验证",
            "icon": "🔄",
            "desc": "分析代码变更，确定回归测试范围",
            "input": ["变更描述", "影响模块"],
            "output": "回归测试范围"
        },
        "web_ui_test": {
            "name": "Web UI 测试",
            "icon": "🌐",
            "desc": "浏览器自动化测试，支持 Playwright",
            "input": ["目标 URL", "测试步骤"],
            "output": "测试执行结果"
        },
        "ai_test_generation": {
            "name": "AI 测试生成",
            "icon": "🤖",
            "desc": "AI 辅助生成自动化测试脚本",
            "input": ["需求文档", "测试场景"],
            "output": "测试脚本代码"
        }
    }


@router.get("/tasks/templates")
async def get_task_templates() -> Dict[str, Any]:
    """Get task templates."""
    return {
        "templates": {
            "generate_cases": {
                "prompt": "请为以下需求生成测试用例：\n\n{requirement}\n\n要求：\n1. 覆盖正常流程、异常流程、边界条件\n2. 用例优先级 P0/P1/P2\n3. 输出格式：表格",
                "fields": ["requirement", "module"]
            },
            "analyze_bug": {
                "prompt": "请分析以下 Bug 并定位根因：\n\n{description}\n\n请提供：\n1. 可能的根因分析\n2. 排查思路\n3. 修复建议",
                "fields": ["description", "reproduction_steps"]
            }
        }
    }


@router.post("/tasks/pipeline")
async def run_pipeline(data: Dict[str, Any]) -> Dict[str, Any]:
    """Run a pipeline of tasks."""
    steps = data.get("steps", [])
    results = []
    
    for step in steps:
        results.append({
            "step": step.get("name", ""),
            "status": "pending",
            "output": ""
        })
    
    return {
        "execution_id": f"pipeline_{data.get('id', '')}",
        "steps": results,
        "status": "started"
    }


@router.get("/stats")
async def get_stats() -> Dict[str, Any]:
    """Get dashboard statistics."""
    return {
        "total_tasks": 6,
        "today_tasks": 3,
        "total_knowledge": 3,
        "total_schedules": 3
    }

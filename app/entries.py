"""入口定义 — 六大核心入口的表单字段和描述"""

ENTRY_DEFS = {
    "generate_cases": {
        "name": "生成测试用例",
        "icon": "🧪",
        "desc": "根据需求自动生成测试用例，参考历史用例风格",
        "fields": [
            {"key": "requirement", "label": "需求描述", "type": "textarea", "required": True},
            {"key": "priority", "label": "优先级", "type": "select", "options": ["P0", "P1", "P2"]},
            {"key": "module", "label": "关联模块", "type": "text"},
        ],
        "auto_execute": {
            "type": "api_test",
            "desc": "执行生成的 API 接口测试"
        }
    },
    "analyze_bug": {
        "name": "分析 Bug",
        "icon": "🐛",
        "desc": "分析 Bug 根因，关联历史相似 Bug",
        "fields": [
            {"key": "description", "label": "Bug 现象描述", "type": "textarea", "required": True},
            {"key": "error_log", "label": "错误日志", "type": "textarea"},
            {"key": "trace_id", "label": "TraceID", "type": "text"},
            {"key": "environment", "label": "环境", "type": "text"},
        ],
        "auto_execute": {
            "type": "kibana_search",
            "desc": "查询 Kibana 日志"
        }
    },
    "troubleshoot_logs": {
        "name": "排查日志",
        "icon": "📋",
        "desc": "分析日志片段，定位调用链路中的问题",
        "fields": [
            {"key": "log_snippet", "label": "日志片段", "type": "textarea", "required": True},
            {"key": "trace_id", "label": "TraceID", "type": "text"},
            {"key": "time_range", "label": "时间范围", "type": "text", "default": "last_15_minutes"},
        ],
        "auto_execute": {
            "type": "kibana_search",
            "desc": "查询 Kibana 日志"
        }
    },
    "analyze_sql": {
        "name": "分析 SQL",
        "icon": "🗄️",
        "desc": "分析 SQL 性能与规范，提供优化建议",
        "fields": [
            {"key": "sql", "label": "SQL 语句", "type": "textarea", "required": True},
            {"key": "scenario", "label": "执行场景说明", "type": "textarea", "required": True},
            {"key": "expected", "label": "期望结果", "type": "text"},
            {"key": "db_url", "label": "数据库连接（可选）", "type": "text"},
        ],
        "auto_execute": {
            "type": "sql_exec",
            "desc": "执行 SQL 查询（只读）"
        }
    },
    "generate_report": {
        "name": "生成测试报告",
        "icon": "📊",
        "desc": "根据执行数据生成标准测试报告",
        "fields": [
            {"key": "round", "label": "测试轮次", "type": "text", "required": True},
            {"key": "total_cases", "label": "用例总数", "type": "number"},
            {"key": "passed", "label": "通过数", "type": "number"},
            {"key": "failed", "label": "失败数", "type": "number"},
            {"key": "bug_stats", "label": "Bug 统计", "type": "textarea"},
        ],
        "auto_execute": None
    },
    "regression": {
        "name": "回归验证",
        "icon": "🔄",
        "desc": "根据变更生成回归测试清单",
        "fields": [
            {"key": "change_description", "label": "变更说明", "type": "textarea", "required": True},
            {"key": "impact_scope", "label": "影响范围", "type": "text", "required": True},
            {"key": "existing_cases", "label": "已有用例集（选填）", "type": "textarea"},
        ],
        "auto_execute": {
            "type": "api_test",
            "desc": "执行回归 API 测试"
        }
    },
    # ── 新增：Web UI 自动化测试入口 ──
    "web_ui_test": {
        "name": "Web UI 自动化测试",
        "icon": "🌐",
        "desc": "使用浏览器自动化执行 UI 测试，支持截图和断言",
        "fields": [
            {"key": "url", "label": "目标 URL", "type": "text", "required": True},
            {"key": "viewport", "label": "视口大小", "type": "text", "default": "1920x1080"},
            {"key": "cases_json", "label": "测试用例（JSON数组）", "type": "textarea",
             "placeholder": '[{"id":"TC001","name":"登录测试","steps":[{"action":"fill","target":"input[name=email]","value":"test@example.com"},{"action":"fill","target":"input[name=password]","value":"123456"},{"action":"click","target":"button[type=submit]"}]}]'},
            {"key": "wait_for", "label": "等待元素（可选）", "type": "text"},
        ],
        "auto_execute": {
            "type": "browser_test",
            "desc": "启动浏览器执行 UI 自动化测试"
        }
    },
    # ── 新增：AI 辅助用例生成 + 自动执行 ──
    "ai_test_generation": {
        "name": "AI 生成 + 执行测试",
        "icon": "🤖",
        "desc": "AI 根据需求生成测试用例并自动在浏览器中执行",
        "fields": [
            {"key": "url", "label": "目标网站 URL", "type": "text", "required": True},
            {"key": "feature", "label": "测试功能描述", "type": "textarea", "required": True},
            {"key": "priority", "label": "优先级", "type": "select", "options": ["P0", "P1", "P2"]},
        ],
        "auto_execute": {
            "type": "ai_browser_test",
            "desc": "AI 生成用例 → 浏览器自动执行 → 截图记录"
        }
    }
}


# 多入口联动流水线定义
PIPELINE_TEMPLATES = {
    "bug_investigation": {
        "name": "线上 Bug 10分钟闭环",
        "desc": "Bug发现 → 日志排查 → Bug分析 → 补充用例 → 回归验证",
        "steps": [
            {"entry_type": "troubleshoot_logs", "desc": "排查日志，定位链路"},
            {"entry_type": "analyze_bug", "desc": "分析 Bug，推断根因"},
            {"entry_type": "generate_cases", "desc": "补充边界测试用例"},
            {"entry_type": "regression", "desc": "生成回归清单"},
        ]
    },
    "sql_optimization": {
        "name": "SQL 性能优化",
        "desc": "SQL分析 → 执行验证 → 报告生成",
        "steps": [
            {"entry_type": "analyze_sql", "desc": "分析 SQL 性能"},
            {"entry_type": "generate_report", "desc": "生成优化报告"},
        ]
    },
    "release_check": {
        "name": "发布前检查",
        "desc": "回归验证 → 生成报告",
        "steps": [
            {"entry_type": "regression", "desc": "回归验证"},
            {"entry_type": "generate_report", "desc": "生成测试报告"},
        ]
    },
    "web_ui_automation": {
        "name": "Web UI 自动化测试",
        "desc": "AI 生成用例 → 浏览器执行 → 截图记录 → 生成报告",
        "steps": [
            {"entry_type": "ai_test_generation", "desc": "AI 生成并执行 UI 测试"},
            {"entry_type": "generate_report", "desc": "生成测试报告"},
        ]
    }
}

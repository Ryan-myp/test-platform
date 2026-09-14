# TestPilot Pro UI 审计

## Design language
- **Audited surface**: TestPilot Pro v2.0 测试平台 Web UI (单页应用)
- **Design sources**: 内联 CSS 在 index.html, 无外部 DESIGN.md
- **Documented decisions**: 暗色主题, 蓝色主色调 (#3b82f6), 紫色渐变accent
- **Governing owners and consumers**: 前端页面渲染
- **Explicit exceptions**: None documented

---

## Findings

| # | Problem | Evidence | Proposed change | Scope | Confidence |
|---|---------|----------|-----------------|-------|------------|
| 1 | 状态标签颜色语义不一致 | `badge-success` 用于成功/启用状态, 但 `badge-danger` 用于禁用状态 - 颜色语义混乱 (success 通常表示正向状态而非失败) | 统一语义: `badge-success` = 启用/通过, `badge-warning` = 禁用/待处理, `badge-danger` = 错误/失败 | 定时任务、任务历史 | High |
| 2 | 缺少自定义滚动条样式 | 滚动条使用浏览器默认样式 (浅色), 与暗色主题冲突, 视觉不协调 | 添加 `::-webkit-scrollbar` 样式, 匹配暗色主题颜色 | 所有滚动区域 | High |
| 3 | 导航图标使用 emoji 跨平台不一致 | 侧边栏使用 emoji (📊⚡🌐等), 在不同 OS/浏览器上渲染差异大 | 替换为 SVG 图标或统一图标字体 (如 Lucide, Heroicons) | 侧边栏导航 | Medium |
| 4 | 卡片 hover 效果不统一 | `entry-card` 有 `transform: translateY(-2px)` 和阴影, 但 `stat-card` 没有 hover 效果 | 为所有卡片添加一致的 hover 反馈样式 | 卡片组件 | Medium |
| 5 | 按钮样式层级混乱 | 存在 `btn-primary`, `btn-success`, `btn-danger`, `btn-secondary` 四种变体但使用场景不明确 | 简化为两种主要按钮: primary (主操作) + secondary (次要操作), 删除状态颜色按钮 | 按钮系统 | Medium |

---

## Improve first

**高优先级修复：自定义滚动条样式**

问题: 当前滚动条是浏览器默认的浅灰色, 与暗色主题 (#0a0e1a) 严重冲突, 视觉上破坏整体感。

建议修复:
```css
/* 滚动条样式 */
::-webkit-scrollbar { width: 8px; height: 8px; }
::-webkit-scrollbar-track { background: var(--surface); }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: var(--muted); }
```

影响: 所有滚动区域 (侧边栏、内容区、表格) 都会改善

---

**中优先级修复：状态标签语义统一**

当前问题:
- `badge-success` 用于"已启用" - 合理
- `badge-danger` 用于"已禁用" - 不合理, danger 应表示错误
- `badge-warning` 用于"运行中" - 合理

建议:
- 启用状态 → `badge-success` ✓
- 运行中状态 → `badge-info` (当前是 warning)
- 禁用状态 → `badge-muted` (新增) 或保持 `badge-danger` 但改变语义

影响: 定时任务、任务历史页面的状态显示

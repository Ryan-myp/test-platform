# Plan: 优化滚动条与状态标签语义

## Context
测试平台暗色主题与浏览器默认滚动条样式冲突，状态标签颜色语义混乱。

## Changes

### 1. 添加自定义滚动条样式

在 `:root` 后添加：

```css
/* 滚动条样式 - 匹配暗色主题 */
::-webkit-scrollbar { width: 8px; height: 8px; }
::-webkit-scrollbar-track { background: var(--surface); }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: var(--muted); }
```

### 2. 统一状态标签语义

**修改 index.html 中的 CSS:**

```css
/* 新增 muted badge */
.badge-muted { background: rgba(100,116,139,0.2); color: var(--muted); }
```

**修改模板中的 badge 使用:**

| 状态 | 原 class | 新 class | 说明 |
|------|----------|----------|------|
| 启用 | badge-success | badge-success | 保持不变 |
| 运行中 | badge-warning | badge-info | 更准确 |
| 禁用 | badge-danger | badge-muted | 语义正确 |
| 成功 | badge-success | badge-success | 保持不变 |
| 失败 | badge-danger | badge-danger | 保持不变 |
| 信息 | badge-info | badge-info | 保持不变 |

## Files to modify
- `/tmp/testpilot-pro/templates/index.html`

## Verification
- 滚动条颜色应为深灰色匹配主题
- 定时任务的启用/禁用状态颜色正确
- 任务状态标签语义清晰

# Plan: 统一卡片交互与按钮系统

## Context
当前卡片 hover 效果不一致，按钮样式过多导致视觉混乱。

## Changes

### 1. 统一卡片 hover 效果

在 CSS 中添加：

```css
/* 卡片 hover 效果 */
.stat-card:hover { transform: translateY(-2px); box-shadow: 0 8px 24px rgba(0,0,0,0.3); }
```

### 2. 简化按钮系统

**移除:**
- `.btn-success` 
- `.btn-danger`

**保留:**
- `.btn-primary` - 主操作 (蓝色渐变)
- `.btn-secondary` - 次要操作 (灰色边框)

**修改模板中的按钮:**
- 删除按钮: `btn-secondary` + `color: var(--danger)` (通过 style 或新增样式)
- 执行按钮: 保持 `btn-primary`

## Files to modify
- `/tmp/testpilot-pro/templates/index.html`

## Verification
- 所有卡片 hover 时有轻微上浮效果
- 按钮样式统一，视觉上更清晰

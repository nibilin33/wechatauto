# macOS UI 模板（用于 UI 检测 / Template Matching）

`wechat_agent/perception/detector.py` 会递归扫描本目录下的 `*.png`，对微信窗口截图做模板匹配，输出 `UiElementsDetected`。

## 命名规则

- 文件名的 stem 作为 label：`send.png` → `send`
- 支持同一 label 多个变体：`send__dark.png`、`send__v4.png`（`__` 前面的部分作为 label）

建议的 label（v1 闭环用到）
- `search`：搜索框/放大镜/搜索入口的图标或按钮
- `send`：发送按钮（图标或按钮局部）

## 如何制作模板

1. 在 `runs/<run_id>/shots/` 里找一张清晰截图（建议 1x 缩放、无压缩 PNG）
2. 用系统截图/图片编辑工具裁切出小图标（尽量只包含图标/按钮，不要带太多背景）
3. 保存为 PNG 放到此目录

## 注意事项

- 多 DPI / 多主题建议多放几套模板（同 label 多变体）
- 若匹配误报：提高 threshold，或裁得更“特征化”（减少大面积纯色背景）


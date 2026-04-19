# 里程碑与交付物（建议执行顺序）

> 目标：在 macOS + Windows 上实现微信 PC 端自动化 Agent，纯视觉优先，兼容 UI 版本变化，并做到“可回放、可验证、可控”。

## M0：工程骨架 + 事件落盘（1–2 天）

交付物：
- 事件 envelope 定义与 JSONL 日志格式（可检索、可关联 run_id）
- 基础运行框架：`cli/config/logger`
- `storage/replay` 的最小能力：给一组截图能重放 perception 输出（先离线也行）

验收标准：
- 一次运行能生成完整事件链（至少：ScreenshotCaptured → SemanticParsed）

## M1：单平台闭环（先 macOS 或 Windows，3–7 天）

交付物：
- `platform`：窗口定位/激活、窗口截图、输入（点击/粘贴/按键）
- `perception`：layout + OCR 最小可用（先不做 detector 也可）
- `actions`：`search_contact/open_chat/read_recent/send_message/verify`

验收标准：
- 在固定分辨率 + 主题下，闭环跑通：打开会话 → 读最近 N 条 → 发送一条测试消息 → 校验成功

## M2：多版本 UI 兼容（核心，1–3 周）

交付物：
- `UiProfile`：运行时 profile 识别（不同版本/布局/主题）
- 语义锚点策略链：Detector/OCR/布局推断的分层定位
- 数据集与回归：收集典型截图（不同版本、DPI、主题、窗口大小）

验收标准：
- 在至少 3 种 UI/主题组合下，核心动作成功率显著提升；失败能自解释（事件链可定位原因）

## M3：跨平台扩展（1–2 周）

交付物：
- 另一平台的 `platform/*` 实现
- 复用同一套 `perception/actions/core`，仅替换 ports

验收标准：
- 两平台均能跑通 M1 闭环，且 actions 代码不分叉（允许 profile/模板分叉）

## M4：自动回复上线（可选，未来）（1–2 周）

交付物：
- `SendGuard`：白名单/频率/静默/黑名单/不确定则停
- `--dry-run` / `--confirm`（默认安全）
- 回复策略（规则 or LLM），并做“发送前校验”

验收标准：
- 在真实聊天中不误发、不重复发；遇到不确定场景能停止并留证据（建议默认 `dry-run/confirm`）

## M5：鲁棒性与可维护性（持续迭代）

交付物：
- 弹窗/遮挡/断网/窗口失焦等恢复策略
- 端到端回归（用历史回放数据集跑 semantic/action 级测试）
- 性能优化（ROI、缓存、并行化）

验收标准：
- UI 改版后只需更新少量 profile/模板即可恢复核心能力

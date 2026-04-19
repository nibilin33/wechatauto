# 架构设计（macOS + Windows，纯视觉优先）

本文把项目目标落到“事件模型 + 模块边界 + 数据流 + 可落地接口”，用于指导实现与迭代。

## 0. 约束与原则

**目标平台**
- macOS：WeChat for Mac
- Windows：WeChat for Windows（PC 微信），需要兼容不同 UI 版本与布局变化

**自动化策略**
- 纯视觉优先：截图 → 布局切分 → UI 检测 / OCR → 语义状态（semantic state）
- 不依赖 UIA/AX（可访问性能力可以作为可选增强，但不作为主路径）

**核心原则**
1. **语义锚点优先**：动作基于“按钮/输入框/会话标题/消息气泡”等语义对象的 bbox，而不是固定坐标。
2. **强校验**：每个关键动作必须有可观测的 post-condition（否则视为失败进入恢复流程）。
3. **可回放**：所有观测、推断、动作、校验与失败原因均事件化落盘，支持离线回放与回归。
4. **不确定就停**：当置信度不足或 UI 未识别时，优先“重新观测/降级/退出”，避免误发。

## 1. 事件驱动主循环（Observe → Perceive → Plan → Act → Verify → Recover）

建议以事件总线贯穿系统，形成统一的可观测链路：

1) Observe（平台观测）
- 激活/定位微信窗口，截取窗口区域（或 ROI）并标准化坐标体系

2) Perceive（视觉理解）
- Layout：切分主要面板（会话列表/聊天内容/输入区/顶部栏）
- Detector：检测关键控件图标（发送、搜索、返回、更多等）
- OCR：抽取文本（会话标题、联系人名、消息文本、按钮文案）
- Semantic：输出“当前页面类型 + 可操作控件 + 消息列表”等语义状态

3) Plan（任务规划）
- 从目标（例如“打开联系人并回复”）规划为可执行动作序列（Action DAG / 线性步骤）

4) Act（执行动作）
- 根据语义对象定位点击/输入/粘贴/等待

5) Verify（结果校验）
- 校验打开的会话是否是目标、消息是否读到、发送是否成功等

6) Recover（失败恢复）
- 重试（带退避）、重新观测、回退到已知状态、降级定位策略、最终安全退出

## 2. 统一事件模型（建议 JSONL 落盘）

所有事件统一 envelope（示例字段）：
- `event_id`：uuid
- `run_id`：一次运行的唯一 id
- `timestamp`：毫秒/ISO
- `type`：事件类型
- `payload`：事件内容（严禁放无法序列化对象）
- `artifacts`：截图路径、裁剪图路径、模型输出路径等
- `metrics`：耗时、置信度等

关键事件类型（建议最小集合）：

**平台事件**
- `WindowLocated`：窗口句柄/边界/缩放信息（仅元数据）
- `WindowActivated`
- `ScreenshotCaptured`：截图路径 + window bbox + 坐标映射信息
- `InputDispatched`：点击/键入/粘贴（仅记录意图与目标 bbox，不记录敏感内容或做脱敏）

**感知事件**
- `LayoutSegmented`：面板 bbox（sidebar/chat/composer/topbar…）
- `UiElementsDetected`：控件 bbox + label + score
- `OcrCompleted`：文本块 bbox + text + score（可按需要脱敏）
- `SemanticParsed`：语义状态摘要 + 关键对象 bbox + 置信度

**任务/动作事件**
- `TaskPlanned`：任务树/步骤
- `ActionStarted` / `ActionSucceeded` / `ActionFailed`
- `Verified`：校验项与结果
- `RecoveryApplied`：采用何种恢复策略

## 3. 模块边界与依赖方向

依赖方向建议固定为：

`app → core → (actions, perception, platform, recovery, storage)`

- `core/`：状态机、任务定义、规划器、事件总线（不含平台细节）
- `platform/`：跨平台 ports + macOS/windows 两套实现（窗口/截图/输入）
- `perception/`：纯视觉理解（OCR/检测/布局/语义解析/版本 profile）
- `actions/`：可复用动作库（仅依赖 ports 与语义状态）
- `recovery/`：重试与兜底策略（不做“业务动作”，只决定“下一步怎么安全继续”）
- `storage/`：事件日志、回放、sqlite（可选）
- `prompts/`：自动回复提示词/策略（可选接入 LLM）

## 4. 纯视觉“兼容多版本 UI”的关键设计

### 4.1 UI Profile（运行时识别 UI 版本/布局）

不同版本 UI 往往差在：布局比例、按钮图标、文案、主题色、间距、字体渲染。

建议引入 `UiProfile`：
- 输入：窗口截图（或 topbar/toolbar 的局部）
- 输出：`profile_id`（例如 `win_v3_compact` / `win_v4_spacious` / `mac_default`）+ 置信度

Profile 的作用：
- 选择不同的布局切分参数（比例、边界先验）
- 选择不同的检测器/模板集（例如发送按钮图标不同）
- 选择不同的 OCR 预处理策略（阈值、去噪、放大倍数）

### 4.2 语义锚点（Anchor）与定位策略链

定义一组跨版本尽量稳定的锚点（Anchor），例如：
- 会话标题区域（topbar 的大文本）
- 搜索框（放大镜图标 + 输入框形状）
- 输入区（底部大矩形文本区域）
- 发送按钮（箭头/“发送”文案/按钮形状）
- 消息气泡（左右对齐、圆角矩形、与头像相邻）

动作定位策略链（从稳到弱）：
1. 视觉检测到目标控件 bbox（Detector：模板匹配 / YOLO）
2. OCR 匹配到目标文案 bbox（例如“发送”）
3. 布局先验 + 相对位置推断（例如发送按钮在输入框右侧）
4. 大模型兜底（Vision LLM 输出候选控件 bbox；仅在关键锚点缺失时触发）
5. 降级：在候选区域内做受控点击（必须有强校验，否则停止）

### 4.3 坐标体系与 DPI 统一（跨平台必做）

必须在 `ScreenshotCaptured` 事件中记录坐标映射信息：
- 截图像素坐标（image space）
- 窗口坐标（window space，点按输入需要）
- 屏幕坐标（screen space）
- DPI/缩放因子（Windows 特别关键）

建议内部统一使用**归一化坐标**（0..1 相对窗口），在真正执行点击时再映射到平台坐标。

## 5. 动作（Actions）设计：以“可验证”为第一目标

动作分两类：

**原子动作（platform-level）**
- click / double_click / right_click / type / paste / key_combo / wait

**业务动作（wechat-level）**
- `search_contact(name)`
- `open_chat(name)`
- `read_recent(n)`
- `send_message(text)`
- `dismiss_popup()`（兜底用）

每个业务动作必须声明：
- preconditions：依赖的语义状态（例如必须在主界面）
- postconditions：可校验结果（例如 topbar 标题匹配目标联系人名）
- timeout / retry policy：超过阈值进入恢复

## 6. 校验（Verify）与恢复（Recovery）

**校验建议最小集合**
- `ChatHeaderMatches(target_name)`：打开会话是否正确
- `ComposerReady()`：输入框是否可输入
- `MessageAppeared(text_hash)`：发送后是否在消息列表出现（避免重复发）
- `NoModalBlocking()`：是否存在遮挡弹窗/引导层

**恢复策略（从轻到重）**
1. 重新观测（刷新截图 + 重新解析）
2. 重试同一动作（退避 + 次数上限）
3. 切换定位策略（检测 → OCR → 布局推断）
4. 回到已知状态（例如点击返回、关闭弹窗、切到主界面）
5. 安全退出（记录事件并停止）

## 7. 自动回复安全护栏（建议默认开启）

在 `core` 增加“发送守门人（SendGuard）”：
- 白名单联系人/群
- 频率限制（每联系人/每群的冷却时间）
- 静默时段
- 关键词黑名单（例如涉及转账/验证码等直接停止）
- `--dry-run` 或 `--confirm`（默认不自动发送，先输出拟发送内容）

## 8. 里程碑建议（与 `docs/MILESTONES.md` 对齐）

实现顺序建议：
1. 单平台闭环（优先你主用平台）→ 验证事件链与回放体系
2. 固化 perception → semantic state 的契约（跨平台复用）
3. 把 actions 全部改为“语义锚点 + 校验 + 兜底”
4. 补齐另一平台 `platform/*`，复用同一套 actions/perception

# wechatauto

一个跨平台（macOS + Windows）的微信 PC 端自动化 Agent，**纯视觉优先**（OCR / UI 检测 / 布局推断），目标是在 UI 版本与布局变化下仍尽量可维护、可回放、可验证。

v1 范围（当前选择：只做闭环）：
1. 自动找到联系人 / 群聊并打开会话
2. 读取最近消息（结构化提取）
3. 发送一条固定测试消息并校验（`--send` 才会真的发）
4. 执行固定动作：发文字、点按钮、切换会话、搜索联系人（逐步补齐）
5. 尽量减少纯坐标点击：以“语义锚点 + 校验 + 兜底”实现可维护

设计文档：
- `docs/ARCHITECTURE.md`
- `docs/MILESTONES.md`
- `docs/YOLO_TRAINING.md`

快速开始（先用骨架验证事件/规划链路）：
- `python3 -m wechat_agent.app.main --platform noop --contact Alice --recent 5`

macOS（需要先启动微信，并授予终端/osascript 辅助功能权限；会尝试按步骤截图落到 `runs/<run_id>/shots/`）：
- `python3 -m wechat_agent.app.main --platform macos --contact Alice --recent 5`

UI 检测（模板匹配）：
- 把 `search*.png`、`send*.png` 等模板放到 `assets/templates/macos/`（见 `assets/templates/macos/README.md`）

UI 检测（YOLO，可选）：
- `python3 -m wechat_agent.app.main --platform macos --contact 你的联系人 --recent 5 --yolo-model assets/models/ui_yolo.pt`

大模型兜底（可选；仅在缺少关键元素时触发）：
- 依赖安装：`pip install '.[vlm]'`
- OpenAI：`OPENAI_API_KEY=... python3 -m wechat_agent.app.main --platform macos --contact 你的联系人 --recent 5 --vlm-provider openai --openai-model gpt-4.1-mini`
- Qwen-VL（DashScope OpenAI 兼容模式）：`DASHSCOPE_API_KEY=... python3 -m wechat_agent.app.main --platform macos --contact 你的联系人 --recent 5 --vlm-provider qwen --qwen-model qwen2.5-vl-7b-instruct`
- 外部命令（自定义）：`python3 -m wechat_agent.app.main --platform macos --contact 你的联系人 --recent 5 --vlm-provider cmd --llm-fallback-cmd 'python3 scripts/llm_fallback.py --image {image_path}'`

wechat_agent/
├─ app/
│  ├─ main.py                  # 程序入口
│  ├─ cli.py                   # 命令行入口
│  └─ config.py                # 配置加载
│
├─ core/
│  ├─ models.py                # 数据结构
│  ├─ state.py                 # 状态机
│  ├─ task.py                  # 任务定义
│  ├─ planner.py               # 任务规划
│  └─ errors.py                # 异常定义
│
├─ platform/
│  ├─ ports.py                  # Window/Screen/Input/A11y 抽象（跨平台）
│  ├─ macos/                    # macOS 实现（窗口/截图/输入）
│  └─ windows/                  # Windows 实现（窗口/截图/输入）(参考 https://github.com/Hello-Mr-Crab/pywechat/blob/main/Weixin4.0.md)
│
├─ perception/
│  ├─ ocr.py                   # OCR封装
│  ├─ detector.py              # YOLO/UI检测封装
│  ├─ layout.py                # 布局切分
│  └─ semantic_parser.py       # 语义对象抽取
│
├─ actions/
│  ├─ base.py                  # 动作接口
│  ├─ common.py                # click/type/paste/wait
│  ├─ search_contact.py        # 搜索联系人动作
│  ├─ open_chat.py             # 打开会话动作
│  ├─ send_message.py          # 发消息动作
│  └─ verify.py                # 校验动作
│
├─ recovery/
│  ├─ retry.py                 # 重试策略
│  └─ fallback.py              # 兜底逻辑
│
├─ storage/
│  ├─ logger.py                # 日志
│  ├─ replay.py                # 回放
│  └─ db.py                    # sqlite
│
├─ prompts/
│  └─ reply_prompt.py          # 后续自动回复用
│
├─ tests/
│  ├─ test_state.py
│  ├─ test_parser.py
│  └─ test_actions.py
│
└─ assets/
   ├─ screenshots/
   ├─ samples/
   └─ models/



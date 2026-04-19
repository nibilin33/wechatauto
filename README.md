# wechatauto
目标是：

自动找到联系人 / 群聊
读取最近消息
自动回复
执行一些固定动作：发文字、点按钮、切换会话、搜索联系人
尽量减少纯坐标点击，提升 UI 改版后的可维护性

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
│  ├─ mac_window.py            # 窗口定位/前台激活
│  ├─ mac_input.py             # 鼠标、键盘、粘贴
│  ├─ mac_screen.py            # 截图
│  └─ mac_accessibility.py     # 可访问性能力（可先留空壳）
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
# YOLO UI 检测：数据标注、训练与导出

本文给出一套最小可用的流程，把微信 PC UI 的关键控件（如 `search` / `send`）训练成 YOLO 检测模型，并接入本项目的 `--yolo-model`。

## 1) 数据格式（YOLO Detect）

一张图对应一个同名标签文件：
- `images/train/xxx.png` ↔ `labels/train/xxx.txt`
- `images/val/xxx.png` ↔ `labels/val/xxx.txt`

标签文件每行一个目标：
```
class_id x_center y_center width height
```
其中坐标均为 0~1 的相对值（按整张图宽高归一化）。

## 2) 类别建议（v1 闭环）

最小闭环先做两个类：
- `search`：搜索入口/放大镜图标/搜索框图标
- `send`：发送按钮（图标或按钮局部）

后续扩展可加：`back`、`close`、`more`、`plus`、`emoji`、`voice`、`input_box` 等。

## 3) 数据集目录结构（Ultralytics 兼容）

建议使用：
- `datasets/wechat_ui/images/train/*.png`
- `datasets/wechat_ui/images/val/*.png`
- `datasets/wechat_ui/labels/train/*.txt`
- `datasets/wechat_ui/labels/val/*.txt`

`datasets/wechat_ui/data.yaml` 例子：
```yaml
path: datasets/wechat_ui
train: images/train
val: images/val
names:
  0: search
  1: send
```

## 4) 从运行截图快速建数据集

项目运行会产出 `runs/<run_id>/shots/*.png`。可用脚本把截图汇总并按比例切分：
```
python3 scripts/dataset_from_runs.py --runs runs --out datasets/wechat_ui --names search,send --val-ratio 0.15
```

然后用标注工具（CVAT/labelImg 等）对 `images/*` 进行框标注，导出 YOLO txt 到 `labels/*`。

## 5) 训练（Ultralytics）

安装：
```
pip install ultralytics
```

训练（小目标建议 imgsz 大一点）：
```
yolo task=detect mode=train model=yolov8n.pt data=datasets/wechat_ui/data.yaml imgsz=1280 epochs=100 batch=8
```

训练产物（默认）：
- `runs/detect/train/weights/best.pt`

## 6) 导出（pt / onnx）

导出 ONNX：
```
yolo mode=export model=runs/detect/train/weights/best.pt format=onnx opset=17 imgsz=1280
```

## 7) 接入本项目

运行时指定：
```
python3 -m wechat_agent.app.main --platform macos --contact 你的联系人 --recent 5 --yolo-model /path/to/best.pt
```

事件日志里会出现 `UiElementsDetected`（source=yolo），供回放与排错。


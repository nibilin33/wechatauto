from __future__ import annotations

from wechat_agent.core.models import UiElement
from wechat_agent.perception.vlm_utils import encode_image_data_url, parse_elements_json


def detect_ui_elements_openai(
    image_path: str,
    *,
    model: str | None,
    labels: list[str],
) -> list[UiElement]:
    """
    Use OpenAI vision models to propose UI element bounding boxes.

    Requires `openai` package and `OPENAI_API_KEY` environment variable.
    """

    try:
        from openai import OpenAI  # type: ignore
    except Exception as e:  # noqa: BLE001
        raise RuntimeError("缺少依赖：请安装 `openai`（例如 pip install '.[vlm]'）") from e

    if not model:
        model = "gpt-4.1-mini"

    image_url = encode_image_data_url(image_path)
    prompt = _build_prompt(labels)

    client = OpenAI()
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": image_url}},
                ],
            }
        ],
        response_format={"type": "json_object"},
        temperature=0,
    )
    content = (resp.choices[0].message.content or "") if resp and resp.choices else ""
    return parse_elements_json(content)


def _build_prompt(labels: list[str]) -> str:
    wanted = ", ".join(labels)
    return (
        "你是一个GUI视觉定位器。请在这张微信PC界面截图中，定位指定UI控件的边界框。\n"
        "要求：\n"
        f"- 只返回以下 label：{wanted}\n"
        "- 坐标使用归一化(0~1)，原点在左上角：bbox={x1,y1,x2,y2}\n"
        "- 注意：y 向下增大（左上=0,0；右下=1,1）\n"
        "- 只输出JSON，不要输出解释或多余文本。\n"
        "- 不确定就不要猜，直接省略该元素。\n"
        "输出格式：\n"
        '{"elements":[{"label":"send","score":0.9,"bbox":{"x1":0.7,"y1":0.9,"x2":0.8,"y2":0.96}}]}\n'
    )

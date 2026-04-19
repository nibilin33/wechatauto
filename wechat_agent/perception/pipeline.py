from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import tempfile

from wechat_agent.core.models import SemanticState, UiElement, UiTextBlock
from wechat_agent.perception.layout import Layout, infer_layout, layout_to_debug
from wechat_agent.perception.semantic_parser import parse_semantic
from wechat_agent.perception.detector import detect_ui_elements as detect_templates
from wechat_agent.perception.detector import debug_elements as debug_template_elements
from wechat_agent.perception.llm_fallback import debug_elements as debug_llm_elements
from wechat_agent.perception.llm_fallback import run_llm_fallback
from wechat_agent.perception.ocr import ocr_text_blocks
from wechat_agent.perception.yolo_detector import debug_elements as debug_yolo_elements
from wechat_agent.perception.yolo_detector import detect_ui_elements_yolo
from wechat_agent.perception.vlm_openai import detect_ui_elements_openai
from wechat_agent.perception.vlm_qwen import detect_ui_elements_qwen
from wechat_agent.perception.vlm_utils import debug_elements as debug_vlm_elements
import cv2


@dataclass(frozen=True)
class PerceptionResult:
    texts: list[UiTextBlock]
    elements: list[UiElement]
    layout: Layout
    semantic: SemanticState


def _has_labels(elements: list[UiElement], labels: set[str]) -> bool:
    present = {e.label for e in elements}
    return labels.issubset(present)


def run_perception(
    image_path: str,
    *,
    bus,
    run_id: str,
    template_dir: str | None = None,
    yolo_model: str | None = None,
    llm_fallback_cmd: str | None = None,
    vlm_provider: str | None = None,  # auto|none|cmd|openai|qwen
    openai_model: str | None = None,
    qwen_model: str | None = None,
    qwen_base_url: str | None = None,
    artifacts_dir: str | None = None,
    require_labels: set[str] | None = None,
) -> PerceptionResult:
    texts = ocr_text_blocks(image_path)
    bus.emit(run_id, "OcrCompleted", {"count": len(texts)})

    elements: list[UiElement] = []

    if template_dir:
        tpl = detect_templates(image_path, templates_dir=template_dir)
        if tpl:
            bus.emit(run_id, "UiElementsDetected", {"source": "template", "count": len(tpl), "elements": debug_template_elements(tpl)})
        elements.extend(tpl)

    if yolo_model:
        try:
            yolo_elems = detect_ui_elements_yolo(image_path, model_path=yolo_model)
        except Exception as e:  # noqa: BLE001
            bus.emit(run_id, "UiDetectWarning", {"source": "yolo", "error": repr(e)})
            yolo_elems = []
        if yolo_elems:
            bus.emit(run_id, "UiElementsDetected", {"source": "yolo", "count": len(yolo_elems), "elements": debug_yolo_elements(yolo_elems)})
        elements.extend(yolo_elems)

    layout_pre = infer_layout(texts=texts, elements=elements)

    # VLM fallback only when required labels are still missing.
    provider = (vlm_provider or "auto").lower()
    if provider == "auto":
        provider = "cmd" if llm_fallback_cmd else "none"

    if require_labels and not _has_labels(elements, require_labels) and provider != "none":
        missing = sorted(list(require_labels - {e.label for e in elements}))
        bus.emit(run_id, "VlmFallback", {"provider": provider, "missing": missing})
        vlm_elems: list[UiElement] = []
        src = provider
        try:
            if provider == "cmd":
                if not llm_fallback_cmd:
                    raise RuntimeError("vlm_provider=cmd 但未提供 --llm-fallback-cmd")
                vlm_elems = run_llm_fallback(llm_fallback_cmd, image_path=image_path)
                src = "cmd"
            elif provider == "openai":
                vlm_elems = detect_ui_elements_openai(image_path, model=openai_model, labels=missing)
                src = "openai"
            elif provider == "qwen":
                vlm_elems = detect_ui_elements_qwen(
                    image_path,
                    model=qwen_model,
                    base_url=qwen_base_url,
                    labels=missing,
                )
                src = "qwen"
            else:
                raise RuntimeError(f"Unknown vlm_provider: {provider}")
        except Exception as e:  # noqa: BLE001
            bus.emit(run_id, "UiDetectWarning", {"source": provider, "error": repr(e)})
            vlm_elems = []

        img = cv2.imread(image_path, cv2.IMREAD_COLOR)
        img_h, img_w = (img.shape[:2] if img is not None else (0, 0))

        # Optional zoom-in refinement for VLM coordinates to reduce "layout guessing".
        if provider in {"openai", "qwen"} and img is not None and img_w > 0 and img_h > 0:
            refined: list[UiElement] = []
            for e in vlm_elems:
                refined_e = _refine_vlm_element(
                    provider=provider,
                    element=e,
                    image_path=image_path,
                    image=img,
                    artifacts_dir=artifacts_dir,
                    openai_model=openai_model,
                    qwen_model=qwen_model,
                    qwen_base_url=qwen_base_url,
                )
                refined.append(refined_e or e)
            vlm_elems = refined

        vlm_elems = _validate_vlm_elements(
            vlm_elems,
            layout_pre,
            texts=texts,
            image_w=img_w,
            image_h=img_h,
            allow_labels=require_labels,
        )
        if vlm_elems:
            dbg = debug_llm_elements(vlm_elems) if src == "cmd" else debug_vlm_elements(vlm_elems)
            bus.emit(run_id, "UiElementsDetected", {"source": src, "count": len(vlm_elems), "elements": dbg})
        elements.extend(vlm_elems)
        if require_labels and not _has_labels(elements, require_labels):
            still_missing = sorted(list(require_labels - {e.label for e in elements}))
            bus.emit(run_id, "VlmFallbackRejected", {"provider": provider, "still_missing": still_missing})

    # If template dir exists but no templates, still OK.
    layout = infer_layout(texts=texts, elements=elements)
    bus.emit(run_id, "LayoutInferred", layout_to_debug(layout))

    semantic = parse_semantic(blocks=texts, elements=elements, layout=layout)
    bus.emit(
        run_id,
        "SemanticParsed",
        {
            "page": semantic.page,
            "chat_title": semantic.chat_title,
            "confidence": semantic.confidence,
            "anchors": list(semantic.anchors.keys()),
            "message_count": len(semantic.messages),
        },
    )
    return PerceptionResult(texts=texts, elements=elements, layout=layout, semantic=semantic)


def default_template_dir(os_name: str) -> str:
    return str(Path("assets") / "templates" / os_name)


def _validate_vlm_elements(
    elements: list[UiElement],
    layout: Layout,
    *,
    texts: list[UiTextBlock],
    image_w: int,
    image_h: int,
    allow_labels: set[str],
) -> list[UiElement]:
    out: list[UiElement] = []
    for e in elements:
        if e.label not in allow_labels:
            continue
        best = _best_bbox_variant(e.bbox, label=e.label, layout=layout, texts=texts, image_w=image_w, image_h=image_h)
        if best is None:
            continue
        out.append(UiElement(bbox=best, label=e.label, score=e.score))
    return out


def _intersects(a, b) -> bool:  # noqa: ANN001, ANN202
    return not (a.x2 < b.x1 or a.x1 > b.x2 or a.y2 < b.y1 or a.y1 > b.y2)


def _best_bbox_variant(bbox, *, label: str, layout: Layout, texts: list[UiTextBlock], image_w: int, image_h: int):  # noqa: ANN001, ANN202
    b0 = _normalize_bbox(bbox, image_w=image_w, image_h=image_h)
    candidates = [b0, _flip_y(b0), _flip_x(b0)]

    keyword = "发送" if label == "send" else "搜索" if label == "search" else None
    keyword_blocks = []
    if keyword:
        region = layout.chat_composer if label == "send" else layout.sidebar_top
        keyword_blocks = [t for t in texts if keyword in (t.text or "") and _intersects(t.bbox, region)]

    best = None
    best_score = -1.0
    for b in candidates:
        if b is None:
            continue
        if not (0.0 <= b.x1 < b.x2 <= 1.0 and 0.0 <= b.y1 < b.y2 <= 1.0):
            continue
        area = (b.x2 - b.x1) * (b.y2 - b.y1)
        if area < 0.00005 or area > 0.08:
            continue

        # region sanity
        if label == "send":
            if not _intersects(b, layout.chat_composer):
                continue
            if b.y1 < 0.60:
                continue
        if label == "search":
            if not _intersects(b, layout.sidebar_top):
                continue
            if b.y2 > 0.45:
                continue

        score = 1.0
        if keyword_blocks:
            score += max(_iou(b, t.bbox) for t in keyword_blocks)
        else:
            # Without keyword evidence, prefer closer to typical zone
            cx = (b.x1 + b.x2) / 2.0
            cy = (b.y1 + b.y2) / 2.0
            if label == "send":
                score += 1.0 - abs(cy - 0.92) - abs(cx - 0.88)
            if label == "search":
                score += 1.0 - abs(cy - 0.08) - abs(cx - 0.14)

        if score > best_score:
            best = b
            best_score = score
    return best


def _normalize_bbox(bbox, *, image_w: int, image_h: int):  # noqa: ANN001, ANN202
    # Accept either normalized or pixel coordinates.
    x1, y1, x2, y2 = float(bbox.x1), float(bbox.y1), float(bbox.x2), float(bbox.y2)
    if max(x2, y2, x1, y1) > 1.5 and image_w > 0 and image_h > 0:
        return type(bbox)(x1=x1 / image_w, y1=y1 / image_h, x2=x2 / image_w, y2=y2 / image_h)
    return type(bbox)(x1=x1, y1=y1, x2=x2, y2=y2)


def _flip_y(bbox):  # noqa: ANN001, ANN202
    return type(bbox)(x1=bbox.x1, y1=1.0 - bbox.y2, x2=bbox.x2, y2=1.0 - bbox.y1)


def _flip_x(bbox):  # noqa: ANN001, ANN202
    return type(bbox)(x1=1.0 - bbox.x2, y1=bbox.y1, x2=1.0 - bbox.x1, y2=bbox.y2)


def _iou(a, b) -> float:  # noqa: ANN001, ANN202
    x1 = max(a.x1, b.x1)
    y1 = max(a.y1, b.y1)
    x2 = min(a.x2, b.x2)
    y2 = min(a.y2, b.y2)
    inter_w = max(0.0, x2 - x1)
    inter_h = max(0.0, y2 - y1)
    inter = inter_w * inter_h
    if inter <= 0.0:
        return 0.0
    area_a = max(0.0, a.x2 - a.x1) * max(0.0, a.y2 - a.y1)
    area_b = max(0.0, b.x2 - b.x1) * max(0.0, b.y2 - b.y1)
    denom = area_a + area_b - inter
    return inter / denom if denom > 0 else 0.0


def _refine_vlm_element(  # noqa: ANN001, ANN202
    *,
    provider: str,
    element: UiElement,
    image_path: str,
    image,
    artifacts_dir: str | None,
    openai_model: str | None,
    qwen_model: str | None,
    qwen_base_url: str | None,
) -> UiElement | None:
    """
    Two-pass VLM refinement:
    - Use coarse bbox (from full image) to crop a zoomed region.
    - Ask VLM again on the crop to return a tighter bbox for the same label.
    """

    h, w = image.shape[:2]
    b = element.bbox
    b = _normalize_bbox(b, image_w=w, image_h=h)
    if not (0.0 <= b.x1 < b.x2 <= 1.0 and 0.0 <= b.y1 < b.y2 <= 1.0):
        return None

    margin = 0.10
    x1 = max(0, int((b.x1 - margin) * w))
    y1 = max(0, int((b.y1 - margin) * h))
    x2 = min(w, int((b.x2 + margin) * w))
    y2 = min(h, int((b.y2 + margin) * h))
    if x2 - x1 < 20 or y2 - y1 < 20:
        return None

    crop = image[y1:y2, x1:x2]
    if artifacts_dir:
        out_dir = Path(artifacts_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        crop_path = str(out_dir / f"vlm_crop_{provider}_{element.label}.png")
    else:
        fd, crop_path = tempfile.mkstemp(prefix=f"vlm_crop_{provider}_{element.label}_", suffix=".png")
        Path(crop_path).unlink(missing_ok=True)  # close+overwrite via cv2
        try:
            import os

            os.close(fd)
        except Exception:
            pass

    ok = cv2.imwrite(crop_path, crop)
    if not ok:
        return None

    # Ask the VLM to locate the same label in the zoomed crop.
    try:
        if provider == "openai":
            elems = detect_ui_elements_openai(crop_path, model=openai_model, labels=[element.label])
        elif provider == "qwen":
            elems = detect_ui_elements_qwen(
                crop_path,
                model=qwen_model,
                base_url=qwen_base_url,
                labels=[element.label],
            )
        else:
            return None
    except Exception:
        return None

    if not elems:
        return None
    # pick best score
    elems.sort(key=lambda e: e.score, reverse=True)
    eb = elems[0].bbox
    eb = _normalize_bbox(eb, image_w=(x2 - x1), image_h=(y2 - y1))
    if not (0.0 <= eb.x1 < eb.x2 <= 1.0 and 0.0 <= eb.y1 < eb.y2 <= 1.0):
        return None

    # map crop-normalized back to full-normalized
    fx1 = (x1 + eb.x1 * (x2 - x1)) / w
    fy1 = (y1 + eb.y1 * (y2 - y1)) / h
    fx2 = (x1 + eb.x2 * (x2 - x1)) / w
    fy2 = (y1 + eb.y2 * (y2 - y1)) / h
    return UiElement(bbox=type(b)(x1=fx1, y1=fy1, x2=fx2, y2=fy2), label=element.label, score=element.score)

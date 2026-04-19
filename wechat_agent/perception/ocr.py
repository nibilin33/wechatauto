from __future__ import annotations

from dataclasses import asdict

import objc
from Foundation import NSBundle, NSURL

from wechat_agent.core.models import UiTextBlock
from wechat_agent.perception.bbox import vision_rect_to_bbox


_VISION_BUNDLE_PATH = "/System/Library/Frameworks/Vision.framework"


def _load_vision():
    bundle = NSBundle.bundleWithPath_(_VISION_BUNDLE_PATH)
    if not bundle or not bundle.load():
        raise RuntimeError("Failed to load Vision.framework")
    recognize_cls = objc.lookUpClass("VNRecognizeTextRequest")
    handler_cls = objc.lookUpClass("VNImageRequestHandler")
    return recognize_cls, handler_cls


def ocr_text_blocks(
    image_path: str,
    *,
    languages: list[str] | None = None,
    min_confidence: float = 0.3,
) -> list[UiTextBlock]:
    """
    OCR a PNG/JPG screenshot using macOS Vision.framework (no external deps).

    Returns text blocks with normalized bbox (0..1) in top-left origin.
    """

    if languages is None:
        languages = ["zh-Hans", "en-US"]

    VNRecognizeTextRequest, VNImageRequestHandler = _load_vision()

    # Use the no-arg initializer to avoid passing a Python callable as an ObjC
    # block (PyObjC raises "Argument 2 is a block, but no signature available"
    # when the block type encoding isn't registered). Results are available via
    # request.results() after the synchronous performRequests_error_ call.
    request = VNRecognizeTextRequest.new()
    request.setUsesLanguageCorrection_(False)
    request.setRecognitionLanguages_(languages)

    url = NSURL.fileURLWithPath_(image_path)
    image_handler = VNImageRequestHandler.alloc().initWithURL_options_(url, None)
    # When Vision.framework is loaded via NSBundle (no bridge-support metadata),
    # PyObjC may return a plain bool instead of (bool, NSError*).
    ret = image_handler.performRequests_error_([request], None)
    ok = ret[0] if isinstance(ret, (tuple, list)) else ret
    if not ok:
        raise RuntimeError("Vision OCR failed")

    blocks: list[UiTextBlock] = []
    for obs in (request.results() or []):
        try:
            candidates = obs.topCandidates_(1)
            if not candidates:
                continue
            candidate = candidates[0]
            text = str(candidate.string() or "").strip()
            score = float(candidate.confidence())
            if not text or score < min_confidence:
                continue
            bbox = vision_rect_to_bbox(obs.boundingBox())
            blocks.append(UiTextBlock(bbox=bbox, text=text, score=score))
        except Exception:  # noqa: BLE001
            pass
    return blocks


def debug_blocks(blocks: list[UiTextBlock]) -> list[dict]:
    return [{"bbox": asdict(b.bbox), "text": b.text, "score": b.score} for b in blocks]


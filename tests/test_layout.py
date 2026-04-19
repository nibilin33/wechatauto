import unittest

from wechat_agent.core.models import BBox, UiElement, UiTextBlock
from wechat_agent.perception.layout import infer_layout


class TestLayoutInfer(unittest.TestCase):
    def test_infer_sidebar_from_search(self):
        elements = [UiElement(bbox=BBox(0.18, 0.05, 0.22, 0.09), label="search", score=0.9)]
        layout = infer_layout(texts=[], elements=elements)
        self.assertGreater(layout.sidebar.x2, 0.20)
        self.assertLess(layout.sidebar.x2, 0.40)

    def test_infer_composer_from_send(self):
        elements = [UiElement(bbox=BBox(0.88, 0.90, 0.94, 0.96), label="send", score=0.9)]
        layout = infer_layout(texts=[], elements=elements)
        self.assertGreater(layout.chat_composer.y1, 0.70)
        self.assertLess(layout.chat_composer.y1, 0.90)

    def test_infer_header_from_title_text(self):
        texts = [UiTextBlock(bbox=BBox(0.40, 0.03, 0.62, 0.08), text="张三", score=0.9)]
        layout = infer_layout(texts=texts, elements=[])
        self.assertGreater(layout.chat_header.y2, 0.10)
        self.assertLess(layout.chat_header.y2, 0.22)


if __name__ == "__main__":
    unittest.main()


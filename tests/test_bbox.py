import unittest

from wechat_agent.perception.bbox import vision_rect_to_bbox


class _Rect:
    class _P:
        def __init__(self, x, y):
            self.x = x
            self.y = y

    class _S:
        def __init__(self, w, h):
            self.width = w
            self.height = h

    def __init__(self, x, y, w, h):
        self.origin = self._P(x, y)
        self.size = self._S(w, h)


class TestVisionRectToBBox(unittest.TestCase):
    def test_flip_y(self):
        # Vision origin bottom-left: rect at y=0.0 with height 0.2 occupies bottom.
        rect = _Rect(0.1, 0.0, 0.3, 0.2)
        bbox = vision_rect_to_bbox(rect)
        self.assertAlmostEqual(bbox.x1, 0.1)
        self.assertAlmostEqual(bbox.x2, 0.4)
        # In top-left origin, this becomes y in [0.8, 1.0]
        self.assertAlmostEqual(bbox.y1, 0.8)
        self.assertAlmostEqual(bbox.y2, 1.0)


if __name__ == "__main__":
    unittest.main()


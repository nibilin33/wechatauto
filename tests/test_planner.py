import unittest

from wechat_agent.core.planner import plan_closed_loop


class TestPlanner(unittest.TestCase):
    def test_plan_without_send(self):
        plan = plan_closed_loop("Alice", 5, "hi", send=False)
        self.assertEqual([a.name for a in plan.actions], ["search_contact", "open_chat", "read_recent"])

    def test_plan_with_send(self):
        plan = plan_closed_loop("Alice", 5, "hi", send=True)
        self.assertEqual(
            [a.name for a in plan.actions],
            ["search_contact", "open_chat", "read_recent", "send_message", "verify_sent"],
        )


if __name__ == "__main__":
    unittest.main()


import unittest

from wechat_agent.core.runner import _planned_actions_for_platform
from wechat_agent.core.task import ActionSpec, TaskPlan


class TestRunnerPlanning(unittest.TestCase):
    def test_windows_plan_prepends_uia_self_check(self):
        plan = TaskPlan(goal="closed_loop", actions=[ActionSpec("search_contact", {"name": "Alice"})])

        out = _planned_actions_for_platform(platform_name="windows", plan=plan)

        self.assertEqual([action.name for action in out.actions], ["uia_self_check", "search_contact"])

    def test_non_windows_plan_is_unchanged(self):
        plan = TaskPlan(goal="closed_loop", actions=[ActionSpec("search_contact", {"name": "Alice"})])

        out = _planned_actions_for_platform(platform_name="macos", plan=plan)

        self.assertEqual([action.name for action in out.actions], ["search_contact"])


if __name__ == "__main__":
    unittest.main()
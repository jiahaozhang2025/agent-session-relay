import importlib.util
from pathlib import Path
import unittest

SPEC = importlib.util.spec_from_file_location("cadence", Path(__file__).resolve().parents[1] / "scripts" / "cadence.py")
cadence = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cadence)


class CadenceTests(unittest.TestCase):
    def test_both_agents_default_to_six_hours(self):
        for runtime in ("codex", "claude"):
            self.assertEqual(cadence.cadence_hours({}, runtime), 6)

    def test_shared_setting_changes_both(self):
        for runtime in ("codex", "claude"):
            self.assertEqual(cadence.cadence_hours({"cadence_hours": 12}, runtime), 12)

    def test_override_changes_only_selected_agent(self):
        config = {"cadence_hours": 6, "cadence_overrides_hours": {"claude": 2}}
        self.assertEqual(cadence.cadence_hours(config, "claude"), 2)
        self.assertEqual(cadence.cadence_hours(config, "codex"), 6)

    def test_bad_intervals_are_rejected(self):
        for value in (0, -1, True, "6", float("nan"), float("inf"), 0.001):
            with self.subTest(value=value), self.assertRaises(ValueError):
                cadence.cadence_hours({"cadence_hours": value}, "claude")

    def test_unknown_agent_override_is_rejected(self):
        with self.assertRaises(ValueError):
            cadence.cadence_hours({"cadence_overrides_hours": {"cluade": 2}}, "claude")


if __name__ == "__main__":
    unittest.main()

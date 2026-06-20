import unittest
import sys
import os

# Adjust paths to match project structure
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agent.core import GROQ_TOOLS

class TestGroqToolSchema(unittest.TestCase):
    """
    Schema validation tests for GROQ_TOOLS.
    These tests replace the old get_tool_subset routing tests (function removed).
    They verify the tool registry is structurally correct so agent calls won't fail.
    """

    # --- Expected tool names in the registry ---
    EXPECTED_TOOLS = {
        "check_gmail_inbox",
        "get_gmail_briefing",
        "get_smart_email_notifications",
        "start_spotify_playback",
        "search_and_play_spotify",
        "pause_spotify",
        "resume_spotify",
        "next_spotify_track",
        "set_reminder",
        "get_active_reminders",
        "manage_calendar",
        "send_neural_push",
        "generate_morning_briefing",
    }

    def test_groq_tools_is_nonempty_list(self):
        """GROQ_TOOLS must be a non-empty list so Groq API calls don't receive empty tool sets."""
        self.assertIsInstance(GROQ_TOOLS, list)
        self.assertGreater(len(GROQ_TOOLS), 0, "GROQ_TOOLS should not be empty")

    def test_all_expected_tools_present(self):
        """Every expected tool name must appear in GROQ_TOOLS."""
        registered_names = {t["function"]["name"] for t in GROQ_TOOLS}
        missing = self.EXPECTED_TOOLS - registered_names
        self.assertSetEqual(
            missing, set(),
            f"These expected tools are missing from GROQ_TOOLS: {missing}"
        )

    def test_each_tool_has_required_schema_fields(self):
        """Every entry must have 'type', 'function.name', 'function.description', 'function.parameters'."""
        for tool in GROQ_TOOLS:
            name = tool.get("function", {}).get("name", "<unknown>")
            with self.subTest(tool=name):
                self.assertEqual(tool.get("type"), "function", f"{name}: 'type' must be 'function'")
                fn = tool.get("function")
                self.assertIsInstance(fn, dict, f"{name}: 'function' key must be a dict")
                self.assertIn("name", fn, f"{name}: missing 'function.name'")
                self.assertIn("description", fn, f"{name}: missing 'function.description'")
                self.assertIn("parameters", fn, f"{name}: missing 'function.parameters'")
                self.assertIsInstance(fn["description"], str, f"{name}: description must be a string")
                self.assertGreater(len(fn["description"]), 0, f"{name}: description must not be empty")

    def test_tool_names_are_unique(self):
        """Duplicate tool names would cause Groq API schema conflicts."""
        names = [t["function"]["name"] for t in GROQ_TOOLS]
        self.assertEqual(len(names), len(set(names)), f"Duplicate tool names found: {names}")

    def test_required_fields_are_lists(self):
        """Where 'required' exists in parameters, it must be a list."""
        for tool in GROQ_TOOLS:
            fn = tool.get("function", {})
            params = fn.get("parameters", {})
            required = params.get("required")
            name = fn.get("name", "<unknown>")
            if required is not None:
                with self.subTest(tool=name):
                    self.assertIsInstance(required, list, f"{name}: 'required' must be a list")


if __name__ == "__main__":
    unittest.main()

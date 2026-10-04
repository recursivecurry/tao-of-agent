import json
import subprocess
import unittest
from pathlib import Path

HOOKS = Path(__file__).resolve().parent.parent / "src/plugin/hooks"


class SessionStartTest(unittest.TestCase):
    def test_prints_the_context_file_as_hook_json(self) -> None:
        result = subprocess.run(
            [HOOKS / "session-start.sh"], check=True, capture_output=True, text=True
        )
        output = json.loads(result.stdout)["hookSpecificOutput"]
        self.assertEqual(output["hookEventName"], "SessionStart")
        context = (HOOKS / "session-context.md").read_text().rstrip("\n")
        self.assertEqual(output["additionalContext"], context)


if __name__ == "__main__":
    unittest.main()

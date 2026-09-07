"""Tests for the optional Codex cache-meter hook."""

import contextlib
import importlib.util
import io
import json
import sys
import unittest
from unittest import mock
from datetime import datetime
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
HOOK_PATH = REPOSITORY_ROOT / "hooks" / "cache-meter" / "cache-meter.py"

spec = importlib.util.spec_from_file_location("cache_meter", HOOK_PATH)
cache_meter = importlib.util.module_from_spec(spec)
sys.modules["cache_meter"] = cache_meter
spec.loader.exec_module(cache_meter)


class CacheMeterTimestampTests(unittest.TestCase):
    def test_timestamp_uses_requested_local_format(self):
        timestamp = cache_meter.current_local_timestamp(
            datetime(2026, 9, 7, 18, 59, 52)
        )
        self.assertEqual("2026-09-07 18:59:52", timestamp)

    def test_usage_summary_ends_with_hook_generation_time(self):
        transcript = REPOSITORY_ROOT / "hooks" / "cache-meter" / "example-rollout.jsonl"
        stdout = io.StringIO()
        with mock.patch.object(
            cache_meter, "current_local_timestamp", return_value="2026-09-07 18:59:52"
        ):
            with contextlib.redirect_stdout(stdout):
                with self.assertRaises(SystemExit):
                    cache_meter.main(
                        json.dumps({"transcript_path": str(transcript)})
                    )

        output = json.loads(stdout.getvalue())
        message = output["systemMessage"]
        self.assertEqual("时间：2026-09-07 18:59:52", message.rsplit("\n", 1)[1])


if __name__ == "__main__":
    unittest.main()

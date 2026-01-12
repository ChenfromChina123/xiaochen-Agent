import unittest
import os
import json
import shutil
from unittest import mock
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from xiaochen_agent_v2.utils import logs

class TestLogSlidingWindow(unittest.TestCase):
    def setUp(self):
        self.test_dir = "test_temp_logs"
        os.makedirs(self.test_dir, exist_ok=True)
        self.history_file = os.path.join(self.test_dir, "test_usage.jsonl")

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_sliding_window(self):
        # Set a small limit for testing
        with mock.patch("xiaochen_agent_v2.utils.logs.MAX_USAGE_HISTORY_LINES", 5):
            # Append 10 records
            for i in range(10):
                logs.append_usage_history(
                    usage={"tokens": i},
                    history_file=self.history_file
                )
            
            # Check content
            with open(self.history_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
            
            self.assertEqual(len(lines), 5, "Should keep only 5 lines")
            
            # Verify the content is the last 5 records (5 to 9)
            first_record = json.loads(lines[0])
            last_record = json.loads(lines[-1])
            
            self.assertEqual(first_record["usage"]["tokens"], 5)
            self.assertEqual(last_record["usage"]["tokens"], 9)

if __name__ == "__main__":
    unittest.main()

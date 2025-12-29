import os
import tempfile
import unittest
import json

from xiaochen_agent_v2.utils.files import edit_lines, read_lines_robust, read_range_numbered
from xiaochen_agent_v2.utils.tags import parse_stack_of_tags
from xiaochen_agent_v2.core.session import SessionManager


class TestEditLinesAlignment(unittest.TestCase):
    """覆盖 edit_lines 的行号对齐与删除/插入组合场景。"""

    def test_delete_then_insert_after_deleted_range_keeps_original_line_reference(self) -> None:
        """insert_at 在删除区间之后时，应按原始行号对齐到期望位置。"""
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "demo.txt")
            with open(path, "w", encoding="utf-8") as f:
                f.write("\n".join([f"A{i}" for i in range(1, 11)]))

            _before, after = edit_lines(
                path_of_file=path,
                delete_start=3,
                delete_end=4,
                insert_at=6,
                auto_indent=False,
                content="X\nY",
            )
            with open(path, "w", encoding="utf-8") as f:
                f.write(after)

            lines = read_lines_robust(path)
            self.assertEqual(
                lines,
                ["A1", "A2", "A5", "X", "Y", "A6", "A7", "A8", "A9", "A10"],
            )

    def test_insert_within_deleted_range_inserts_at_delete_start(self) -> None:
        """insert_at 落在删除区间内时，应默认插入到删除起始行位置。"""
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "demo.txt")
            with open(path, "w", encoding="utf-8") as f:
                f.write("\n".join([f"A{i}" for i in range(1, 8)]))

            _before, after = edit_lines(
                path_of_file=path,
                delete_start=3,
                delete_end=5,
                insert_at=4,
                auto_indent=False,
                content="X",
            )
            with open(path, "w", encoding="utf-8") as f:
                f.write(after)

            lines = read_lines_robust(path)
            self.assertEqual(lines, ["A1", "A2", "X", "A6", "A7"])

    def test_python_header_replace_does_not_duplicate_module_header(self) -> None:
        """Python 顶部替换时，应避免把旧模块头部残留导致重复。"""
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "demo.py")
            original = "\n".join(
                [
                    "#!/usr/bin/env python3",
                    "# -*- coding: utf-8 -*-",
                    "\"\"\"",
                    "旧模块说明",
                    "\"\"\"",
                    "",
                    "def f():",
                    "    return 1",
                ]
            )
            with open(path, "w", encoding="utf-8") as f:
                f.write(original)

            new_header = "\n".join(
                [
                    "#!/usr/bin/env python3",
                    "# -*- coding: utf-8 -*-",
                    "\"\"\"",
                    "新模块说明",
                    "\"\"\"",
                ]
            )

            _before, after = edit_lines(
                path_of_file=path,
                delete_start=1,
                delete_end=1,
                insert_at=1,
                auto_indent=False,
                content=new_header,
            )
            with open(path, "w", encoding="utf-8") as f:
                f.write(after)

            lines = read_lines_robust(path)
            self.assertIn("新模块说明", "\n".join(lines))
            self.assertNotIn("旧模块说明", "\n".join(lines))
            self.assertEqual(sum(1 for l in lines if l.strip() == '"""'), 2)
            self.assertEqual(lines.count("# -*- coding: utf-8 -*-"), 1)


class TestTaskTagParsing(unittest.TestCase):
    """覆盖 task_add/task_update 的解析兼容性。"""

    def test_task_add_accepts_raw_inner_text(self) -> None:
        """task_add 没有 <content> 子标签时，仍应解析为任务内容。"""
        text = "<task_add>修复命令行模型切换</task_add>"
        tasks = parse_stack_of_tags(text)
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0]["type"], "task_add")
        self.assertEqual(tasks[0]["content"], "修复命令行模型切换")

    def test_task_add_rejects_unclosed_content_tag(self) -> None:
        text = "<task_add><content>未闭合</task_add>"
        tasks = parse_stack_of_tags(text)
        self.assertEqual(tasks, [])

    def test_run_command_rejects_unclosed_command_tag(self) -> None:
        text = "<run_command><command>echo 1</run_command>"
        tasks = parse_stack_of_tags(text)
        self.assertEqual(tasks, [])

    def test_read_file_rejects_missing_range(self) -> None:
        text = "<read_file><path>a.py</path></read_file>"
        tasks = parse_stack_of_tags(text)
        self.assertEqual(tasks, [])

    def test_read_file_parses_required_range(self) -> None:
        text = "<read_file><path>a.py</path><start_line>10</start_line><end_line>20</end_line></read_file>"
        tasks = parse_stack_of_tags(text)
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0]["type"], "read_file")
        self.assertEqual(tasks[0]["path"], "a.py")
        self.assertEqual(tasks[0]["start_line"], 10)
        self.assertEqual(tasks[0]["end_line"], 20)

    def test_replace_in_file_parses_basic_fields(self) -> None:
        text = (
            "<replace_in_file>"
            "<path>a.py</path>"
            "<search>old</search>"
            "<replace>new</replace>"
            "<count>2</count>"
            "<regex>false</regex>"
            "<auto_indent>true</auto_indent>"
            "</replace_in_file>"
        )
        tasks = parse_stack_of_tags(text)
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0]["type"], "replace_in_file")
        self.assertEqual(tasks[0]["path"], "a.py")
        self.assertEqual(tasks[0]["search"], "old")
        self.assertEqual(tasks[0]["replace"], "new")
        self.assertEqual(tasks[0]["count"], 2)
        self.assertEqual(tasks[0]["regex"], False)
        self.assertEqual(tasks[0]["auto_indent"], True)


class TestSessionTitle(unittest.TestCase):
    """覆盖会话标题生成与默认回退逻辑。"""

    def test_list_sessions_uses_title_when_present(self) -> None:
        """存在 title 字段时，应直接展示 title。"""
        with tempfile.TemporaryDirectory() as td:
            sm = SessionManager(sessions_dir=td)
            filename = sm.create_autosave_session()
            path = os.path.join(td, filename)
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            data["title"] = "测试标题"
            data["messages"] = [
                {"role": "system", "content": ["sys"]},
                {"role": "user", "content": ["hello"]},
            ]
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            sessions = sm.list_sessions(limit=10)
            self.assertEqual(len(sessions), 1)
            self.assertEqual(sessions[0]["title"], "测试标题")

    def test_list_sessions_falls_back_to_first_user_input(self) -> None:
        """没有 title 时，应回退到首条用户输入作为标题。"""
        with tempfile.TemporaryDirectory() as td:
            sm = SessionManager(sessions_dir=td)
            filename = sm.create_autosave_session()
            path = os.path.join(td, filename)
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            data["title"] = ""
            data["first_user_input"] = ""
            data["messages"] = [
                {"role": "system", "content": ["sys"]},
                {"role": "user", "content": ["第一句话", "第二行"]},
            ]
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            sessions = sm.list_sessions(limit=10)
            self.assertEqual(len(sessions), 1)
            self.assertEqual(sessions[0]["title"], "第一句话")


class TestReadIndentHeader(unittest.TestCase):
    def test_read_range_numbered_header_mode_emits_single_header(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "demo.py")
            with open(path, "w", encoding="utf-8") as f:
                f.write("def f():\n    return 1\n")
            _total, _end, content = read_range_numbered(path, 1, None, indent_mode="header")
            self.assertTrue(content.splitlines()[0].startswith("indent_style:"))
            self.assertNotIn("[s=", content)


class TestOptionalRuffDetection(unittest.TestCase):
    def test_detect_ruff_runner_returns_none_when_missing(self) -> None:
        from unittest import mock
        from xiaochen_agent_v2.core.config import Config
        from xiaochen_agent_v2.core.agent import Agent

        cfg = Config(apiKey="x", baseUrl="http://x", modelName="m")
        agent = Agent(cfg)
        agent.pythonValidateRuff = "auto"
        with mock.patch("shutil.which", return_value=None):
            with mock.patch("subprocess.run") as run:
                run.return_value.returncode = 1
                runner = agent._detect_ruff_runner()
                self.assertIsNone(runner)


class TestHistoryCompaction(unittest.TestCase):
    def test_compact_history_inserts_persistent_summary_and_keeps_tail(self) -> None:
        from unittest import mock
        from xiaochen_agent_v2.core.config import Config
        from xiaochen_agent_v2.core.agent import Agent

        cfg = Config(apiKey="x", baseUrl="http://x", modelName="m", tokenThreshold=10)
        agent = Agent(cfg)
        msg_system = {"role": "system", "content": "sys"}
        history = [
            {"role": "user", "content": "u1 " * 50},
            {"role": "assistant", "content": "a1 " * 50},
            {"role": "user", "content": "u2 " * 50},
            {"role": "assistant", "content": "a2 " * 50},
        ]
        with mock.patch.object(agent, "_generate_summary_via_model", return_value="SUM"):
            new_history, did = agent._maybe_compact_history(history, msg_system, keep_last_messages=2)
        self.assertTrue(did)
        self.assertEqual(new_history[0]["role"], "system")
        self.assertTrue(str(new_history[0]["content"]).startswith("【长期摘要】"))
        self.assertEqual(new_history[1:], history[-2:])

    def test_compact_history_replaces_existing_persistent_summary(self) -> None:
        from unittest import mock
        from xiaochen_agent_v2.core.config import Config
        from xiaochen_agent_v2.core.agent import Agent

        cfg = Config(apiKey="x", baseUrl="http://x", modelName="m", tokenThreshold=10)
        agent = Agent(cfg)
        msg_system = {"role": "system", "content": "sys"}
        history = [
            {"role": "system", "content": "【长期摘要】\nOLD"},
            {"role": "user", "content": "u1 " * 50},
            {"role": "assistant", "content": "a1 " * 50},
            {"role": "user", "content": "u2 " * 50},
            {"role": "assistant", "content": "a2 " * 50},
        ]
        with mock.patch.object(agent, "_generate_summary_via_model", return_value="NEW"):
            new_history, did = agent._maybe_compact_history(history, msg_system, keep_last_messages=2)
        self.assertTrue(did)
        self.assertEqual(new_history[0]["role"], "system")
        self.assertIn("NEW", str(new_history[0]["content"]))
        self.assertNotIn("OLD", str(new_history[0]["content"]))
        self.assertEqual(new_history[1:], history[-2:])


if __name__ == "__main__":
    unittest.main()

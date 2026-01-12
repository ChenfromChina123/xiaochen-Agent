import sys
import os
import time
from dataclasses import dataclass, field
from typing import Dict, Optional, List

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from xiaochen_agent_v2.ui.cli import _resolve_terminal_id, _get_sorted_terminals

@dataclass
class MockProcess:
    pid: int

@dataclass
class MockTerminal:
    id: str
    process: MockProcess
    start_time: float

class MockTerminalManager:
    def __init__(self):
        self.terminals: Dict[str, MockTerminal] = {}

def test_resolve_terminal_id():
    manager = MockTerminalManager()
    
    # Create 3 terminals with different start times
    t1 = MockTerminal(id="uuid1", process=MockProcess(pid=1001), start_time=100.0)
    t2 = MockTerminal(id="uuid2", process=MockProcess(pid=1002), start_time=200.0)
    t3 = MockTerminal(id="uuid3", process=MockProcess(pid=1003), start_time=300.0)
    
    manager.terminals = {
        "uuid1": t1,
        "uuid2": t2,
        "uuid3": t3
    }
    
    # Test sorting
    sorted_terms = _get_sorted_terminals(manager)
    print("Sorted terminals:", [t[0] for t in sorted_terms])
    assert len(sorted_terms) == 3
    assert sorted_terms[0][0] == "uuid1"
    assert sorted_terms[1][0] == "uuid2"
    assert sorted_terms[2][0] == "uuid3"
    
    # Test simple ID resolution
    assert _resolve_terminal_id(manager, "1") == "uuid1"
    assert _resolve_terminal_id(manager, "2") == "uuid2"
    assert _resolve_terminal_id(manager, "3") == "uuid3"
    
    # Test invalid simple ID
    assert _resolve_terminal_id(manager, "4") is None
    assert _resolve_terminal_id(manager, "0") is None
    
    # Test UUID resolution
    assert _resolve_terminal_id(manager, "uuid1") == "uuid1"
    
    # Test PID resolution
    assert _resolve_terminal_id(manager, "1001") == "uuid1" # "1001" could be interpreted as index 1001 or PID.
    # The logic checks simple ID first. 1001 is > 3, so not a valid index. Then checks PID.
    assert _resolve_terminal_id(manager, "1002") == "uuid2"
    
    # Test what if PID collides with simple ID?
    # e.g. PID is 2. Simple ID 2 maps to uuid2.
    # Logic:
    # 1. Check if digit. Yes.
    # 2. Check if simple ID (1 <= idx <= len). If yes, return simple ID match.
    # So if user types "2", and there are >= 2 terminals, it resolves to 2nd terminal.
    # If user meant PID 2, they can't access it via "2" if there are >= 2 terminals.
    # This is an acceptable trade-off for convenience, or we should check if PID exists first?
    # User requested: "ps以列表的形式列出字进程信息，然后有一个简单的id（1、2、3）watch和kill命令可以直接使用简单id作为参数"
    # So simple ID takes precedence.
    
    t4 = MockTerminal(id="uuid4", process=MockProcess(pid=1), start_time=400.0)
    manager.terminals["uuid4"] = t4
    # Now we have 4 terminals. Index 1 is uuid1. PID 1 is uuid4.
    # Input "1" -> should be uuid1 (Simple ID).
    assert _resolve_terminal_id(manager, "1") == "uuid1"
    
    print("All tests passed!")

if __name__ == "__main__":
    test_resolve_terminal_id()
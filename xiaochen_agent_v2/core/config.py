from dataclasses import dataclass, field
from typing import List


@dataclass
class Config:
    apiKey: str
    baseUrl: str
    modelName: str
    maxCycles: int = 30
    tokenThreshold: int = 30000
    stopAfterFirstToolExecution: bool = False
    verifySsl: bool = True
    whitelistedTools: List[str] = field(
        default_factory=lambda: [
            "search_files",
            "search_in_files",
            "read_file",
            "task_add",
            "task_update",
            "task_delete",
            "task_list",
            "task_clear",
        ]
    )
    whitelistedCommands: List[str] = field(default_factory=lambda: ["ls", "dir", "pwd", "whoami", "echo", "cat", "type"])

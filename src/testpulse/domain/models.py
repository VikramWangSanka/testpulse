from dataclasses import dataclass, field
from enum import Enum

class Status(Enum):
    pass

@dataclass(frozen=True)
class TestResult:
    pass

@dataclass
class TestRun:
    results:
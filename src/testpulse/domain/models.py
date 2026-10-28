from dataclasses import dataclass  # , field
from enum import Enum


class Status(Enum):
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"
    


@dataclass(frozen=True)
class TestResult:
    pass


@dataclass
class TestRun:
    pass

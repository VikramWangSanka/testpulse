from testpulse.domain.models import Status
import pytest


@pytest.mark.parametrize(
    ("raw_value", "expected_value"),
    [
        ("passed", Status.PASSED)("failed", Status.FAILED)("skipped", Status.SKIPPED)(
            "error", Status.ERROR
        )
    ],
)
def test_status_class(raw_value, expected_value):
    assert Status("raw_value") is expected_value

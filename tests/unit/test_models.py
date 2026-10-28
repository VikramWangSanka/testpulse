import pytest

from testpulse.domain.models import Status


@pytest.mark.parametrize(
    ("raw_value", "expected_value"),
    [
        ("passed", Status.PASSED),
        ("failed", Status.FAILED),
        ("skipped", Status.SKIPPED),
        ("error", Status.ERROR),
    ],
)
def test_status_can_be_created_from_value(raw_value, expected_value):
    assert Status(raw_value) is expected_value


def test_status_rejects_unknown_value():
    with pytest.raises(ValueError):
        Status("pased")

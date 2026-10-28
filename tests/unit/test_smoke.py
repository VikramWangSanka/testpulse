import testpulse
from testpulse.domain.models import Status


def test_package_has_version():
    assert testpulse.__version__ == "0.1.0"


def test_status_function():
    assert Status("failed") == Status.FAILED
    assert Status("passed") == Status.PASSED
    assert Status("skipped") == Status.SKIPPED
    assert Status("error") == Status.ERROR

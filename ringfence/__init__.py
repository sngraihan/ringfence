from .guard import (  # noqa: F401
    LockHeld,
    WorkLock,
    completion,
    detect_drift,
    is_worker_running,
    mark_done,
    mark_failed,
    should_stop,
)

__version__ = "0.1.0"

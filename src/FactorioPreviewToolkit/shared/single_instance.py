"""
Guards against a second toolkit instance running at the same time.

Both instances would use the same temp folder, so their Factorio subprocesses fight over
Factorio's write-data lock. The loser dies mid-run with "Couldn't create lock file ... 32.
Is another instance already running?", which is a confusing way to find out that you
double-clicked the executable twice.
"""

import os
from collections.abc import Iterator
from contextlib import contextmanager

import psutil

from src.FactorioPreviewToolkit.shared.shared_constants import constants
from src.FactorioPreviewToolkit.shared.structured_logger import log


class AlreadyRunningError(RuntimeError):
    """Raised when another instance of the toolkit is already running."""


def _is_live_toolkit_process(pid: int) -> bool:
    """
    Tells whether the pid belongs to another live instance of this toolkit, rather than to
    a stale entry from a crash or to an unrelated process that reused the pid.
    """
    try:
        other = psutil.Process(pid)
        return other.is_running() and other.name() == psutil.Process(os.getpid()).name()
    except (psutil.NoSuchProcess, psutil.AccessDenied, ValueError):
        return False


def _read_locked_pid() -> int | None:
    """
    Returns the pid recorded in the instance lock, or None if there is no usable lock.
    """
    try:
        return int(constants.TOOLKIT_INSTANCE_LOCK_FILEPATH.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return None


@contextmanager
def single_instance_guard() -> Iterator[None]:
    """
    Claims the instance lock for this process, or raises AlreadyRunningError.
    A lock left behind by a crashed or killed instance is taken over.
    """
    lock_path = constants.TOOLKIT_INSTANCE_LOCK_FILEPATH
    locked_pid = _read_locked_pid()

    if (
        locked_pid is not None
        and locked_pid != os.getpid()
        and _is_live_toolkit_process(locked_pid)
    ):
        raise AlreadyRunningError(
            f"The Factorio Preview Toolkit is already running (process {locked_pid}).\n"
            f"Close the other window before starting a new one - both would use the same "
            f"temp folder and their Factorio processes would fight over the same lock."
        )

    if locked_pid is not None:
        log.info(f"🧹 Taking over an instance lock left behind by process {locked_pid}.")

    try:
        lock_path.write_text(str(os.getpid()), encoding="utf-8")
    except OSError as e:
        # Not being able to write the lock is no reason to refuse to run.
        log.warning(f"⚠️ Could not write the instance lock '{lock_path}': {e}")

    try:
        yield
    finally:
        try:
            if _read_locked_pid() == os.getpid():
                lock_path.unlink()
        except OSError as e:
            log.warning(f"⚠️ Could not remove the instance lock '{lock_path}': {e}")

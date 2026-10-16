"""
Background task execution pool, concurrency management, and thread lifecycle.
"""

from __future__ import annotations

import concurrent.futures
from typing import Callable, Any, Optional

from logging_service.logger import get_logger

logger = get_logger("app.task_manager")


class TaskManager:
    """
    Manages non-blocking concurrent task execution outside the GUI thread.
    """

    def __init__(self, max_workers: int = 4) -> None:
        self.executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="OmniWorker",
        )
        self._is_shutdown = False

    def submit_task(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> concurrent.futures.Future:
        """Submits a callable to run in the background thread pool."""
        if self._is_shutdown:
            raise RuntimeError("TaskManager has already been shut down.")
        return self.executor.submit(fn, *args, **kwargs)

    def shutdown(self, wait: bool = True) -> None:
        """Gracefully halts worker threads."""
        logger.info("Shutting down TaskManager thread pool (wait=%s)...", wait)
        self._is_shutdown = True
        self.executor.shutdown(wait=wait, cancel_futures=True)

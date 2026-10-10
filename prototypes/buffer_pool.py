"""Reusable Screen Buffer Pool."""

class ScreenBufferPool:
    def __init__(self, capacity: int = 4):
        self._pool = []
        self._capacity = capacity

    def acquire(self, size: int) -> bytearray:
        if self._pool:
            return self._pool.pop()
        return bytearray(size)

    def release(self, buf: bytearray):
        if len(self._pool) < self._capacity:
            self._pool.append(buf)

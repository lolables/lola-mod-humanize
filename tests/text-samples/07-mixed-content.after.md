# Building a Connection Pool

A connection pool reuses database connections instead of opening a new one per query. This matters once you have concurrent requests, because connection setup is expensive and most databases cap the number of simultaneous connections.

## How it works

The pool keeps idle connections in a thread-safe queue. When your code needs a connection, it pulls one from the queue (or creates a new one if the pool isn't full). When it's done, it puts the connection back.

```python
import logging
import queue
import threading
from dataclasses import dataclass
from typing import Any


@dataclass
class PoolConfig:
    """Settings for the connection pool."""

    host: str
    port: int
    database: str
    user: str
    password: str
    max_size: int = 10
    min_size: int = 2
    acquire_timeout: float = 30.0
    idle_timeout: float = 300.0


class ConnectionPool:
    """Thread-safe pool of reusable database connections."""

    def __init__(self, config: PoolConfig) -> None:
        self._config = config
        self._pool: queue.Queue = queue.Queue(maxsize=config.max_size)
        self._lock = threading.Lock()
        self._created = 0
        self._log = logging.getLogger(__name__)
        self._log.info(f"Connection pool ready (max_size={config.max_size})")

    def acquire(self) -> Any:
        """Get a connection from the pool.

        Blocks up to `acquire_timeout` seconds if the pool is empty.
        Raises PoolTimeout if no connection becomes available.
        """
        try:
            conn = self._pool.get(timeout=self._config.acquire_timeout)
            if self._is_alive(conn):
                return conn
            self._log.warning("Stale connection, creating replacement")
            return self._connect()
        except queue.Empty:
            raise PoolTimeout(
                f"No connection available after {self._config.acquire_timeout}s "
                f"(pool max_size={self._config.max_size})"
            )

    def release(self, conn: Any) -> None:
        """Return a connection to the pool."""
        try:
            self._pool.put_nowait(conn)
        except queue.Full:
            self._log.warning("Pool full, closing excess connection")
            self._close(conn)

    def _is_alive(self, conn: Any) -> bool:
        try:
            conn.ping()
            return True
        except Exception:
            return False

    def _connect(self) -> Any:
        self._created += 1
        self._log.info(f"New connection (total_created={self._created})")
        # actual driver call goes here
        ...

    def _close(self, conn: Any) -> None:
        try:
            conn.close()
        except Exception as exc:
            self._log.error(f"Error closing connection: {exc}")


class PoolTimeout(Exception):
    """Raised when a connection can't be acquired within the timeout."""
    pass
```

## Notes

- The queue handles thread safety for the pool itself. The `_lock` is there for bookkeeping that touches `_created` from multiple threads.
- `_is_alive` does a ping check before handing out a connection. This catches connections that went stale while sitting in the pool (server timeout, network blip, etc.).
- In a real implementation, you'd want a background thread that enforces `idle_timeout` and maintains `min_size` warm connections.

"""Subprocess helpers for the TUI: line-buffered async streaming + interactive runs.

Why this module exists
----------------------
Historically, ``tui.app`` used ``subprocess.Popen(text=True, bufsize=1)``
and a thread. In CPython, ``bufsize=1`` with ``text=True`` only enables
line-buffering when stdout is a TTY; with ``stdout=PIPE`` it falls back
to **block-buffering** (4-8 KB). Odoo doesn't flush often, so reading
``for line in proc.stdout`` blocks → the TUI looks frozen during
``update`` on large module lists.

The fix is asyncio's ``create_subprocess_exec``: ``await stream.readline()``
yields one line at a time, with REAL line-buffering on the pipe. The
``stream_command`` coroutine below is the single source of truth for that
pattern.

Cancel semantics
----------------
``stream_command`` handles ``asyncio.CancelledError`` by:

  1. ``proc.terminate()`` (SIGTERM)
  2. ``await asyncio.wait_for(proc.wait(), timeout=5)`` — grace period
  3. If that times out, ``proc.kill()`` (SIGKILL) and a short wait

The caller (the worker task) re-raises ``CancelledError`` after cleanup.
"""

import asyncio
import sys
from typing import Awaitable, Callable, Optional, Tuple

# Time (seconds) we wait for a SIGTERM'd subprocess to exit before
# escalating to SIGKILL.
_TERMINATE_GRACE = 5.0
# Time (seconds) we wait for the post-kill wait.
_KILL_GRACE = 2.0
# Time (seconds) we wait for the subprocess to finish on its own; if it
# exceeds this, we SIGKILL. 5 minutes is well above the longest known
# Odoo update in this repo.
_PROC_WAIT_TIMEOUT = 300.0


# Callback signatures (kept simple on purpose: the runner does the
# parsing, callers don't have to).
OnLine = Callable[[str], None]
OnProgress = Callable[[int, int], None]


async def stream_command(
    argv: list,
    cwd: str,
    *,
    on_line: Optional[OnLine] = None,
    on_progress: Optional[OnProgress] = None,
    terminate_grace: float = _TERMINATE_GRACE,
    kill_grace: float = _KILL_GRACE,
    proc_wait_timeout: float = _PROC_WAIT_TIMEOUT,
) -> int:
    """Run ``argv`` in ``cwd`` and stream stdout line by line.

    stderr is merged into stdout so callers see a single ordered log.

    Args:
        argv: Command and args (each element passed as a separate argv).
        cwd: Working directory.
        on_line: Sync callback called for every line (after ``rstrip``).
        on_progress: Sync callback called for every line that contains a
            ``(N/M)`` progress marker. Skipped silently if ``on_line``
            already saw the line (the runner only parses once per line).
        terminate_grace: Seconds to wait for a SIGTERM'd process to exit
            before escalating to SIGKILL.
        kill_grace: Seconds to wait for a SIGKILL'd process to exit.
        proc_wait_timeout: Seconds to wait for the subprocess to finish
            on its own; if it exceeds this, we SIGKILL.

    Returns:
        Process return code.

    Raises:
        FileNotFoundError: If the executable doesn't exist.
        asyncio.CancelledError: If the awaiting task is cancelled. The
            subprocess is terminated (and killed if needed) before
            re-raising.
    """
    # Local import keeps tui.parser optional for unit tests that don't
    # touch the streaming path.
    from tui.parser import parse_progress

    try:
        proc = await asyncio.create_subprocess_exec(
            *argv,
            cwd=cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
    except FileNotFoundError:
        # Surface the error to the caller; they usually want to log it
        # to the RichLog.
        raise

    if proc.stdout is None:
        # Should not happen with PIPE, but be defensive.
        return await _wait_with_timeout(proc, proc_wait_timeout, kill_grace)

    try:
        # Per-line loop. ``readline()`` returns ``b""`` at EOF, which is
        # falsy and breaks the loop. The asyncio stream is line-buffered
        # for pipes, so we don't see the 4-8 KB block-buffering issue
        # that the old ``subprocess.Popen(text=True, bufsize=1)`` had.
        while True:
            raw = await proc.stdout.readline()
            if not raw:
                break
            try:
                line = raw.decode("utf-8", errors="replace").rstrip("\n")
            except Exception:
                # Last-ditch: never crash the runner on a decode glitch.
                line = raw.decode("latin-1", errors="replace").rstrip("\n")
            if on_line is not None:
                try:
                    on_line(line)
                except Exception as exc:
                    # A buggy callback must not kill the runner.
                    print(
                        f"[tui.runner] on_line callback raised: {exc}",
                        file=sys.stderr,
                    )
            if on_progress is not None:
                parsed = parse_progress(line)
                if parsed is not None:
                    try:
                        on_progress(parsed[0], parsed[1])
                    except Exception as exc:
                        print(
                            f"[tui.runner] on_progress callback raised: {exc}",
                            file=sys.stderr,
                        )
    except asyncio.CancelledError:
        await _terminate_and_reap(proc, terminate_grace, kill_grace)
        raise

    # Drain a final wait under a timeout in case the process hangs after
    # closing its stdout. If it really hangs, SIGKILL.
    try:
        return await _wait_with_timeout(proc, proc_wait_timeout, kill_grace)
    except asyncio.CancelledError:
        await _terminate_and_reap(proc, terminate_grace, kill_grace)
        raise


async def _wait_with_timeout(
    proc: "asyncio.subprocess.Process",
    proc_wait_timeout: float = _PROC_WAIT_TIMEOUT,
    kill_grace: float = _KILL_GRACE,
) -> int:
    """``await proc.wait()`` bounded by ``proc_wait_timeout``."""
    try:
        return await asyncio.wait_for(proc.wait(), timeout=proc_wait_timeout)
    except asyncio.TimeoutError:
        # Process is wedged. SIGKILL and wait briefly.
        try:
            proc.kill()
        except ProcessLookupError:
            pass
        try:
            return await asyncio.wait_for(proc.wait(), timeout=kill_grace)
        except asyncio.TimeoutError:
            # If it still won't die, return a sentinel that signals
            # "killed by us" so the caller can log it.
            return -9


async def _terminate_and_reap(
    proc: "asyncio.subprocess.Process",
    terminate_grace: float = _TERMINATE_GRACE,
    kill_grace: float = _KILL_GRACE,
) -> None:
    """SIGTERM the proc, wait grace period, escalate to SIGKILL on timeout."""
    if proc.returncode is not None:
        return  # already done
    try:
        proc.terminate()
    except ProcessLookupError:
        return
    try:
        await asyncio.wait_for(proc.wait(), timeout=terminate_grace)
        return
    except asyncio.TimeoutError:
        pass
    try:
        proc.kill()
    except ProcessLookupError:
        return
    try:
        await asyncio.wait_for(proc.wait(), timeout=kill_grace)
    except asyncio.TimeoutError:
        # Give up; the process is a zombie at this point. Don't block
        # the cancel propagation forever.
        pass


async def run_interactive(
    argv: list,
    cwd: str,
    *,
    proc_wait_timeout: float = _PROC_WAIT_TIMEOUT,
    kill_grace: float = _KILL_GRACE,
) -> int:
    """Run ``argv`` in ``cwd`` and return its exit code (no streaming).

    Used by the TUI's "interactive" actions (bash, logs, psql) that
    suspend the Textual app via ``self.suspend()`` to give the user a
    real terminal. This is just a thin async wrapper around
    ``create_subprocess_exec`` + ``wait`` so the caller can ``await`` it
    from the worker pool.
    """
    proc = await asyncio.create_subprocess_exec(*argv, cwd=cwd)
    return await _wait_with_timeout(proc, proc_wait_timeout, kill_grace)

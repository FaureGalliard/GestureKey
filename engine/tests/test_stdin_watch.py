"""
Regression: the stdin shutdown watch must not block other threads' use of the
std handles. A pending synchronous read on a Windows pipe makes
GetFileInformationByHandle on it hang — and so does loading a new DLL, which
is what happens when MSMF opens the camera — so the camera never opened
while the engine was launched by the app.
"""
from __future__ import annotations
import subprocess
import sys
import textwrap

import pytest

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="Windows pipe semantics")

CHILD = textwrap.dedent("""
    import ctypes, msvcrt, sys, threading, time
    from gesturekey.runtime.server import _wait_for_stdin_eof
    threading.Thread(target=_wait_for_stdin_eof, args=(lambda: None,), daemon=True).start()
    time.sleep(0.5)                               # the watcher is now running
    done = threading.Event()
    def probe():
        info = ctypes.create_string_buffer(64)   # BY_HANDLE_FILE_INFORMATION
        ctypes.windll.kernel32.GetFileInformationByHandle(msvcrt.get_osfhandle(sys.stdin.fileno()), info)
        done.set()
    threading.Thread(target=probe, daemon=True).start()
    print("ok" if done.wait(2.0) else "blocked", flush=True)
""")


def test_stdin_watch_does_not_block_std_handles():
    # stdin stays open (like the app keeps it) while the child probes it
    child = subprocess.Popen([sys.executable, "-c", CHILD], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    try:
        out = child.stdout.readline()
    finally:
        child.stdin.close()
        child.wait(timeout=10)
    assert out.strip() == b"ok"

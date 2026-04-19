#!/usr/bin/env python3
"""One-command dev runner for Helix.

Starts four processes:
- Recourse backend     (uvicorn on :8000)
- LenderCo backend     (uvicorn on :8001)
- Recourse frontend    (vite on :5173)
- LenderCo frontend    (vite on :5174)

Each log line is prefixed with a color-coded service tag. Health is polled until
all services respond, then a banner with clickable URLs is printed. Ctrl-C
sends SIGTERM to every child and waits for them to exit cleanly.
"""
from __future__ import annotations

import os
import signal
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
BLUE = "\033[34m"
MAGENTA = "\033[35m"
CYAN = "\033[36m"
ORANGE = "\033[38;5;208m"


@dataclass
class Service:
    tag: str
    color: str
    cmd: list[str]
    cwd: Path
    env_extra: dict[str, str]
    health_url: str | None
    public_url: str


if sys.platform == "win32":
    VENV_PY = REPO / "backend" / ".venv" / "Scripts" / "python.exe"
else:
    VENV_PY = REPO / "backend" / ".venv" / "bin" / "python"

IS_WINDOWS = sys.platform == "win32"

SERVICES: list[Service] = [
    Service(
        tag="recourse-api",
        color=ORANGE,
        cmd=[str(VENV_PY), "-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", "8000", "--reload"],
        cwd=REPO,
        env_extra={},
        health_url="http://127.0.0.1:8000/health",
        public_url="http://localhost:8000/docs",
    ),
    Service(
        tag="lender-api",
        color=CYAN,
        cmd=[str(VENV_PY), "-m", "uvicorn", "customer_portal.backend.main:app", "--host", "127.0.0.1", "--port", "8001", "--reload"],
        cwd=REPO,
        env_extra={},
        health_url="http://127.0.0.1:8001/health",
        public_url="http://localhost:8001/docs",
    ),
    Service(
        tag="recourse-web",
        color=MAGENTA,
        cmd=(["npm.cmd"] if IS_WINDOWS else ["npm"]) + ["run", "dev", "--silent"],
        cwd=REPO / "frontend",
        env_extra={},
        health_url=None,
        public_url="http://localhost:5173",
    ),
    Service(
        tag="lender-web",
        color=BLUE,
        cmd=(["npm.cmd"] if IS_WINDOWS else ["npm"]) + ["run", "dev", "--silent"],
        cwd=REPO / "customer_portal" / "frontend",
        env_extra={},
        health_url=None,
        public_url="http://localhost:5174",
    ),
]


def c(color: str, s: str) -> str:
    return f"{color}{s}{RESET}"


def warn(msg: str) -> None:
    print(c(YELLOW, "⚠ ") + msg, file=sys.stderr)


def fail(msg: str) -> None:
    print(c(RED, "✗ ") + msg, file=sys.stderr)
    sys.exit(1)


def ok(msg: str) -> None:
    print(c(GREEN, "✓ ") + msg)


def info(msg: str) -> None:
    print(c(DIM, "· ") + msg)


# ---------- preflight ----------

def preflight() -> None:
    print(c(BOLD, "\n▸ Preflight checks\n"))

    # 1. Ollama daemon + model
    try:
        subprocess.run(["ollama", "--version"], check=True, capture_output=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        fail("ollama not installed. See https://ollama.com/download")
    try:
        req = urllib.request.Request("http://127.0.0.1:11434/api/tags")
        with urllib.request.urlopen(req, timeout=2) as r:
            body = r.read().decode()
        if "glm-ocr:bf16" in body or "glm-ocr" in body:
            ok("ollama running · glm-ocr model present")
        else:
            warn("ollama running but glm-ocr model not pulled. Run: ollama pull glm-ocr:bf16")
    except Exception:
        warn("ollama daemon not responding on :11434 — starting it for you …")
        subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(2)
        ok("ollama daemon started in background")

    # 2. Python venv
    if not VENV_PY.exists():
        fail(f"Backend venv missing at {VENV_PY}. See README for setup.")
    ok(f"python venv · {VENV_PY}")

    # 3. Frontend node_modules
    for fe in (REPO / "frontend", REPO / "customer_portal" / "frontend"):
        if not (fe / "node_modules").exists():
            warn(f"{fe} has no node_modules. Running npm install now …")
            subprocess.run(["npm", "install"], cwd=fe, check=True)
    ok("frontend deps present")

    print()


# ---------- process mgmt ----------

class Runner:
    def __init__(self, services: list[Service]) -> None:
        self.services = services
        self.procs: list[subprocess.Popen] = []
        self.stop_event = threading.Event()

    def start_all(self) -> None:
        env_base = os.environ.copy()
        for svc in self.services:
            env = {**env_base, **svc.env_extra}
            popen_kwargs = dict(
                cwd=str(svc.cwd),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                bufsize=1,
                text=True,
            )
            if IS_WINDOWS:
                popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
            else:
                popen_kwargs["preexec_fn"] = os.setsid
            p = subprocess.Popen(svc.cmd, **popen_kwargs)
            self.procs.append(p)
            threading.Thread(target=self._tail, args=(svc, p), daemon=True).start()

    def _tail(self, svc: Service, p: subprocess.Popen) -> None:
        prefix = c(svc.color, f"[{svc.tag:<12}]")
        assert p.stdout is not None
        for line in p.stdout:
            sys.stdout.write(f"{prefix} {line.rstrip()}\n")
            sys.stdout.flush()

    def wait_for_health(self, timeout_s: float = 45.0) -> None:
        deadline = time.time() + timeout_s
        pending = [s for s in self.services if s.health_url]
        while time.time() < deadline and pending:
            ready: list[Service] = []
            for s in pending:
                try:
                    with urllib.request.urlopen(s.health_url, timeout=1) as r:
                        if r.status == 200:
                            ready.append(s)
                            ok(f"{s.tag} · healthy")
                except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError):
                    continue
                except Exception:
                    continue
            pending = [s for s in pending if s not in ready]
            if pending:
                time.sleep(0.6)
        if pending:
            warn("some services never became healthy: " + ", ".join(s.tag for s in pending))

    def banner(self) -> None:
        line = "━" * 64
        print()
        print(c(BOLD, line))
        print(c(BOLD, "  HELIX / RECOURSE · All services online"))
        print(c(BOLD, line))
        for s in self.services:
            print(f"  {c(s.color, s.tag.ljust(14))}  {s.public_url}")
        print(f"  {c(DIM, 'ollama        ')}  http://localhost:11434")
        print(c(BOLD, line))
        print(c(DIM, "  Ctrl-C stops everything."))
        print(c(BOLD, line))
        print()

    def wait_and_cleanup(self) -> int:
        def handler(_signum, _frame):  # noqa: ARG001
            self.stop_event.set()
        signal.signal(signal.SIGINT, handler)
        signal.signal(signal.SIGTERM, handler)
        while not self.stop_event.is_set():
            # if any child died unexpectedly, stop everything
            dead = [(s, p) for s, p in zip(self.services, self.procs) if p.poll() is not None]
            if dead:
                for s, p in dead:
                    warn(f"{s.tag} exited with code {p.returncode}")
                break
            time.sleep(0.4)
        return self.shutdown()

    def shutdown(self) -> int:
        print()
        warn("Stopping all services…")
        for p in self.procs:
            if p.poll() is None:
                try:
                    if IS_WINDOWS:
                        p.send_signal(signal.CTRL_BREAK_EVENT)
                    else:
                        os.killpg(os.getpgid(p.pid), signal.SIGTERM)
                except (ProcessLookupError, OSError):
                    pass
        deadline = time.time() + 6
        for p in self.procs:
            while p.poll() is None and time.time() < deadline:
                time.sleep(0.1)
        for p in self.procs:
            if p.poll() is None:
                try:
                    if IS_WINDOWS:
                        p.kill()
                    else:
                        os.killpg(os.getpgid(p.pid), signal.SIGKILL)
                except (ProcessLookupError, OSError):
                    pass
        ok("All services stopped.")
        return 0


def main() -> int:
    preflight()
    runner = Runner(SERVICES)
    runner.start_all()
    runner.wait_for_health()
    runner.banner()
    return runner.wait_and_cleanup()


if __name__ == "__main__":
    sys.exit(main())

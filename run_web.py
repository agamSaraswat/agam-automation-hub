#!/usr/bin/env python3
"""Local dev runner for the FastAPI + React skeleton."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
FRONTEND_DIR = REPO_ROOT / "frontend"


def _spawn(cmd: list[str], cwd: Path | None = None) -> subprocess.Popen:
    return subprocess.Popen(cmd, cwd=str(cwd) if cwd else None)


def _npm_command() -> str:
    return "npm.cmd" if sys.platform.startswith("win") else "npm"


def _run_backend() -> int:
    return subprocess.call(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "src.web.main:app",
            "--host",
            "0.0.0.0",
            "--port",
            "8000",
            "--reload",
        ],
        cwd=REPO_ROOT,
    )


def _run_frontend() -> int:
    return subprocess.call([_npm_command(), "run", "dev"], cwd=FRONTEND_DIR)


def _run_both() -> int:
    backend = _spawn(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "src.web.main:app",
            "--host",
            "0.0.0.0",
            "--port",
            "8000",
            "--reload",
        ],
        cwd=REPO_ROOT,
    )
    frontend = _spawn([_npm_command(), "run", "dev"], cwd=FRONTEND_DIR)

    print("🚀 Backend:  http://localhost:8000")
    print("🚀 Frontend: http://localhost:5173")
    print("Press Ctrl+C to stop both processes.")

    try:
        backend.wait()
        frontend.wait()
    except KeyboardInterrupt:
        pass
    finally:
        for proc in (backend, frontend):
            if proc.poll() is None:
                proc.terminate()
        for proc in (backend, frontend):
            if proc.poll() is None:
                proc.wait(timeout=5)

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Run web dev services")
    parser.add_argument(
        "--mode",
        choices=("backend", "frontend", "both"),
        default="both",
        help="Which web service(s) to run",
    )
    args = parser.parse_args()

    if args.mode == "backend":
        return _run_backend()
    if args.mode == "frontend":
        return _run_frontend()
    return _run_both()


if __name__ == "__main__":
    raise SystemExit(main())

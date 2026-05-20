import argparse
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path


def _resolve_backend_python(project_root: Path) -> str:
    venv_python = project_root / ".venv" / "Scripts" / "python.exe"
    if venv_python.exists():
        return str(venv_python)
    return sys.executable


def _resolve_npm() -> str:
    npm_cmd = shutil.which("npm")
    if npm_cmd:
        return npm_cmd
    raise FileNotFoundError(
        "npm was not found in PATH. Install Node.js or add npm to PATH."
    )


def _start_process(name: str, cmd: list[str], cwd: Path) -> subprocess.Popen:
    print(f"[start] {name}: {' '.join(cmd)} (cwd={cwd})")
    return subprocess.Popen(
        cmd,
        cwd=str(cwd),
        stdout=None,
        stderr=None,
        creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
    )


def _stop_process(name: str, proc: subprocess.Popen, timeout: float = 5.0) -> None:
    if proc.poll() is not None:
        return

    print(f"[stop] {name}")
    try:
        proc.terminate()
        proc.wait(timeout=timeout)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Launch backend (FastAPI) and frontend (Vite) together."
    )
    parser.add_argument("--backend-port", type=int, default=8000)
    parser.add_argument("--frontend-port", type=int, default=5173)
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent
    frontend_dir = project_root / "frontend"

    if not frontend_dir.exists():
        print(f"[error] frontend directory not found: {frontend_dir}")
        return 1

    backend_python = _resolve_backend_python(project_root)
    npm_cmd = _resolve_npm()

    backend_cmd = [backend_python, "app.py"]
    frontend_cmd = [
        npm_cmd,
        "run",
        "dev",
        "--",
        "--host",
        "0.0.0.0",
        "--port",
        str(args.frontend_port),
    ]

    backend_proc = None
    frontend_proc = None

    try:
        backend_proc = _start_process("backend", backend_cmd, project_root)
        time.sleep(1)
        frontend_proc = _start_process("frontend", frontend_cmd, frontend_dir)

        print("\n[ready] Services started")
        print(f"  Backend:  http://localhost:{args.backend_port}")
        print(f"  Frontend: http://localhost:{args.frontend_port}")
        print("  Press Ctrl+C to stop both.\n")

        while True:
            time.sleep(1)

            if backend_proc.poll() is not None:
                print("[error] backend exited unexpectedly")
                return backend_proc.returncode or 1

            if frontend_proc.poll() is not None:
                print("[error] frontend exited unexpectedly")
                return frontend_proc.returncode or 1

    except KeyboardInterrupt:
        print("\n[signal] Ctrl+C received")
        return 0
    finally:
        if frontend_proc:
            _stop_process("frontend", frontend_proc)
        if backend_proc:
            _stop_process("backend", backend_proc)


if __name__ == "__main__":
    sys.exit(main())

import os
import sys
import threading
import subprocess
import platform


RESET = "\x1b[0m"
CYAN = "\x1b[36m"
YELLOW = "\x1b[33m"


def stream_output(pipe, prefix):
    try:
        for line in iter(pipe.readline, ""):
            if not line:
                break
            print(f"{prefix}{line.rstrip()}{RESET}")
    finally:
        pipe.close()


def ensure_required_paths():
    backend_main = os.path.join("backend", "main.py")
    backend_db = os.path.join("backend", "cards.db")
    frontend_dir = "frontend"

    missing = []
    if not os.path.isfile(backend_main):
        missing.append(backend_main)
    if not os.path.isfile(backend_db):
        missing.append(backend_db)
    if not os.path.isdir(frontend_dir):
        missing.append(frontend_dir)

    if missing:
        print("Missing required paths:")
        for path in missing:
            print(f"- {path}")
        sys.exit(1)


def start_process(cmd, cwd, shell=False):
    return subprocess.Popen(
        cmd,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        shell=shell,
    )


def main():
    ensure_required_paths()

    is_windows = platform.system() == "Windows"
    backend_cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "main:app",
        "--host",
        "127.0.0.1",
        "--port",
        "8000",
        "--reload",
    ]
    if is_windows:
        frontend_cmd = ["npm.cmd", "start"]
        frontend_shell = False
    else:
        frontend_cmd = ["npm", "start"]
        frontend_shell = False

    backend_proc = start_process(backend_cmd, cwd="backend")
    frontend_proc = start_process(frontend_cmd, cwd="frontend", shell=frontend_shell)

    threads = [
        threading.Thread(
            target=stream_output,
            args=(backend_proc.stdout, f"{CYAN}[BACKEND]{RESET} "),
            daemon=True,
        ),
        threading.Thread(
            target=stream_output,
            args=(backend_proc.stderr, f"{CYAN}[BACKEND]{RESET} "),
            daemon=True,
        ),
        threading.Thread(
            target=stream_output,
            args=(frontend_proc.stdout, f"{YELLOW}[FRONTEND]{RESET} "),
            daemon=True,
        ),
        threading.Thread(
            target=stream_output,
            args=(frontend_proc.stderr, f"{YELLOW}[FRONTEND]{RESET} "),
            daemon=True,
        ),
    ]
    for t in threads:
        t.start()

    try:
        while True:
            if backend_proc.poll() is not None or frontend_proc.poll() is not None:
                break
            threading.Event().wait(0.2)
    except KeyboardInterrupt:
        print("\nStopping processes...")
    finally:
        for proc in (backend_proc, frontend_proc):
            if proc.poll() is None:
                proc.terminate()


if __name__ == "__main__":
    main()

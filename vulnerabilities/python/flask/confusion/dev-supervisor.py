#!/usr/bin/env python3
import argparse
import signal
import subprocess
import sys
import threading

from watchfiles import watch


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Dev supervisor:\n"
            " - runs a command\n"
            " - lets the command's own reloader handle changes while it's alive\n"
            " - if the command exits/crashes, only restarts it after the NEXT file change"
        ),
        # This allows the help message to show newlines
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "-w",
        "--watch",
        action="append",
        # This prevents `argparse` from *adding* '/app' if other -w flags are used.
        default=None,
        help="Directory to watch (can be given multiple times). Defaults to /app.",
    )
    parser.add_argument(
        "cmd",
        nargs=argparse.REMAINDER,
        help="Command to run, e.g. -- flask run --debug --host=0.0.0.0 --port=8000",
    )

    args = parser.parse_args()

    # Manually set default watch_paths if none were provided
    watch_paths = args.watch if args.watch is not None else ["/app"]
    cmd = args.cmd

    # The 'cmd' list will contain ['--', 'flask', 'run', ...].
    # We must strip the '--' separator.
    if cmd and cmd[0] == "--":
        cmd = cmd[1:]

    if not cmd:
        print("[dev-supervisor] No command specified", file=sys.stderr)
        return 1

    print(f"[dev-supervisor] watching: {', '.join(watch_paths)}", flush=True)
    print(f"[dev-supervisor] command : {' '.join(cmd)}", flush=True)

    proc = subprocess.Popen(cmd)
    stop_event = threading.Event()

    def handle_signal(sig, frame):
        if stop_event.is_set():  # Avoid duplicate signals
            return
        print(f"[dev-supervisor] received signal {sig}, shutting down...", flush=True)
        stop_event.set()
        if proc.poll() is None:
            print("[dev-supervisor] terminating child process...", flush=True)
            proc.terminate()

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    # Main loop: only restart on file change IF the child is *not* running.
    try:
        for _changes in watch(*watch_paths, stop_event=stop_event):
            if stop_event.is_set():
                break

            # Child still running → let Flask / Node dev server handle reload itself.
            if proc.poll() is None:
                continue

            # Child has crashed or exited; only now do we restart on a change.
            print(
                "[dev-supervisor] detected file changes and child is not running; restarting...",
                flush=True,
            )
            proc = subprocess.Popen(cmd)

    except RuntimeError as e:
        # Catch RuntimeError if stop_event is set after watcher is stopped
        if not stop_event.is_set() and "Stop event" not in str(e):
            raise e

    print("[dev-supervisor] waiting for child process to exit...", flush=True)
    if proc.poll() is None:
        proc.wait()

    print("[dev-supervisor] exiting", flush=True)
    return proc.returncode if proc.returncode is not None else 0


if __name__ == "__main__":
    raise SystemExit(main())

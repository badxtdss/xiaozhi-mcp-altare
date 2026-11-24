#!/usr/bin/env python3
"""
小智 MCP 服务集合 - Altare 部署入口
同时运行:
  1. bridge/    - 魔搭 MCP 代理（必应搜索、A股、记忆、高德）
  2. reminder/  - 闹钟 + 待办提醒（V2 主动通知版）

两个服务共享同一个 MCP_ENDPOINT（小智接入点 WebSocket），
各自注册不同的工具。进程崩溃自动重启。
"""
import subprocess
import signal
import sys
import os
import time
import threading

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

services = {
    "bridge": {
        "cmd": [sys.executable, "mcp_pipe.py"],
        "cwd": os.path.join(BASE_DIR, "bridge"),
        "desc": "魔搭MCP代理(搜索/股票/记忆/地图)",
    },
    "reminder": {
        "cmd": [sys.executable, "mcp_pipe.py", "run_server_v2.py"],
        "cwd": os.path.join(BASE_DIR, "reminder"),
        "desc": "闹钟+待办提醒(V2主动通知)",
    },
}

running = {}
shutdown_event = threading.Event()


def launch(name, cfg):
    """启动一个服务子进程"""
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    proc = subprocess.Popen(
        cfg["cmd"],
        cwd=cfg["cwd"],
        env=env,
        stdout=sys.stdout,
        stderr=sys.stderr,
    )
    running[name] = proc
    print(f"[supervisor] {name} ({cfg['desc']}) started, pid={proc.pid}", flush=True)
    return proc


def monitor(name, cfg):
    """监控循环：进程退出后自动重启（指数退避）"""
    backoff = 1
    while not shutdown_event.is_set():
        proc = launch(name, cfg)
        try:
            proc.wait()
        except Exception:
            pass
        if shutdown_event.is_set():
            break
        code = proc.returncode
        print(f"[supervisor] {name} exited (code={code}), restarting in {backoff}s...", flush=True)
        time.sleep(backoff)
        backoff = min(backoff * 2, 60)


def signal_handler(sig, frame):
    print(f"\n[supervisor] Signal {sig}, shutting down...", flush=True)
    shutdown_event.set()
    for name, proc in running.items():
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except Exception:
            proc.kill()
    sys.exit(0)


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    print("[supervisor] 小智 MCP 服务集合启动", flush=True)
    print(f"[supervisor] MCP_ENDPOINT={'已设置' if os.environ.get('MCP_ENDPOINT') else '未设置!'}", flush=True)

    if not os.environ.get("MCP_ENDPOINT"):
        print("[supervisor] FATAL: MCP_ENDPOINT 环境变量未设置", flush=True)
        sys.exit(1)

    threads = []
    for name, cfg in services.items():
        t = threading.Thread(target=monitor, args=(name, cfg), daemon=True)
        t.start()
        threads.append(t)
        time.sleep(2)  # 错开启动，避免同时连 WebSocket

    # 主线程等待退出信号
    try:
        while not shutdown_event.is_set():
            shutdown_event.wait(timeout=10)
    except KeyboardInterrupt:
        signal_handler(signal.SIGINT, None)

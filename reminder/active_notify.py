"""主动通知定时器

后台线程每 N 秒检查到期提醒，发现新的到期项时向 stdout 写入一条
MCP 通知消息（notifications/resources/updated）。mcp_pipe 会把 stdout
的每一行转发给小智云端，从而触发设备播报。

采用"到期只提醒一次"策略：每个提醒ID首次到期时通知一次，之后不再
重复通知。避免旧数据导致频繁轰炸。如果需要重新听到某个提醒，可以
口头询问小智"有提醒吗"。

注意：用线程锁保护 stdout 写入，避免与 MCP stdio 传输的响应交错。
"""
import sys
import os
import json
import time
import threading

# 确保能 import mcp_reminder
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from mcp_reminder.storage import JSONStorage

_stdout_lock = threading.Lock()


def _send_notification(uri="reminder://pending"):
    """向 stdout 写入一条 MCP 通知（line-delimited JSON-RPC）"""
    msg = {
        "jsonrpc": "2.0",
        "method": "notifications/resources/updated",
        "params": {"uri": uri},
    }
    line = json.dumps(msg, ensure_ascii=False) + "\n"
    with _stdout_lock:
        sys.stdout.write(line)
        sys.stdout.flush()


def _check_loop(storage, interval=30):
    """后台循环：检查到期提醒，新的到期项通知一次"""
    notified = set()  # 已通知过的提醒ID

    while True:
        try:
            pending_alarms = storage.get_pending_alarms()
            pending_todos = storage.get_pending_todos()

            current_ids = set()
            for a in pending_alarms:
                current_ids.add(f"alarm:{a.id}")
            for t in pending_todos:
                current_ids.add(f"todo:{t.id}")

            # 只通知新出现的到期提醒
            new_ids = current_ids - notified
            if new_ids:
                _send_notification()
                notified.update(new_ids)
                # 日志写到 stderr，不影响 MCP 的 stdout 流
                print(f"[notify] {len(new_ids)} 个新到期提醒已通知（共{len(current_ids)}个到期）",
                      file=sys.stderr, flush=True)
        except Exception as e:
            print(f"[notify] 检查出错: {e}", file=sys.stderr, flush=True)

        time.sleep(interval)


def start_notify_timer(interval=30):
    """启动后台通知定时器"""
    storage = JSONStorage("data")
    t = threading.Thread(target=_check_loop, args=(storage, interval), daemon=True)
    t.start()
    print(f"[notify] 主动通知定时器已启动，每 {interval}s 检查，到期只提醒一次",
          file=sys.stderr, flush=True)
    return t

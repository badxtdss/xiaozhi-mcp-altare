"""MCP Reminder Service V2 Entry Point - With Active Notification Support"""
import sys
import os

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Import and run the V2 server with notification support
from mcp_reminder.server_v2 import mcp
from active_notify import start_notify_timer

if __name__ == "__main__":
    # 启动主动通知定时器（后台线程，每30秒检查到期提醒）
    start_notify_timer(interval=30)
    # 运行 MCP 服务器（stdio 传输）
    mcp.run(transport="stdio")

"""小智MCP闹钟和待办事项服务"""
from mcp.server.fastmcp import FastMCP
import logging
import sys
import os

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from mcp_reminder.models import Alarm, Todo, parse_time
from mcp_reminder.storage import JSONStorage

# 配置日志
logger = logging.getLogger('mcp_reminder')

# Fix UTF-8 encoding for Windows console
if sys.platform == 'win32':
    try:
        sys.stderr.reconfigure(encoding='utf-8')
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        # Python < 3.7 fallback
        import codecs
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

# 创建MCP服务
mcp = FastMCP("reminder")

# 初始化存储
storage = JSONStorage()


@mcp.tool()
def add_alarm(time: str, description: str = "") -> dict:
    """
    添加闹钟

    Args:
        time: 闹钟时间，支持自然语言如"下午2点30分"、"明天上午10点"或精确时间"2025-09-02 14:30"
        description: 闹钟描述（可选）

    Returns:
        包含闹钟ID和确认信息的字典
    """
    # 解析时间
    parsed_time = parse_time(time)
    if not parsed_time:
        return {
            "success": False,
            "error": f"无法解析时间: {time}，请使用如'下午2点30分'或'2025-09-02 14:30'格式"
        }

    # 创建闹钟
    alarm = Alarm(
        time=parsed_time,
        description=description
    )

    # 保存闹钟
    storage.add_alarm(alarm)

    logger.info(f"添加闹钟: {alarm.time}, 描述: {alarm.description}")

    return {
        "success": True,
        "alarm_id": alarm.id,
        "time": alarm.time,
        "description": alarm.description,
        "message": f"闹钟已设置在 {alarm.time}" + (f": {description}" if description else "")
    }


@mcp.tool()
def get_pending_alarms() -> dict:
    """
    获取所有到期的闹钟

    小智会定期调用此接口检查是否有需要提醒的闹钟

    Returns:
        包含到期闹钟列表的字典
    """
    pending_alarms = storage.get_pending_alarms()

    logger.info(f"查询到期闹钟，找到 {len(pending_alarms)} 个")

    if not pending_alarms:
        return {
            "success": True,
            "count": 0,
            "alarms": [],
            "message": "当前没有到期的闹钟"
        }

    alarms_data = [
        {
            "id": alarm.id,
            "time": alarm.time,
            "description": alarm.description
        }
        for alarm in pending_alarms
    ]

    return {
        "success": True,
        "count": len(pending_alarms),
        "alarms": alarms_data,
        "message": f"有 {len(pending_alarms)} 个闹钟到期"
    }


@mcp.tool()
def dismiss_alarm(alarm_id: str) -> dict:
    """
    关闭/删除闹钟

    Args:
        alarm_id: 闹钟ID

    Returns:
        操作结果
    """
    alarm = storage.get_alarm_by_id(alarm_id)
    if not alarm:
        return {
            "success": False,
            "error": f"未找到ID为 {alarm_id} 的闹钟"
        }

    alarm.status = "dismissed"
    storage.update_alarm(alarm)

    logger.info(f"关闭闹钟: {alarm_id}")

    return {
        "success": True,
        "message": "闹钟已关闭"
    }


@mcp.tool()
def add_todo(title: str, remind_time: str = "", description: str = "") -> dict:
    """
    添加待办事项

    Args:
        title: 待办事项标题
        remind_time: 提醒时间（可选），支持自然语言如"明天下午3点"
        description: 待办事项描述（可选）

    Returns:
        包含待办ID和确认信息的字典
    """
    if not title:
        return {
            "success": False,
            "error": "待办事项标题不能为空"
        }

    # 解析提醒时间
    parsed_remind_time = None
    if remind_time:
        parsed_remind_time = parse_time(remind_time)
        if not parsed_remind_time:
            return {
                "success": False,
                "error": f"无法解析提醒时间: {remind_time}"
            }

    # 创建待办事项
    todo = Todo(
        title=title,
        description=description,
        remind_time=parsed_remind_time
    )

    # 保存待办
    storage.add_todo(todo)

    logger.info(f"添加待办: {todo.title}, 提醒时间: {todo.remind_time}")

    message = f"已添加待办: {title}"
    if parsed_remind_time:
        message += f"，将在 {parsed_remind_time} 提醒"

    return {
        "success": True,
        "todo_id": todo.id,
        "title": todo.title,
        "remind_time": todo.remind_time,
        "message": message
    }


@mcp.tool()
def get_pending_todos() -> dict:
    """
    获取所有到期且未完成的待办事项

    小智会定期调用此接口检查是否有需要提醒的待办

    Returns:
        包含到期待办列表的字典
    """
    pending_todos = storage.get_pending_todos()

    logger.info(f"查询到期待办，找到 {len(pending_todos)} 个")

    if not pending_todos:
        return {
            "success": True,
            "count": 0,
            "todos": [],
            "message": "当前没有到期的待办事项"
        }

    todos_data = [
        {
            "id": todo.id,
            "title": todo.title,
            "description": todo.description,
            "remind_time": todo.remind_time
        }
        for todo in pending_todos
    ]

    return {
        "success": True,
        "count": len(pending_todos),
        "todos": todos_data,
        "message": f"有 {len(pending_todos)} 个待办事项到期"
    }


@mcp.tool()
def complete_todo(title: str) -> dict:
    """
    完成待办事项

    通过标题关键词匹配待办事项并标记为已完成

    Args:
        title: 待办事项标题或关键词

    Returns:
        操作结果
    """
    if not title:
        return {
            "success": False,
            "error": "请提供待办事项标题或关键词"
        }

    # 查找待办事项
    todo = storage.find_todo_by_title(title)
    if not todo:
        return {
            "success": False,
            "error": f"未找到标题包含 '{title}' 的待办事项"
        }

    # 标记为已完成
    todo.status = "completed"
    storage.update_todo(todo)

    logger.info(f"完成待办: {todo.title}")

    return {
        "success": True,
        "todo_id": todo.id,
        "title": todo.title,
        "message": f"已完成待办: {todo.title}"
    }


@mcp.tool()
def list_todos(status: str = "pending") -> dict:
    """
    列出待办事项

    Args:
        status: 筛选状态，可选值: "pending"(未完成)、"completed"(已完成)、"all"(全部)，默认"pending"

    Returns:
        待办事项列表
    """
    todos = storage.load_todos()

    # 筛选
    if status == "pending":
        todos = [t for t in todos if t.status == "pending"]
    elif status == "completed":
        todos = [t for t in todos if t.status == "completed"]
    # status == "all" 则不筛选

    logger.info(f"列出待办事项，状态: {status}, 数量: {len(todos)}")

    todos_data = [
        {
            "id": todo.id,
            "title": todo.title,
            "description": todo.description,
            "remind_time": todo.remind_time,
            "status": todo.status,
            "created_at": todo.created_at
        }
        for todo in todos
    ]

    return {
        "success": True,
        "count": len(todos),
        "todos": todos_data,
        "status_filter": status
    }


@mcp.tool()
def check_all_reminders() -> dict:
    """
    一次性检查所有到期的提醒（闹钟和待办事项）

    这是一个便捷工具，小智可以定期调用此接口来检查是否有需要提醒的内容

    Returns:
        包含所有到期闹钟和待办的汇总信息
    """
    # 获取到期闹钟
    pending_alarms = storage.get_pending_alarms()

    # 获取到期待办
    pending_todos = storage.get_pending_todos()

    total_count = len(pending_alarms) + len(pending_todos)

    logger.info(f"检查所有提醒，找到 {len(pending_alarms)} 个闹钟和 {len(pending_todos)} 个待办")

    if total_count == 0:
        return {
            "success": True,
            "has_reminders": False,
            "total_count": 0,
            "alarms": [],
            "todos": [],
            "message": "当前没有到期的提醒"
        }

    # 构建闹钟数据
    alarms_data = [
        {
            "id": alarm.id,
            "time": alarm.time,
            "description": alarm.description,
            "type": "alarm"
        }
        for alarm in pending_alarms
    ]

    # 构建待办数据
    todos_data = [
        {
            "id": todo.id,
            "title": todo.title,
            "description": todo.description,
            "remind_time": todo.remind_time,
            "type": "todo"
        }
        for todo in pending_todos
    ]

    # 生成提醒消息
    messages = []
    if pending_alarms:
        for alarm in pending_alarms:
            msg = f"闹钟提醒: {alarm.description if alarm.description else '时间到了'}"
            messages.append(msg)

    if pending_todos:
        for todo in pending_todos:
            msg = f"待办提醒: {todo.title}"
            messages.append(msg)

    return {
        "success": True,
        "has_reminders": True,
        "total_count": total_count,
        "alarm_count": len(pending_alarms),
        "todo_count": len(pending_todos),
        "alarms": alarms_data,
        "todos": todos_data,
        "messages": messages,
        "message": f"有 {total_count} 个提醒到期"
    }


# Start the server
if __name__ == "__main__":
    mcp.run(transport="stdio")

"""数据模型定义"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import uuid
import dateparser


@dataclass
class Alarm:
    """闹钟数据模型"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    time: str = ""  # ISO格式时间字符串
    description: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    status: str = "active"  # active/dismissed

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "time": self.time,
            "description": self.description,
            "created_at": self.created_at,
            "status": self.status
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Alarm":
        """从字典创建实例"""
        return cls(**data)

    def is_due(self) -> bool:
        """判断是否已到期"""
        if self.status != "active":
            return False
        try:
            alarm_time = datetime.fromisoformat(self.time)
            return datetime.now() >= alarm_time
        except (ValueError, TypeError):
            return False


@dataclass
class Todo:
    """待办事项数据模型"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    description: str = ""
    remind_time: Optional[str] = None  # 可选的提醒时间
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    status: str = "pending"  # pending/completed

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "remind_time": self.remind_time,
            "created_at": self.created_at,
            "status": self.status
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Todo":
        """从字典创建实例"""
        return cls(**data)

    def is_due(self) -> bool:
        """判断是否已到提醒时间"""
        if self.status != "pending" or not self.remind_time:
            return False
        try:
            remind_time = datetime.fromisoformat(self.remind_time)
            return datetime.now() >= remind_time
        except (ValueError, TypeError):
            return False


def parse_time(time_str: str) -> Optional[str]:
    """
    解析时间字符串，支持自然语言

    Args:
        time_str: 时间字符串，如"明天下午3点"、"30分钟后"、"2025-09-02 14:30"

    Returns:
        ISO格式的时间字符串，解析失败返回None
    """
    if not time_str:
        return None

    # 优先尝试ISO格式
    try:
        dt = datetime.fromisoformat(time_str)
        return dt.isoformat()
    except (ValueError, TypeError):
        pass

    # 使用dateparser解析自然语言
    try:
        dt = dateparser.parse(
            time_str,
            settings={
                'PREFER_DATES_FROM': 'future',
                'RETURN_AS_TIMEZONE_AWARE': False,
                'TIMEZONE': 'Asia/Shanghai'
            }
        )
        if dt:
            return dt.isoformat()
    except Exception:
        pass

    return None

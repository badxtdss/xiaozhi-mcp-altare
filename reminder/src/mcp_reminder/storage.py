"""JSON数据持久化"""
import json
import os
from pathlib import Path
from typing import List
from threading import Lock
from .models import Alarm, Todo


class JSONStorage:
    """JSON文件存储管理器"""

    def __init__(self, data_dir: str = "data"):
        """
        初始化存储管理器

        Args:
            data_dir: 数据存储目录路径
        """
        self.data_dir = Path(data_dir)
        self.alarms_file = self.data_dir / "alarms.json"
        self.todos_file = self.data_dir / "todos.json"
        self._lock = Lock()

        # 确保数据目录存在
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # 初始化数据文件
        self._init_file(self.alarms_file, [])
        self._init_file(self.todos_file, [])

    def _init_file(self, file_path: Path, default_data: list):
        """初始化数据文件"""
        if not file_path.exists():
            self._write_json(file_path, default_data)

    def _read_json(self, file_path: Path) -> list:
        """读取JSON文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return []

    def _write_json(self, file_path: Path, data: list):
        """写入JSON文件（原子写入）"""
        temp_file = file_path.with_suffix('.tmp')
        try:
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            # 原子替换
            temp_file.replace(file_path)
        except Exception as e:
            if temp_file.exists():
                temp_file.unlink()
            raise e

    def load_alarms(self) -> List[Alarm]:
        """加载所有闹钟"""
        with self._lock:
            data = self._read_json(self.alarms_file)
            return [Alarm.from_dict(item) for item in data]

    def save_alarms(self, alarms: List[Alarm]):
        """保存闹钟列表"""
        with self._lock:
            data = [alarm.to_dict() for alarm in alarms]
            self._write_json(self.alarms_file, data)

    def add_alarm(self, alarm: Alarm) -> Alarm:
        """添加闹钟"""
        alarms = self.load_alarms()
        alarms.append(alarm)
        self.save_alarms(alarms)
        return alarm

    def get_alarm_by_id(self, alarm_id: str) -> Alarm | None:
        """根据ID获取闹钟"""
        alarms = self.load_alarms()
        for alarm in alarms:
            if alarm.id == alarm_id:
                return alarm
        return None

    def update_alarm(self, alarm: Alarm):
        """更新闹钟"""
        alarms = self.load_alarms()
        for i, a in enumerate(alarms):
            if a.id == alarm.id:
                alarms[i] = alarm
                break
        self.save_alarms(alarms)

    def get_pending_alarms(self) -> List[Alarm]:
        """获取所有到期且未关闭的闹钟"""
        alarms = self.load_alarms()
        return [alarm for alarm in alarms if alarm.is_due()]

    def load_todos(self) -> List[Todo]:
        """加载所有待办事项"""
        with self._lock:
            data = self._read_json(self.todos_file)
            return [Todo.from_dict(item) for item in data]

    def save_todos(self, todos: List[Todo]):
        """保存待办事项列表"""
        with self._lock:
            data = [todo.to_dict() for todo in todos]
            self._write_json(self.todos_file, data)

    def add_todo(self, todo: Todo) -> Todo:
        """添加待办事项"""
        todos = self.load_todos()
        todos.append(todo)
        self.save_todos(todos)
        return todo

    def get_todo_by_id(self, todo_id: str) -> Todo | None:
        """根据ID获取待办事项"""
        todos = self.load_todos()
        for todo in todos:
            if todo.id == todo_id:
                return todo
        return None

    def update_todo(self, todo: Todo):
        """更新待办事项"""
        todos = self.load_todos()
        for i, t in enumerate(todos):
            if t.id == todo.id:
                todos[i] = todo
                break
        self.save_todos(todos)

    def get_pending_todos(self) -> List[Todo]:
        """获取所有到期且未完成的待办事项"""
        todos = self.load_todos()
        return [todo for todo in todos if todo.is_due()]

    def find_todo_by_title(self, title_keyword: str) -> Todo | None:
        """
        根据标题关键词查找待办事项（模糊匹配）

        匹配策略：
        1. 精确匹配优先
        2. 包含匹配（忽略大小写）
        3. 返回最近创建的未完成项

        Args:
            title_keyword: 标题关键词

        Returns:
            匹配到的待办事项，未匹配到返回None
        """
        from difflib import SequenceMatcher

        todos = self.load_todos()
        pending_todos = [t for t in todos if t.status == "pending"]

        if not pending_todos:
            return None

        # 精确匹配
        for todo in pending_todos:
            if todo.title.strip().lower() == title_keyword.strip().lower():
                return todo

        # 包含匹配
        candidates = []
        for todo in pending_todos:
            if title_keyword.lower() in todo.title.lower():
                candidates.append(todo)

        # 如果有包含匹配，返回最近创建的
        if candidates:
            candidates.sort(key=lambda t: t.created_at, reverse=True)
            return candidates[0]

        # 相似度匹配
        best_match = None
        best_ratio = 0.0
        for todo in pending_todos:
            ratio = SequenceMatcher(None, title_keyword.lower(), todo.title.lower()).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_match = todo

        # 只返回相似度大于0.5的匹配
        if best_ratio > 0.5:
            return best_match

        return None

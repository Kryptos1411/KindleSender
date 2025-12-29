"""Manages the queue of books to process."""
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import List, Optional, Callable
import threading
import uuid as uuid_module

from core.metadata import BookMetadata


class TaskStatus(Enum):
    QUEUED = "queued"
    CONVERTING = "converting"
    CONVERTED = "converted"
    TRANSFERRING = "transferring"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class BookTask:
    id: str
    metadata: BookMetadata
    output_format: str
    status: TaskStatus = TaskStatus.QUEUED
    progress: float = 0.0
    converted_path: Optional[Path] = None
    cover_path: Optional[Path] = None
    mobi_asin: Optional[str] = None  # The UUID calibre assigns for thumbnail matching
    error_message: str = ""
    send_to_kindle: bool = True
    save_to_folder: Optional[Path] = None

    @classmethod
    def create(cls, metadata: BookMetadata, output_format: str) -> "BookTask":
        return cls(
            id=str(uuid_module.uuid4())[:8],
            metadata=metadata,
            output_format=output_format
        )


class TaskManager:
    def __init__(self):
        self.tasks: List[BookTask] = []
        self._lock = threading.Lock()
        self._update_callbacks: List[Callable[[], None]] = []

    def add_update_callback(self, callback: Callable[[], None]):
        self._update_callbacks.append(callback)

    def _notify_update(self):
        for cb in self._update_callbacks:
            try:
                cb()
            except Exception as e:
                print(f"Update callback error: {e}")

    def add_task(self, task: BookTask):
        with self._lock:
            self.tasks.append(task)
        self._notify_update()

    def remove_task(self, task_id: str):
        with self._lock:
            self.tasks = [t for t in self.tasks if t.id != task_id]
        self._notify_update()

    def get_task(self, task_id: str) -> Optional[BookTask]:
        with self._lock:
            for task in self.tasks:
                if task.id == task_id:
                    return task
        return None

    def update_task(self, task_id: str, **kwargs):
        with self._lock:
            for task in self.tasks:
                if task.id == task_id:
                    for key, value in kwargs.items():
                        setattr(task, key, value)
                    break
        self._notify_update()

    def get_pending_tasks(self) -> List[BookTask]:
        with self._lock:
            return [t for t in self.tasks if t.status == TaskStatus.QUEUED]

    def get_all_tasks(self) -> List[BookTask]:
        with self._lock:
            return list(self.tasks)

    def clear_completed(self):
        with self._lock:
            self.tasks = [t for t in self.tasks if t.status not in (TaskStatus.COMPLETED, TaskStatus.FAILED)]
        self._notify_update()
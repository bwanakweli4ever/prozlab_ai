
# app/modules/tasks/models/task_enums.py
from enum import Enum


class TaskStatusEnum(str, Enum):
    """Task status enum - values must match database enum exactly"""
    PENDING = "PENDING"        # uppercase to match DB
    ASSIGNED = "ASSIGNED"
    ACCEPTED = "ACCEPTED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


class TaskPriorityEnum(str, Enum):
    """Task priority enum - values must match database enum exactly"""
    LOW = "LOW"               # uppercase to match DB
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    URGENT = "URGENT"
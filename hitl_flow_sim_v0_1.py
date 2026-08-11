from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional

VERSION = "HITL_FLOW_SIM_V0.1"


class Decision(Enum):
    AUTO_CONTINUE = auto()
    LOCAL_HOLD = auto()
    EARLY_HITL = auto()
    MANDATORY_HITL = auto()
    GLOBAL_STOP = auto()


class TaskStatus(Enum):
    PENDING = auto()
    COMPLETED = auto()
    LOCAL_HOLD = auto()
    WAITING_HITL = auto()
    STOPPED = auto()


@dataclass
class SubTask:
    task_id: str
    name: str
    clarity: float
    dependencies: List[str] = field(default_factory=list)
    external_effect: bool = False
    integrity_critical: bool = False
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[str] = None


@dataclass
class HITLRequest:
    task_id: str
    decision: Decision
    reason: str


@dataclass
class AuditEvent:
    event_type: str
    task_id: str
    message: str


class HITLFlowSimulator:
    """Core V0.1 simulator only; no built-in demo scenario."""

    CLARITY_THRESHOLD = 0.75

    def __init__(self, tasks: List[SubTask]):
        self.tasks: Dict[str, SubTask] = {task.task_id: task for task in tasks}
        self.hitl_queue: List[HITLRequest] = []
        self.audit_log: List[AuditEvent] = []
        self.approved_external_tasks: set[str] = set()
        self.completed_order: List[str] = []
        self.global_stop = False

    def log(self, event_type: str, task_id: str, message: str) -> None:
        self.audit_log.append(AuditEvent(event_type, task_id, message))

    def dependencies_satisfied(self, task: SubTask) -> bool:
        return all(
            self.tasks[dependency].status == TaskStatus.COMPLETED
            for dependency in task.dependencies
        )

    def has_downstream_dependents(self, task_id: str) -> bool:
        return any(task_id in task.dependencies for task in self.tasks.values())

    def classify(self, task: SubTask) -> Decision:
        if task.integrity_critical:
            return Decision.GLOBAL_STOP

        if task.external_effect and task.task_id not in self.approved_external_tasks:
            return Decision.MANDATORY_HITL

        if task.clarity < self.CLARITY_THRESHOLD:
            if self.has_downstream_dependents(task.task_id):
                return Decision.EARLY_HITL
            return Decision.LOCAL_HOLD

        return Decision.AUTO_CONTINUE

    def add_hitl_request(
        self,
        task: SubTask,
        decision: Decision,
        reason: str,
    ) -> None:
        if any(request.task_id == task.task_id for request in self.hitl_queue):
            return
        self.hitl_queue.append(HITLRequest(task.task_id, decision, reason))

    def complete_task(self, task: SubTask) -> None:
        task.status = TaskStatus.COMPLETED
        task.result = f"Completed: {task.name}"
        self.completed_order.append(task.task_id)
        self.log("COMPLETED", task.task_id, task.result)

    def execute_task(self, task: SubTask) -> bool:
        if self.global_stop:
            return False
        if task.status != TaskStatus.PENDING:
            return False
        if not self.dependencies_satisfied(task):
            return False

        decision = self.classify(task)
        self.log("DECISION", task.task_id, f"Decision={decision.name}")

        if decision == Decision.AUTO_CONTINUE:
            self.complete_task(task)
            return True

        if decision == Decision.LOCAL_HOLD:
            task.status = TaskStatus.LOCAL_HOLD
            self.log(
                "LOCAL_HOLD",
                task.task_id,
                "Task held locally because it is ambiguous but does not block downstream work.",
            )
            return True

        if decision == Decision.EARLY_HITL:
            task.status = TaskStatus.WAITING_HITL
            self.add_hitl_request(
                task,
                decision,
                "Ambiguity must be resolved because downstream work depends on this task.",
            )
            self.log(
                "EARLY_HITL",
                task.task_id,
                "Human clarification required before dependent tasks continue.",
            )
            return True

        if decision == Decision.MANDATORY_HITL:
            task.status = TaskStatus.WAITING_HITL
            self.add_hitl_request(
                task,
                decision,
                "External effect requires explicit human approval.",
            )
            self.log(
                "MANDATORY_HITL",
                task.task_id,
                "External-effect task stopped for explicit human approval.",
            )
            return True

        if decision == Decision.GLOBAL_STOP:
            task.status = TaskStatus.STOPPED
            self.global_stop = True
            self.log(
                "GLOBAL_STOP",
                task.task_id,
                "Workflow stopped because workflow integrity may no longer be trustworthy.",
            )
            return True

        return False

    def run_until_blocked(self) -> None:
        made_progress = True
        while made_progress and not self.global_stop:
            made_progress = False
            for task in self.tasks.values():
                if task.status != TaskStatus.PENDING:
                    continue
                if self.execute_task(task):
                    made_progress = True

    def resolve_ambiguity(self, task_id: str, new_clarity: float) -> None:
        task = self.tasks[task_id]
        if task.status not in {TaskStatus.LOCAL_HOLD, TaskStatus.WAITING_HITL}:
            raise ValueError(f"{task_id} is not waiting for ambiguity resolution.")

        task.clarity = new_clarity
        task.status = TaskStatus.PENDING
        self.hitl_queue = [r for r in self.hitl_queue if r.task_id != task_id]
        self.log(
            "HITL_CLARIFICATION",
            task_id,
            f"Human resolved ambiguity. New clarity={new_clarity}",
        )

    def approve_external_action(self, task_id: str, approved: bool) -> None:
        task = self.tasks[task_id]
        if not task.external_effect:
            raise ValueError(f"{task_id} is not an external-effect task.")
        if task.status != TaskStatus.WAITING_HITL:
            raise ValueError(f"{task_id} is not waiting for HITL.")

        self.hitl_queue = [r for r in self.hitl_queue if r.task_id != task_id]

        if approved:
            self.approved_external_tasks.add(task_id)
            task.status = TaskStatus.PENDING
            self.log(
                "HITL_APPROVED",
                task_id,
                "Human explicitly approved the external-effect action.",
            )
        else:
            task.status = TaskStatus.STOPPED
            self.log(
                "HITL_REJECTED",
                task_id,
                "Human rejected the external-effect action.",
            )

    def resume(self) -> None:
        if self.global_stop:
            self.log(
                "RESUME_DENIED",
                "WORKFLOW",
                "Resume denied because GLOBAL_STOP is active.",
            )
            return

        self.log(
            "RESUME",
            "WORKFLOW",
            "Workflow resumed without re-running completed tasks.",
        )
        self.run_until_blocked()

    def print_summary(self) -> None:
        print("\n" + "=" * 72)
        print(VERSION)
        print("=" * 72)

        print("\nTASK STATUS")
        for task in self.tasks.values():
            print(f"{task.task_id:>3} | {task.status.name:<14} | {task.name}")

        print("\nHITL QUEUE")
        if not self.hitl_queue:
            print("No pending HITL requests.")
        else:
            for request in self.hitl_queue:
                print(
                    f"{request.task_id} | {request.decision.name} | {request.reason}"
                )

        print("\nCOMPLETED ORDER")
        print(" -> ".join(self.completed_order) if self.completed_order else "None")

        print("\nAUDIT LOG")
        for event in self.audit_log:
            print(
                f"[{event.event_type:<18}] {event.task_id:<10} {event.message}"
            )

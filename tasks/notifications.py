from notifications.services import dispatch_push


def notify_task_assigned(task):
    dispatch_push(
        task.assigned_representative.user,
        title="New task assigned",
        body=f"You've been assigned: {task.service_title}",
        data={"type": "task_assigned", "task_id": task.id},
    )


def notify_task_confirmed(task):
    dispatch_push(
        task.requested_by.user,
        title="Request confirmed",
        body=f"Your {task.service_title} request was confirmed.",
        data={"type": "task_status", "status": "confirmed", "task_id": task.id},
    )


def notify_task_started(task):
    dispatch_push(
        task.requested_by.user,
        title="Work started",
        body=f"Work on your {task.service_title} request has started.",
        data={"type": "task_status", "status": "in_progress", "task_id": task.id},
    )


def notify_task_completed(task):
    dispatch_push(
        task.requested_by.user,
        title="Task completed",
        body=f"Your {task.service_title} request is complete.",
        data={"type": "task_status", "status": "completed", "task_id": task.id},
    )

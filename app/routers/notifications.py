from fastapi import APIRouter, BackgroundTasks

router = APIRouter(
    prefix="/notifications",
    tags=["Notifications"],
)

def write_notification_log(message: str) -> None:
    with open("notification.log", "a", encoding="utf-8") as file:
        file.write(message + "\n")

@router.post("/test")
def create_notification(
    background_tasks: BackgroundTasks,
):
    background_tasks.add_task(
        write_notification_log,
        "Notification requested",
    )

    return {
        "message": "Notification accepted",
    }
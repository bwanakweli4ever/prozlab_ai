# app/modules/tasks/routes.py
from fastapi import APIRouter

# Import controllers
from app.modules.tasks.controllers.task_controller import router as task_router
from app.modules.tasks.controllers.task_request_controller import router as task_request_router

# Create the main router for the tasks module
router = APIRouter()

# Include existing task routes
router.include_router(task_router, tags=["Task Management"])

# Include new task request routes
router.include_router(task_request_router, tags=["Business Task Requests"])

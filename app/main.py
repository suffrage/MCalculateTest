import os
from typing import List

import requests
from fastapi import FastAPI
from fastapi.responses import JSONResponse

import sentry_sdk
from sentry_asgi import SentryMiddleware

from schemas import Calculate, Task, TaskCreated, State, Operation
from worker import plus, minus, divide, multiply

flower_url = os.environ.get("FLOWER_URL")
sentry_sdk.init(dsn=os.environ.get("SENTRY_DSN"),
                environment=os.environ.get("SENTRY_ENV"))

app = FastAPI()


def run_calculate_task(x: int, y: int, operation: Operation):
    match operation:
        case Operation.PLUS:
            task = plus.delay(x, y)
        case Operation.MINUS:
            task = minus.delay(x, y)
        case Operation.DIVIDE:
            task = divide.delay(x, y)
        case Operation.MULTIPLY:
            task = multiply.delay(x, y)
    return task.id


@app.post("/calculate", status_code=201, response_model=TaskCreated)
def calculate(payload: Calculate):
    task_id = run_calculate_task(payload.x, payload.y, payload.operation)
    return JSONResponse({"task_id": task_id})


@app.get("/calculate", status_code=201, response_model=TaskCreated)
def calculate_get(x: int, y: int, operation: Operation):
    task_id = run_calculate_task(x, y, operation)
    return JSONResponse({"task_id": task_id})


def get_task_list(**kwargs):
    r = requests.get(
        f"{flower_url}/api/tasks",
        params={
            k: v for k,
            v in kwargs.items() if v is not None})
    tasks = []
    for _, value in r.json().items():
        value['task_id'] = value.pop('uuid')
        tasks.append(value)
    return tasks


def get_task(task_id: str) -> Task:
    r = requests.get(f"{flower_url}/api/task/result/{task_id}")
    result = r.json()
    result['task_id'] = result.pop('task-id')
    if 'result' not in result:
        result['result'] = None
    return result


@app.get("/tasks", response_model=List[Task])
def get_tasks(limit: int = None, offset: int = None, state: State = None):
    if state is not None:
        state = state.value
    return get_task_list(limit=limit, offset=offset, state=state)


@app.get("/tasks/{task_id}", response_model=Task)
def get_task(task_id: str):
    return get_task(task_id)


app.add_middleware(SentryMiddleware)

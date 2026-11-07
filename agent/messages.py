"""Small typed messages for the private Bureau workflow."""
from uagents import Model


class Work(Model):
    job_id: str
    stage: str
    payload: str


class Result(Model):
    job_id: str
    stage: str
    ok: bool
    payload: str = '{}'
    error: str = ''


class Progress(Model):
    job_id: str
    event: str

import uuid

from utils.logger_config import trace_id_var


def set_trace_id(trace_id=None):
    trace_id = trace_id or str(uuid.uuid4())[:8]
    token = trace_id_var.set(trace_id)
    return token


def reset_trace_id(token=None):
    trace_id_var.reset(token)

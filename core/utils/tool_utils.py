import json


def json_success(msg):
    return json.dumps({"status": "success", "message": msg})


def json_error(msg):
    return json.dumps({"status": "error", "message": msg})


def json_partial_success(msg):
    return json.dumps({"status": "partial_success", "message": msg})

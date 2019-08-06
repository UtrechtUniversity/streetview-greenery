import datetime

def get_time_from_str(dt_str):
    try:
        dt = datetime.datetime.strptime(dt_str, "%Y-%m-%dT%H:%M:%S.%fZ")
    except ValueError:
        dt = datetime.datetime.strptime(dt_str, "%Y-%m-%dT%H:%M:%SZ")
    return dt

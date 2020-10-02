import datetime


def get_time_from_str(dt_str):
    time_formats = ["%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ",
                    "%Y-%m-%d %H:%M:%S.%f"]
    for t_format in time_formats:
        try:
            return datetime.datetime.strptime(dt_str, t_format)
        except ValueError:
            pass

    raise ValueError(f"Error converting time '{dt_str}'.")

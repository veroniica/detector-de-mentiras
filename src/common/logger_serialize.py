import datetime


def logger_serialize(response):
    return {
        k: str(v) if isinstance(v, (datetime.datetime, datetime.date)) else v
        for k, v in response.items()
    }

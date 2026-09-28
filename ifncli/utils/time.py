
from datetime import datetime

ISO_TIME_FORMAT = "%Y-%m-%dT%H:%M:%S"

def from_iso_time(time:str):
    return datetime.strptime(time, ISO_TIME_FORMAT)

def to_iso_time(d):
    return d.strftime(ISO_TIME_FORMAT)

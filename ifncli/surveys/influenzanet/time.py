
from datetime import datetime

class Timestamp:

    def __init__(self, value):
        """
        docstring
        """
        self.value = int(value)

    def __repr__(self):
        return "<timestamp %d>" % self.value

    def to_time(self):
        return datetime.fromtimestamp(self.value)

    def to_readable(self, ctx):
        return self.to_time()
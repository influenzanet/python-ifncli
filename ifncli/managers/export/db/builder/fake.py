from .base import SourceDataLoader
from collections import OrderedDict
from typing import Union

class FakeColumnsData:

    def __init__(self, columns:list[str], version:Union[str, list[str]], rows:int=1):
        self.data = []
        if isinstance(version, str):
            version = [version]
        self.build(columns, version, rows)

    def build(self, columns: list[str], versions:list[str], rows: int):
        
        row_template = dict[str, any]([ (column, True) for column in columns])
        
        for version in versions:
            for i in range(rows):
                row = row_template.copy()
                row['version'] = version
                self.data.append(row)


class FakeDataLoader(SourceDataLoader):

    def __init__(self, data: list[dict]):
        self.data = data

    def total_rows(self):
        return len(self.data)
    
    def load(self, batch_size, offset):
        count = 0
        records = OrderedDict()
        max_rows = len(self.data)
        index = offset
        while(index < max_rows):
            r = self.data[index]
            version = r['version']
            if version not in records:
                records[version] = []
            records[version].append(r)
            count += 1
            index += 1
        return (count, records)
from typing import Optional, TextIO

def default_column_formatter(column:str, value):
    return value

class TableFormatter:
    """
        Format table using dictionary
    """
    def __init__(self, column_formatter: Optional[type[default_column_formatter]]=None):
        self.columns = []
        if column_formatter is None:
            self.column_formatter = default_column_formatter
        else:
            self.column_formatter = column_formatter
        self.width = {}
        self.data = []
        self.headers = {}

    def reorder(self, columns: list[str]):
        """
            Reorder columns to put the columns in args as first columns
        """
        cc = []
        for col in columns: 
            if col in self.columns:
                cc.append(col)
        for col in self.columns:
            if col not in cc:
                cc.append(col)
        self.columns = cc

    def set_header(self, column: str, label: str):
        self.header[column] = label
    
    def append(self, d:dict):
        o = {}
        for k, v in d.items():
            if k not in self.columns:
                self.columns.append(k)
            value = str(self.column_formatter(k, v))
            self.adjust_width(k, len(value))
            o[k] = value
        self.data.append(o)
    
    def adjust_width(self, column, width: int):
        w = self.width.get(column, 0)
        w = max(w, width)
        self.width[column] = w
        return w

    def print(self, out: TextIO):

        def write_line(s):
            out.write(s)
            out.write('\n')

        tpl = []
        for column in self.columns:
            w = self.adjust_width(column, len(column))
            tpl.append('{' + column +':<' + str(w) +'}')
        row_template = "| " + " | ".join(tpl) + " |"

        h = dict( (column, self.headers.get(column, column)) for column in self.columns)
        r = row_template.format(**h)
        write_line(r)
       
        h = dict( (column, '-' * self.width.get(column)) for column in self.columns)
        r = row_template.format(**h)
        write_line(r)

        for row in self.data:
            row_data = dict( (column, row.get(column, '')) for column in self.columns )
            r = row_template.format(**row_data)
            write_line(r)

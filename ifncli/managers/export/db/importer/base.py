import pandas

class SourceDataLoader:
    """
        Load data from a data source (like database) for the importer
    """

    def total_rows(self)->int:
        """
            Total number of rows
        """
        raise NotImplementedError()
    
    def load(self, batch_size: int, offset:int)->tuple[int, dict]:
        raise NotImplementedError()
    

class Writer:
    """
        Writer class append data frame 
    """
    def close(self):
        pass

    def append(self, df: pandas.DataFrame):
        pass


class PrintWriter(Writer):

    def append(self, df: pandas.DataFrame):
        print(df.info(True))
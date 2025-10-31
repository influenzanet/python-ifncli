
from .database import ExportDatabase
from typing import Optional
import zlib
import time
try:
    import zstd
    zstd_available = True
except ImportError:
    zstd_available = False

class Compressor:

    def __init__(self, compressor: str) -> None:
        (compress, decompress) = self.compressor_from_name(compressor)
        if compress is None or decompress is None:
            raise ValueError("Unknown compressor '{}'".format(compressor))
        self.compress = compress
        self.decompress = decompress
        self.name = compressor
    
    def compressor_from_name(self, compressor:str):
        compress = None
        decompress = None
        if compressor == 'zlib':
            compress = zlib.compress
            decompress = zlib.decompress
        if compressor == 'zlib-1':
            compress = lambda x: zlib.compress(x, 1)
            decompress = zlib.decompress
        if compressor == 'zlib-3':
            compress = lambda x: zlib.compress(x, 3)
            decompress = zlib.decompress
        if compressor == "zstd":
            if zstd_available:
                compress = zstd.compress # type: ignore
                decompress = zstd.decompress # type: ignore
            else:
                raise NotImplementedError("Cannot use zstd not available, install `zstd` package")
        if compressor == 'none':
            func = lambda x: x
            compress = func
            decompress = func
        return (compress, decompress)

class Evaluator:
    def __init__(self, compressor: Compressor) -> None:
        self.size = 0
        self.time = 0
        self.name = compressor.name
        self.compressor = compressor

    def compress(self, value):
        start = time.perf_counter_ns()
        z = self.compressor.compress(value)
        end = time.perf_counter_ns()
        self.size += len(z)
        self.time += end - start

class CompressEvaluator:
    """
        Reason for response:db commands not available (missing module)
    """
    def __init__(self, db) -> None:
        self.db = ExportDatabase(db)

    def evaluate(self, survey:str):
        total_size = 0
        
        table = self.db.response_table(survey)

        cc = ['zlib', 'zlib-1', 'zlib-3']
        if zstd_available:
            cc.append('zstd')
        else:
            print("`ztsd` not available")
        evaluators = []
        for name in cc:
            evaluators.append(Evaluator(Compressor(name)))
        for row in self.db.fetch_all("select data from {}".format(table)):
            json = bytes(row[0], 'utf-8')
            size = len(json)
            total_size += size
            for compressor in evaluators:
                compressor.compress(json)
        print("Total size {}".format(total_size))
        for compressor in evaluators:
            percent = 100 * compressor.size / total_size
            print("{} {} {:.2f}% {:.2f}ms".format(compressor.name, compressor.size, percent, compressor.time/1000000))

def get_best_compressor_available():
    if zstd_available:
        return 'zstd'
    return 'zlib-1'
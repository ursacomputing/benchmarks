import time

import click
import conbench.runner
import pyarrow
import pyarrow.feather as feather
import pyarrow.parquet as parquet

from benchmarks import _benchmark, _sources


CASES = [
    ("parquet", "uncompressed", "table"),
    ("parquet", "uncompressed", "dataframe"),
    ("parquet", "snappy", "table"),
    ("parquet", "snappy", "dataframe"),
    ("feather", "uncompressed", "table"),
    ("feather", "uncompressed", "dataframe"),
    ("feather", "lz4", "table"),
    ("feather", "lz4", "dataframe"),
    ("feather", "zstd", "table"),
    ("feather", "zstd", "dataframe"),
]
CHOICES = {
    "file_type": ("feather", "parquet"),
    "compression": ("uncompressed", "snappy", "lz4", "zstd"),
    "type": ("table", "dataframe"),
}


class FileBenchmark(_benchmark.Benchmark, _benchmark.BenchmarkR):
    def run(self, source, case=None, cpu_count=None, **kwargs):
        if not isinstance(source, _sources.Source):
            source = _sources.Source(source)

        cases = self.get_cases(case, kwargs)
        tags = self.get_tags(source, cpu_count)
        language = kwargs.get("language", "Python").lower()
        msg = "Warning: arrowbench doesn't support the compression=lz4 case."

        for case in cases:
            _, compression, _ = case
            if compression == "lz4" and language == "r":
                click.echo(click.style(msg, fg="red"))
                continue
            if language == "python":
                f = self._get_benchmark_function(source, case)
                yield self.benchmark(f, tags, kwargs, case)
            elif language == "r":
                command = self._get_r_command(source, case, kwargs)
                yield self.r_benchmark(command, tags, kwargs, case)

    def _get_r_command(self, source, case, options):
        file_type, compression, _type = case
        _type = "arrow_table" if _type == "table" else "data_frame"
        _name = "input" if self.r_name == "write_file" else "output"
        return (
            f"library(arrowbench); "
            f"run_one({self.r_name}, "
            f'source="{source.name}", '
            f'format="{file_type}", '
            f'compression="{compression}", '
            f'{_name}="{_type}", '
            f'n_iter={options.get("iterations", 1)}, '
            f"cpu_count={self.r_cpu_count(options)})"
        )


@conbench.runner.register_benchmark
class FileReadBenchmark(FileBenchmark):
    """
    Read parquet & feather files to arrow tables & pandas data frames.

        FileReadBenchmark().run(<source>, options...)

    Parameters
    ----------
    source : str
        A source name from the benchmarks source store.
    all : boolean, optional
        Run all benchmark cases
    language : str, optional
        Valid values: "Python", "R".
    file_type : str, optional
        The file type of the file to read ("parquet" or "feather").
    compression : str, optional
        Valid values: "uncompressed", "snappy", "lz4", "zstd".
    output_type : str, optional
        The target output type on read ("table" or "dataframe").
    case : sequence, optional
        Benchmark options as a sequence (rather than individual params):
        [<file_type>, <compression>, <output_type>]
    cpu_count : int, optional
        Set the number of threads to use in parallel operations (arrow).
    iterations : int, default 1
        Number of times to run the benchmark.
    gc_collect : boolean, default True
        Whether to do garbage collection before each benchmark run.
    gc_disable : boolean, default True
        Whether to do disable collection during each benchmark run.
    run_id : str, optional
        Group executions together with a run id.

    Returns
    -------
    (result, output) : sequence
        result : The benchmark result.
        output : The output from the benchmarked function.
    """

    name, r_name = "file-read", "read_file"
    valid_cases = [("file_type", "compression", "output_type")] + CASES
    arguments = ["source"]
    options = {
        "language": {"type": str, "choices": ["Python", "R"]},
        "cpu_count": {"type": int},
    }

    def _get_benchmark_function(self, source, case):
        file_type, compression, output_type = case
        path = source.create_if_not_exists(file_type, compression)

        if file_type == "parquet" and output_type == "table":
            f = lambda: parquet.read_table(path, memory_map=False)
        elif file_type == "parquet" and output_type == "dataframe":
            f = lambda: parquet.read_table(path, memory_map=False).to_pandas()
        elif file_type == "feather" and output_type == "table":
            f = lambda: feather.read_table(path, memory_map=False)
        elif file_type == "feather" and output_type == "dataframe":
            f = lambda: feather.read_feather(path, memory_map=False)

        return f


@conbench.runner.register_benchmark
class FileWriteBenchmark(FileBenchmark):
    """
    Write parquet & feather files from arrow tables & pandas data frames.

        FileWriteBenchmark().run(<source>, options...)

    Parameters
    ----------
    source : str
        A source name from the benchmarks source store.
    all : boolean, optional
        Run all benchmark cases
    language : str, optional
        Valid values: "Python", "R".
    file_type : str, optional
        The resulting file type on write ("feather" or "parquet").
    compression : str, optional
        Valid values: "uncompressed", "snappy", "lz4", "zstd".
    input_type : str, optional
        The type of the data to read ("table" or "dataframe").
    case : sequence, optional
        Benchmark options as a sequence (rather than individual params):
        [<file_type>, <compression>, <input_type>]
    cpu_count : int, optional
        Set the number of threads to use in parallel operations (arrow).
    iterations : int, default 1
        Number of times to run the benchmark.
    gc_collect : boolean, default True
        Whether to do garbage collection before each benchmark run.
    gc_disable : boolean, default True
        Whether to do disable collection during each benchmark run.
    run_id : str, optional
        Group executions together with a run id.

    Returns
    -------
    (result, output) : sequence
        result : The benchmark result.
        output : The output from the benchmarked function.
    """

    name, r_name = "file-write", "write_file"
    valid_cases = [("file_type", "compression", "input_type")] + CASES
    arguments = ["source"]
    options = {
        "language": {"type": str, "choices": ["Python", "R"]},
        "cpu_count": {"type": int},
    }

    def _get_benchmark_function(self, source, case):
        file_type, compression, input_type = case
        path = source.temp_path(file_type, compression)

        # Create outside benchmark function because creating the table
        # and dataframe is expensive and should be excluded from the
        # timing because it is benchmark setup.
        start = time.time()
        if input_type == "table":
            table = source.table
        if input_type == "dataframe":
            dataframe = source.dataframe
        print(f"Time to create table/dataframe {time.time() - start}")

        comp = _sources.munge_compression(compression, file_type)
        if file_type == "parquet" and input_type == "table":
            f = lambda: parquet.write_table(table, path, compression=comp)
        elif file_type == "parquet" and input_type == "dataframe":
            f = lambda: parquet.write_table(
                self._table(dataframe), path, compression=comp
            )
        elif file_type == "feather" and input_type == "table":
            f = lambda: feather.write_feather(table, path, compression=comp)
        elif file_type == "feather" and input_type == "dataframe":
            f = lambda: feather.write_feather(dataframe, path, compression=comp)

        return f

    def _table(self, dataframe):
        return pyarrow.Table.from_pandas(
            dataframe, preserve_index=False
        ).replace_schema_metadata(None)
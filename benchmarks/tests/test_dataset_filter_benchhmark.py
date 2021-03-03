import json

from .. import _sources
from .. import dataset_filter_benchmark
from ..tests._asserts import assert_benchmark, assert_cli


HELP = """
Usage: conbench dataset-filter [OPTIONS] SOURCE

  Run dataset-filter benchmark.

Options:
  --cpu-count INTEGER
  --iterations INTEGER   [default: 1]
  --gc-collect BOOLEAN   [default: true]
  --gc-disable BOOLEAN   [default: true]
  --show-result BOOLEAN  [default: true]
  --show-output BOOLEAN  [default: false]
  --run-id TEXT          Group executions together with a run id.
  --help                 Show this message and exit.
"""


nyctaxi = _sources.Source("nyctaxi_sample")


def test_dataset_filter_nyctaxi():
    benchmark = dataset_filter_benchmark.DatasetFilterBenchmark()
    [(result, output)] = benchmark.run(nyctaxi, iterations=1)
    assert_benchmark(result, nyctaxi.name, benchmark.name)
    print(json.dumps(result, indent=4, sort_keys=True))
    assert "pyarrow.Table" in str(output)


def test_dataset_filter_cli():
    command = ["conbench", "dataset-filter", "--help"]
    assert_cli(command, HELP)
import copy
import json

import pytest

from .. import _sources
from .. import dataset_read_benchmark
from ..tests._asserts import assert_cli, assert_context


HELP = """
Usage: conbench dataset-read [OPTIONS] SOURCE

  Run dataset-read benchmark(s).

  For each benchmark option, the first option value is the default.

  Valid benchmark combinations:
  --pre-buffer=true
  --pre-buffer=false

  To run all combinations:
  $ conbench dataset-read --all=true

Options:
  --pre-buffer [false|true]
  --all BOOLEAN              [default: false]
  --cpu-count INTEGER
  --iterations INTEGER       [default: 1]
  --gc-collect BOOLEAN       [default: true]
  --gc-disable BOOLEAN       [default: true]
  --show-result BOOLEAN      [default: true]
  --show-output BOOLEAN      [default: false]
  --run-id TEXT              Group executions together with a run id.
  --help                     Show this message and exit.
"""


nyctaxi = _sources.Source("nyctaxi_multi_parquet_s3_sample")
benchmark = dataset_read_benchmark.DatasetReadBenchmark()


def assert_benchmark(result, case, source):
    munged = copy.deepcopy(result)

    legacy = {
        "name": "dataset-read",
        "dataset": source,
        "cpu_count": None,
        "gc_collect": True,
        "gc_disable": True,
        "pre_buffer": None,
    }
    pre_buffer = {
        "name": "dataset-read",
        "dataset": source,
        "cpu_count": None,
        "gc_collect": True,
        "gc_disable": True,
        "pre_buffer": case[0],
    }

    try:
        assert munged["tags"] == pre_buffer
    except AssertionError:
        assert munged["tags"] == legacy

    assert_context(munged)


@pytest.mark.parametrize("case", benchmark.cases, ids=benchmark.case_ids)
def test_dataset_read(case):
    [(result, output)] = benchmark.run(nyctaxi, case, iterations=1)
    assert_benchmark(result, case, nyctaxi.name)
    print(json.dumps(result, indent=4, sort_keys=True))
    assert "pyarrow.Table" in str(output)


def test_dataset_read_cli():
    command = ["conbench", "dataset-read", "--help"]
    assert_cli(command, HELP)
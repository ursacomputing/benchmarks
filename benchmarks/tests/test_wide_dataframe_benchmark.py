import copy
import json

import pytest

from .. import wide_dataframe_benchmark
from ..tests._asserts import assert_cli, assert_context


HELP = """
Usage: conbench wide-dataframe [OPTIONS]

  Run wide-dataframe benchmark(s).

  For each benchmark option, the first option value is the default.

  Valid benchmark combinations:
  --use-legacy-dataset=true
  --use-legacy-dataset=false

  To run all combinations:
  $ conbench wide-dataframe --all=true

Options:
  --use-legacy-dataset [false|true]
  --all BOOLEAN                   [default: false]
  --cpu-count INTEGER
  --iterations INTEGER            [default: 1]
  --gc-collect BOOLEAN            [default: true]
  --gc-disable BOOLEAN            [default: true]
  --show-result BOOLEAN           [default: true]
  --show-output BOOLEAN           [default: false]
  --run-id TEXT                   Group executions together with a run id.
  --help                          Show this message and exit.
"""


benchmark = wide_dataframe_benchmark.WideDataframeBenchmark()


def assert_benchmark(result, case):
    munged = copy.deepcopy(result)
    assert munged["tags"] == {
        "name": "wide-dataframe",
        "cpu_count": None,
        "gc_collect": True,
        "gc_disable": True,
        "use_legacy_dataset": case[0],
    }
    assert_context(munged)


@pytest.mark.parametrize("case", benchmark.cases, ids=benchmark.case_ids)
def test_wide_dataframe(case):
    [(result, output)] = benchmark.run(case, iterations=1)
    assert_benchmark(result, case)
    print(json.dumps(result, indent=4, sort_keys=True))
    assert "100 rows x 10000 columns" in str(output)


def test_wide_dataframe_read_cli():
    command = ["conbench", "wide-dataframe", "--help"]
    assert_cli(command, HELP)
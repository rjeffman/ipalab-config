"""Test steps that deal with file data"""

import re

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap, CommentedSeq

from behave import then


def deep_diff(a, b, ignore=None, level=""):
    """Deep compare two dicts or ruamel.yaml data."""

    def convert_ruamel_data(data):
        if isinstance(data, CommentedMap):
            return dict(data)
        if isinstance(data, CommentedSeq):
            return list(data)
        return data

    a = convert_ruamel_data(a)
    b = convert_ruamel_data(b)
    if isinstance(a, dict) and isinstance(b, dict):
        diff_keys = (set(a.keys()) ^ set(b.keys())) - set(ignore or [])
        assert (
            not diff_keys
        ), f"Keys mismatch ({level}): {set(a.keys())} / {set(b.keys())}"
        for key in a.keys():
            deep_diff(
                a[key], b[key], ignore, f"{level}.{key}" if level else key
            )
    elif isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        assert len(a) == len(b), f"List sizes mismatch ({level})."
        for index, (a_v, b_v) in enumerate(zip(a, b)):
            deep_diff(a_v, b_v, f"{level}.{index}")
    else:
        assert isinstance(
            b, type(a)
        ), f"Type mismatch ({level}): {type(a)} - {type(b)}"
        assert b == a, f"Data mismatch ({level}): {a} - {b}"


@then("the {filename} file contains")  # pylint: disable=E1102
def _then_file_contents(context, filename):
    # This assumes all writes are done through the "save_file" function
    write_calls = iter(context.patches["open_file"]().write.call_args_list)
    for call in context.patches["open_file"].call_args_list:
        if call.args and (
            call.args[1].startswith("w") and not call.args[0].endswith(".yml")
        ):
            try:
                observed = "".join(next(write_calls)[0])  # file data
            except StopIteration:
                raise AssertionError("Not enough writes to files") from None
            if call.args[0] == filename:
                assert (
                    re.match(re.compile(context.text), observed) is not None
                ), f"Expected:\n{context.text}\nObserved:\n{observed}\n"
                break
    else:
        raise AssertionError("File not written.")


@then("the {filename} file is")  # pylint: disable=E1102
def _then_yaml_file_contents(context, filename):
    expected = YAML(pure=True).load(context.text)

    for index, call in enumerate(  # noqa: B007
        context.patches["yaml_dump"].call_args_list
    ):
        a_b = set(expected.keys()) - set(call.args[0].keys())
        b_a = set(expected.keys()) - set(call.args[0].keys())
        if not a_b or not b_a:
            deep_diff(expected, call.args[0])
            break
    else:
        index = -1

    assert index >= 0, "No file created with given data."

    called = [
        call.args[0]
        for call in context.patches["open_file"].call_args_list
        if call.args[1].startswith("w") and call.args[0].endswith(".yml")
    ]
    assert bool(called), "No files were created!"
    assert (
        called[index] == filename
    ), f"Data was created in the wrong file: {called[index]}"

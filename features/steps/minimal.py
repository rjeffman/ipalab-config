"""Steps for ensuring behavior on minimal configuration usage."""

import os
import importlib.resources

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap, CommentedSeq

from behave import given, then


def deep_diff(a, b, level=""):
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
        diff_keys = set(a.keys()) - set(b.keys())
        assert (
            not diff_keys
        ), f"Keys mismatch ({level}): {set(a.keys())} / {set(b.keys())}"
        diff_keys = set(b.keys()) - set(a.keys())
        assert (
            not diff_keys
        ), f"Keys mismatch ({level}): {set(a.keys())} / {set(b.keys())}"
        for key in a.keys():
            deep_diff(a[key], b[key], f"{level}.{key}" if level else key)
    elif isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        assert len(a) == len(b), f"List sizes mismatch ({level})."
        for index, (a_v, b_v) in enumerate(zip(a, b)):
            deep_diff(a_v, b_v, f"{level}.{index}")
    else:
        assert isinstance(
            b, type(a)
        ), f"Type mismatch ({level}): {type(a)} - {type(b)}"
        assert b == a, f"Data mismatch ({level}): {a} - {b}"


@given("the deployment configuration")  # pylint: disable=E1102
def _given_deployment_configuration(context):
    context.input_data = context.text
    args = getattr(context, "cli_args", ["ipalab-config"])
    args.extend(["input_data"])
    context.cli_args = args


@then('the output directory name is "{dirname}"')  # pylint: disable=E1102
def _then_output_directory_created_with_correct_name(context, dirname):
    call_list = [
        (dirname,) == call.args
        for call in context.patches["make_dirs"].call_args_list
    ]
    assert any(call_list), f"No call 'os.makedirs' with '{dirname}'"


@then("the {filename} file is")  # pylint: disable=E1102
def _then_(context, filename):
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
        for call in context.patches["input_file"].call_args_list
        if call.args[1].startswith("w")
    ]
    assert bool(called), "No files were created!"
    assert (
        called[index] == filename
    ), f"Data was created in the wrong file: {called[index]}"


# Modify the test to check for specific files.
# @then('the "{directory}" directory contains [{file_list}]')
@then('the "{directory}" directory was copied')  # pylint: disable=E1102
def _then_directory_contains(context, directory):
    source = os.path.join(
        importlib.resources.files("ipalab_config"),
        "data",
        os.path.basename(directory),
    )
    call_list = [
        (source, directory) == call.args
        for call in context.patches["copy_tree"].call_args_list
    ]
    assert any(call_list), f"No call 'shutil.copytree' for '{directory}'"

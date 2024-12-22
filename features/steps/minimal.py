"""Steps for ensuring behavior on minimal configuration usage."""

import sys
import os
import importlib.resources

from unittest.mock import patch, mock_open

from ruamel.yaml import YAML
from behave import given, when, then

from ipalab_config.__main__ import main


@given("the deployment configuration")  # pylint: disable=E1102
def _given_deployment_configuration(context):
    context.input_data = context.text
    args = getattr(context, "cli_args", ["ipalab-config"])
    args.extend(["input_data"])
    context.cli_args = args


@when("I run ipalab-config")  # pylint: disable=E1102
def _when_run_ipalab(context):
    sys.argv = context.cli_args
    with (
        patch(
            "builtins.open", mock_open(read_data=context.input_data)
        ) as input_file,
        patch("shutil.copytree") as copy_tree,
        patch("shutil.copyfile") as copy_file,
        patch("os.makedirs") as make_dirs,
        patch("ruamel.yaml.YAML.dump") as yaml_dump,
    ):
        context.patches = {
            "input_file": input_file,
            "copy_tree": copy_tree,
            "copy_file": copy_file,
            "make_dirs": make_dirs,
            "yaml_dump": yaml_dump,
        }
        try:
            context.err_code = main()
        except Exception as ex:  # pylint: disable=broad-except
            raise ex from None


@then('the output directory name is "{dirname}"')  # pylint: disable=E1102
def _then_output_directory_created_with_correct_name(context, dirname):
    call_list = [
        (dirname,) == call.args
        for call in context.patches["make_dirs"].call_args_list
    ]
    assert any(call_list), f"No call 'os.makedirs' with '{dirname}'"


@then("the {filename} file is")  # pylint: disable=E1102
def _then_(context, filename):
    expected = YAML().load(context.text)
    found_results = [
        call.args
        for ndx, call in enumerate(context.patches["yaml_dump"].call_args_list)
    ]
    found_results = [
        ndx
        for ndx, call in enumerate(context.patches["yaml_dump"].call_args_list)
        if dict(expected) == call.args[0]
    ]
    assert bool(found_results) is True, "No file created with given data."
    assert (
        len(found_results) == 1
    ), f"Too many files with the same data: {len(found_results)}"

    index = found_results[0]
    called = [
        call.args[0]
        for call in context.patches["input_file"].call_args_list
        if call.args[1].startswith("w")
    ]
    assert bool(called), "No files were created!"
    assert (
        called[index] == filename
    ), f"Data was created in the wrong file: {filename}"


#
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

"""Steps for ensuring behavior on minimal configuration usage."""

import os
import importlib.resources

from behave import given, then


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

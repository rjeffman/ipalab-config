"""Steps for ensuring behavior on minimal configuration usage."""

import os
import importlib.resources

from behave import then


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


@then('the file "{src}" was copied to "{dest}"')  # pylint: disable=E1102
def _then_file_was_copied(context, src, dest):
    assert any(
        call.args[0].endswith(src) and call.args[1].endswith(dest)
        for call in context.patches["copy_file"].call_args_list
    ), f"File {src} was not copied to {dest}"

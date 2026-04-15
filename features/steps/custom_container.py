"""Steps to verify custom container behavior."""

import os

from behave import given, then


@given('the command line arguments "{cli_args}"')  # pylint: disable=E1102
def _given_cli_args(context, cli_args):
    args = getattr(context, "cli_args", ["ipalab-config"])
    args.extend(cli_args.split(" "))
    context.cli_args = args


@then(  # pylint: disable=E1102
    'the file "{filename}" is copied to directory "{directory}"'
)
def _then_directory_contains_file(context, directory, filename):
    source = os.path.join(os.getcwd(), filename)
    dest = os.path.join(directory, os.path.basename(filename))
    # Check both copy and copyfile as code may use either
    copy_calls = context.patches["copy"].call_args_list
    copyfile_calls = context.patches["copy_file"].call_args_list
    assert any(
        (source, dest) == call.args or (filename, dest) == call.args
        for call in copy_calls + copyfile_calls
    ), f"File '{filename}' was not copied to '{directory}'"

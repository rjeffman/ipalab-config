"""Steps to verify custom container behavior."""

import os

from behave import given, then


@given('the command line arguments "{cli_args}"')
def _given_cli_args(context, cli_args):
    args = getattr(context, "cli_args", ["ipalab-config"])
    args.extend(cli_args.split(" "))
    context.cli_args = args


@then('the file "{filename}" is copied to directory "{directory}"')
def _then_directory_contains_file(context, directory, filename):
    source = os.path.join(os.getcwd(), filename)
    dest = os.path.join(directory, os.path.basename(filename))
    assert any(
        (source, dest) == call.args or (filename, dest)
        for call in context.patches["copy_file"].call_args_list
    ), f"File '{filename}' was not copied to '{directory}'"

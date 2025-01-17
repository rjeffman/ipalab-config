"""Steps to execute ipalab-config"""

import sys
import re

from unittest.mock import patch, mock_open

from behave import given, when, then

from ipalab_config.__main__ import main, generate_ipalab_configuration


def patched_execution(fn):
    """Add patches for execution of 'when' steps"""

    def run_patched(context, *args, **kwargs):
        sys.argv = context.cli_args
        with (
            patch(
                "builtins.open",
                mock_open(read_data=context.input_data),
                create=True,
            ) as open_file,
            patch("shutil.copytree") as copy_tree,
            patch("shutil.copyfile") as copy_file,
            patch("os.makedirs") as make_dirs,
            patch("ruamel.yaml.YAML.dump") as yaml_dump,
        ):
            context.patches = {
                "open_file": open_file,
                "copy_tree": copy_tree,
                "copy_file": copy_file,
                "make_dirs": make_dirs,
                "yaml_dump": yaml_dump,
            }
            fn(context, *args, **kwargs)

    return run_patched


@given("the deployment configuration")  # pylint: disable=E1102
def _given_deployment_configuration(context):
    context.input_data = context.text
    args = getattr(context, "cli_args", ["ipalab-config"])
    args.extend(["input_data"])
    context.cli_args = args


@when("I run ipalab-config")  # pylint: disable=E1102
@patched_execution
def _when_run_ipalab(context):
    context.err_code = main()


@when("I expect ipalab-config to fail")  # pylint: disable=E1102
@patched_execution
def _when_run_ipalab_exception(context):
    try:
        generate_ipalab_configuration()
    except Exception as ex:  # pylint: disable=broad-except
        context.exception = ex
    else:
        raise AssertionError("An error was expected, but did not occur.")


@then(  # pylint: disable=E1102
    'an error {exception} occurs, with message "{msg}"'
)
def _then_an_error_msg(context, exception, msg):
    assert (
        getattr(context, "exception", None) is not None
    ), "No exception occurred"
    exception_class = getattr(sys.modules["builtins"], exception, None)
    assert isinstance(context.exception, exception_class)
    assert re.match(re.compile(msg), str(context.exception))

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
            patch("shutil.copy") as copy,
            patch("os.makedirs") as make_dirs,
            patch("ruamel.yaml.YAML.dump") as yaml_dump,
            patch("os.path.isfile"),
            patch("os.access"),
            patch("ipalab_config.logger.logger.warning") as logger_warning,
        ):
            context.patches = {
                "open_file": open_file,
                "copy_tree": copy_tree,
                "copy_file": copy_file,
                "copy": copy,
                "make_dirs": make_dirs,
                "yaml_dump": yaml_dump,
                "logger_warning": logger_warning,
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
    assert isinstance(context.exception, exception_class), (
        "Exception: Expected: "
        f"{str(exception_class)} / {type(context.exception)}"
    )
    assert re.match(re.compile(msg), str(context.exception))


# pylint: disable=E1102
@then("a warning message is displayed about no servers defined for domain")
def _then_warning_no_servers(context):
    logger_warning = context.patches.get("logger_warning")
    assert logger_warning is not None, "Logger warning patch not found"
    assert logger_warning.called, "No warning was logged"

    # Check if any warning message contains "No servers defined for domain"
    warning_found = False
    for call in logger_warning.call_args_list:
        args, _ = call
        if args and "No servers defined for domain" in args[0]:
            warning_found = True
            break

    assert warning_found, (
        f"Expected warning about 'No servers defined for domain' but got: "
        f"{[call[0] for call in logger_warning.call_args_list]}"
    )


# pylint: disable=E1102
@then("a warning message is displayed about no IPA deployments")
def _then_warning_no_ipa_deployments(context):
    logger_warning = context.patches.get("logger_warning")
    assert logger_warning is not None, "Logger warning patch not found"
    assert logger_warning.called, "No warning was logged"

    # Check if any warning message contains "No IPA deployment will be created"
    warning_found = False
    for call in logger_warning.call_args_list:
        args, _ = call
        if args and "No IPA deployment will be created" in args[0]:
            warning_found = True
            break

    assert warning_found, (
        f"Expected warning about 'No IPA deployment will be created' but got: "
        f"{[call[0] for call in logger_warning.call_args_list]}"
    )

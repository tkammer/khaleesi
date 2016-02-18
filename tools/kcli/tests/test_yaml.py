import os.path

import configure
import pytest
import yaml

from tests.test_cwd import utils

our_cwd_setup = utils.our_cwd_setup


def test_unsupported_yaml_constructor(our_cwd_setup):
    from kcli.utils import update_settings
    from kcli.exceptions import IRYAMLConstructorError
    tester_file = 'IRYAMLConstructorError.yml'
    settings = configure.Configuration.from_dict({})
    with pytest.raises(IRYAMLConstructorError):
        update_settings(settings, os.path.join(utils.TESTS_CWD, tester_file))


def test_placeholder_validator(our_cwd_setup):
    from kcli.utils import update_settings
    from kcli.exceptions import IRPlaceholderException

    # Checks that 'IRPlaceholderException' is raised if value isn't been
    # overwritten
    tester_file = 'placeholder_injector.yml'
    settings = configure.Configuration.from_dict({})
    with pytest.raises(IRPlaceholderException) as exc:
        settings = update_settings(settings,
                                   os.path.join(utils.TESTS_CWD, tester_file))
        yaml.safe_dump(settings, default_flow_style=False)
    assert "Mandatory value is missing." in str(exc.value.message)

    # Checks that exceptions haven't been raised after overwriting the
    # placeholder
    tester_file = 'placeholder_overwriter.yml'
    update_settings(settings, os.path.join(utils.TESTS_CWD, tester_file))

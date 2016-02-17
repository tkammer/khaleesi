import os.path

import pytest
import configure

from tests.test_cwd import utils
from kcli.utils import update_settings
from kcli.exceptions import IRYAMLConstructorError


def test_unsupported_yaml_constructor():
    tester_file = 'IRYAMLConstructorError.yml'
    settings = configure.Configuration.from_dict({})
    with pytest.raises(IRYAMLConstructorError):
        update_settings(settings, os.path.join(utils.TESTS_CWD, tester_file))

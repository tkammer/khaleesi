import os.path

import pytest
import configure

from kcli.utils import update_settings
from kcli.exceptions import IRYAMLConstructorError

TESTS_DIR = os.path.dirname(__file__)
TEST_DIR = os.path.splitext(os.path.basename(__file__))[0]
YAML_FILE_NAME = 'IRYAMLConstructorError.yml'

TESTER_FILE = os.path.join(TESTS_DIR, TEST_DIR, YAML_FILE_NAME)


def test_unsupported_yaml_constructor():
    settings = configure.Configuration.from_dict({})
    with pytest.raises(IRYAMLConstructorError):
        update_settings(settings, TESTER_FILE)

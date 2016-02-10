import os
import pytest

from tests.test_cwd import consts as test_const

MYCWD = test_const.TESTS_CWD


@pytest.fixture()
def our_cwd_setup(request):
    """Change cwd to test_cwd dir. Revert to original dir on teardown. """

    bkp = os.getcwd()

    def our_cwd_teardown():
        os.chdir(bkp)

    request.addfinalizer(our_cwd_teardown)
    os.chdir(MYCWD)


@pytest.yield_fixture
def os_environ():
    """Backups env var from os.environ and restores it at teardown. """

    from kcli import conf

    backup_flag = False
    if conf.ENV_VAR_NAME in os.environ:
        backup_flag = True
        backup_value = os.environ.get(conf.ENV_VAR_NAME)
    yield os.environ
    if backup_flag:
        os.environ[conf.ENV_VAR_NAME] = backup_value


def test_get_config_dir(our_cwd_setup):
    from kcli import conf
    conf_file = conf.load_config_file()
    assert os.path.abspath(conf_file.get("DEFAULTS", "KHALEESI_DIR")) == \
        os.path.abspath(MYCWD)

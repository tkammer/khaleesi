import os
import pytest

from tests.test_cwd import consts as test_const

MYCWD = test_const.TESTS_CWD


@pytest.fixture()
def our_cwd_setup(request):
    bkp = os.getcwd()
    def our_cwd_teardown():
        os.chdir(bkp)
    request.addfinalizer(our_cwd_teardown)
    os.chdir(MYCWD)



@pytest.yield_fixture
def os_environ():
    from kcli import conf
    """Backups env var from os.environ and restores it at teardown. """
    backup_flag = False
    if conf.ENV_VAR_NAME in os.environ:
        backup_flag = True
        backup_value = os.environ.get(conf.ENV_VAR_NAME)
    yield os.environ
    if backup_flag:
        os.environ[conf.ENV_VAR_NAME] = backup_value


def test_get_config_dir(our_cwd_setup):
    from kcli import conf
    file = conf.load_config_file()
    assert os.path.abspath(file.get("DEFAULTS", "KHALEESI_DIR")) == \
           os.path.abspath(MYCWD)

    # # Negative - Missing input
    # with pytest.raises(ValueError) as exc:
    #     core.get_config_dir(fake_config_cli(config_dir=None))
    # assert "Missing path" in str(exc.value)
    #
    # # Negative - Bad path
    # with pytest.raises(ValueError) as exc:
    #     core.get_config_dir(fake_config_cli(config_dir="/fake/path"))
    # assert "Bad path" in str(exc.value)
    # assert "/fake/path" in str(exc.value)
    #
    # # verify CLI
    # assert core.get_config_dir(
    #     fake_config_cli(config_dir=SETTINGS_DIR)) == SETTINGS_DIR

    # Verify ENV

    # # Verify CLI over ENV
    # os.environ["KHALEESI_SETTINGS"] = "/fake/env/path"
    # assert core.get_config_dir(
    #     fake_config_cli(config_dir=SETTINGS_DIR)) == SETTINGS_DIR

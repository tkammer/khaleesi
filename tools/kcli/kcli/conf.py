import ConfigParser
import os
import sys

ENV_VAR_NAME = "KCLI_CONFIG"
KCLI_CONF_FILE = 'kcli.cfg'
CWD_PATH = os.path.join(os.getcwd(), KCLI_CONF_FILE)
USER_PATH = os.path.expanduser('~/.' + KCLI_CONF_FILE)
SYSTEM_PATH =os.path.join('/etc/khaleesi', KCLI_CONF_FILE)


def load_config_file():
    """Load config file order(ENV, CWD, USER HOME, SYSTEM).

    :return ConfigParser: config object
    """
    _config = ConfigParser.ConfigParser(allow_no_value=True)
    env_path = os.getenv(ENV_VAR_NAME, None)
    if env_path is not None:
        env_path = os.path.expanduser(env_path)
        if os.path.isdir(env_path):
            env_path = os.path.join(env_path, KCLI_CONF_FILE)
    for path in (env_path, CWD_PATH, USER_PATH, SYSTEM_PATH):
        if path is not None and os.path.exists(path):
            _config.read(path)
            return _config
    # TODO(yfried): replace 'exit' with a proper exception
    # raise ConfigParser.Error("kcli conf file %s not found" % KCLI_CONF_FILE)
    print "ERROR: kcli conf file (%s) not found" % KCLI_CONF_FILE
    sys.exit(1)

config = load_config_file()






for dir_path in config.options('DEFAULTS'):
    globals()[dir_path.upper()] = config.get('DEFAULTS', dir_path)


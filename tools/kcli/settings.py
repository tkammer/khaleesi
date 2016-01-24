import ConfigParser
import sys

# KCLI_CONF_FILE = '/etc/khaleesi/kcli.cfg'
KCLI_CONF_FILE = 'kcli.cfg'

# config = ConfigParser.RawConfigParser(allow_no_value=True)
config = ConfigParser.ConfigParser(allow_no_value=True)
try:
    with open(KCLI_CONF_FILE) as conf:
        config.readfp(conf)
except IOError:
    print "ERROR: kcli conf file (%s) not found" % KCLI_CONF_FILE
    sys.exit(1)

for dir_path in config.options('DEFAULTS'):
    globals()[dir_path.upper()] = config.get('DEFAULTS', dir_path)


class IRException(Exception):
    def __init__(self, msg):
        self.msg = msg


class IRKeyNotFoundException(IRException):
    def __init__(self, key, dic):
        super(self.__class__, self).__init__(
            "Key \"%s\" not found in %s" % (key, dic))


class IRFileNotFoundException(IRException):
    def __init__(self, file_path, msg=None):
        pre_msg = msg if msg else "No such file or directory: "
        super(self.__class__, self).__init__(pre_msg + file_path)


class IRExtraVarsException(IRException):
    def __init__(self, extra_var):
        super(self.__class__, self).__init__(
            "\"%s\" - extra-var argument must be a path to a setting file or "
            "in 'key=value' form" % extra_var)


class IRMissingAncestorException(IRException):
    def __init__(self, key):
        super(self.__class__, self).__init__(
            "Please provide all ancestors of \"--%s\"" % key.replace("_", "-"))


class IRMissingEnvironmentVariableExcption(IRException):
    def __init__(self, env_var):
        super(self.__class__, self).__init__(
            "Environment variable \"%s\" isn't defined" % env_var)


class IRPlaybookFailedException(IRException):
    def __init__(self, playbook):
        super(self.__class__, self).__init__("Playbook %s failed!" % playbook)

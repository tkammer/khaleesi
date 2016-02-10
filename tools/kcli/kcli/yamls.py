import re
import string

import configure
import yaml

import kcli.utils
from kcli import exceptions
from kcli import logger

LOG = logger.LOG

# Representer for Configuration object
yaml.SafeDumper.add_representer(
    configure.Configuration,
    lambda dumper, value:
    yaml.representer.BaseRepresenter.represent_mapping
    (dumper, u'tag:yaml.org,2002:map', value))


def random_generator(size=32, chars=string.ascii_lowercase + string.digits):
    import random

    return ''.join(random.choice(chars) for _ in range(size))


@configure.Configuration.add_constructor('join')
def _join_constructor(loader, node):
    seq = loader.construct_sequence(node)
    return ''.join([str(i) for i in seq])


@configure.Configuration.add_constructor('random')
def _random_constructor(loader, node):
    """
    usage:
        !random <length>
    returns a random string of <length> characters
    """

    num_chars = loader.construct_scalar(node)
    return random_generator(int(num_chars))


def _limit_chars(_string, length):
    length = int(length)
    if length < 0:
        raise exceptions.IRException('length to crop should be int, not ' +
                                     str(length))

    return _string[:length]


@configure.Configuration.add_constructor('limit_chars')
def _limit_chars_constructor(loader, node):
    """
    Usage:
        !limit_chars [<string>, <length>]
    Method returns first param cropped to <length> chars.
    """

    params = loader.construct_sequence(node)
    if len(params) != 2:
        raise exceptions.IRException(
            'limit_chars requires two params: string length')
    return _limit_chars(params[0], params[1])


@configure.Configuration.add_constructor('env')
def _env_constructor(loader, node):
    """
    usage:
        !env <var-name>
        !env [<var-name>, [default]]
        !env [<var-name>, [default], [length]]
    returns value for the environment var-name
    default may be specified by passing a second parameter in a list
    length is maximum length of output (croped to that length)
    """

    import os
    # scalar node or string has no defaults,
    # raise IRUndefinedEnvironmentVariableExcption if absent
    if isinstance(node, yaml.nodes.ScalarNode):
        try:
            return os.environ[loader.construct_scalar(node)]
        except KeyError:
            raise exceptions.IRUndefinedEnvironmentVariableExcption(node.value)

    seq = loader.construct_sequence(node)
    var = seq[0]
    if len(seq) >= 2:
        ret = os.getenv(var, seq[1])  # second item is default val

        # third item is max. length
        if len(seq) == 3:
            ret = _limit_chars(ret, seq[2])
        return ret

    return os.environ[var]


class Lookup(yaml.YAMLObject):
    yaml_tag = u'!lookup'
    yaml_dumper = yaml.SafeDumper

    settings = None

    def __init__(self, key, old_style_lookup=False):
        self.key = key
        if old_style_lookup:
            self.convert_old_style_lookup()

    def __repr__(self):
        return "%s(%s)" % (self.__class__.__name__, self.key)

    def convert_old_style_lookup(self):
        self.key = '{{!lookup %s}}' % self.key

        parser = re.compile('\[\s*\!lookup\s*[\w.]*\s*\]')
        lookups = parser.findall(self.key)

        for lookup in lookups:
            self.key = self.key.replace(lookup, '.{{%s}}' % lookup[1:-1])

    def replace_lookup(self):
        """
        Replace any !lookup with the corresponding value from settings table
        """
        while True:
            parser = re.compile('\{\{\s*\!lookup\s*[\w.]*\s*\}\}')
            lookups = parser.findall(self.key)

            if not lookups:
                break

            for a_lookup in lookups:
                lookup_key = re.search('(\w+\.?)+ *?\}\}', a_lookup)
                lookup_key = lookup_key.group(0).strip()[:-2].strip()
                lookup_value = kcli.utils.dict_lookup(
                    self.settings, *lookup_key.split("."))

                if isinstance(lookup_value, Lookup):
                    return

                lookup_value = str(lookup_value)

                self.key = re.sub('\{\{\s*\!lookup\s*[\w.]*\s*\}\}',
                                  lookup_value, self.key, count=1)

    @classmethod
    def from_yaml(cls, loader, node):
        return Lookup(loader.construct_scalar(node), old_style_lookup=True)

    @classmethod
    def to_yaml(cls, dumper, node):
        if node.settings:
            node.replace_lookup()

        return dumper.represent_data("%s" % node.key)

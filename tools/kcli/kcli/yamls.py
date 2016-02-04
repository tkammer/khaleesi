import logging
import yaml
import sys

from string import ascii_lowercase, digits
from configure import Configuration

logger = logging.getLogger('logger')


def random_generator(size=32, chars=ascii_lowercase + digits):
    import random

    return ''.join(random.choice(chars) for _ in range(size))


@Configuration.add_constructor('join')
def _join_constructor(loader, node):
    seq = loader.construct_sequence(node)
    return ''.join([str(i) for i in seq])


@Configuration.add_constructor('random')
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
        raise AttributeError(
            'length to crop should be int, not ' + str(length))

    return _string[:length]


@Configuration.add_constructor('limit_chars')
def _limit_chars_constructor(loader, node):
    """
    Usage:
        !limit_chars [<string>, <length>]
    Method returns first param cropped to <length> chars.
    """
    params = loader.construct_sequence(node)
    if len(params) != 2:
        raise AttributeError('limit_chars requires two params: string length')
    return _limit_chars(params[0], params[1])


@Configuration.add_constructor('env')
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
    # scalar node or string has no defaults, raise KeyError
    # if absent
    if isinstance(node, yaml.nodes.ScalarNode):
        try:
            return os.environ[loader.construct_scalar(node)]
        except KeyError:
            import main

            logger.error("No environment variable named \"%s\" and default"
                         "isn't defined" % node.value)
            sys.exit(1)

    seq = loader.construct_sequence(node)
    var = seq[0]
    if len(seq) >= 2:
        ret = os.getenv(var, seq[1])  # second item is default val

        # third item is max. length
        if len(seq) == 3:
            ret = _limit_chars(ret, seq[2])
        return ret

    return os.environ[var]

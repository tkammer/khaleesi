"""
This module provide some general helper methods
"""

import os
import logging
import re
import sys

import configure
import yaml

import kcli.yamls
import kcli.conf
from kcli import exceptions
from kcli import logger

LOG = logger.LOG


# TODO: check if can be moved into Lookup
def dict_lookup(dic, key, *keys):
    """lookup and return value of a nested key from a given dictionary

    to get the value of a nested key, all ancestor keys should be given as
    method's arguments

    example:
      dict_lookup({'key1': {'key2': 'val'}}, 'key1.key2'.split('.'))

    :param dic: dictionary object to get the key's value from
    :param key: key / first key in a keys' chain
    :param keys: sub keys in a keys' chain
    :return: value of a gives keys
    """
    if LOG.getEffectiveLevel() <= logging.DEBUG:
        calling_method_name = sys._getframe().f_back.f_code.co_name
        current_method_name = sys._getframe().f_code.co_name
        if current_method_name != calling_method_name:
            full_key = list(keys)
            full_key.insert(0, key)
            LOG.debug("looking up the value of \"%s\"" % ".".join(full_key))

    if key not in dic:
        if isinstance(key, str) and key.isdigit():
            key = int(key)
        elif isinstance(key, int):
            key = str(key)

    if keys:
        return dict_lookup(dic.get(key, {}), *keys)

    try:
        value = dic[key]
    except KeyError:
        raise exceptions.IRKeyNotFoundException(key, dic)

    LOG.debug("value has been found: \"%s\"" % value)
    return value


def dict_insert(dic, val, key, *keys):
    """insert a value of a nested key into a dictionary

    to insert value for a nested key, all ancestor keys should be given as
    method's arguments

    example:
      dict_lookup({}, 'val', 'key1.key2'.split('.'))

    :param dic: a dictionary object to insert the nested key value into
    :param val: a value to insert to the given dictionary
    :param key: first key in a chain of key that will store the value
    :param keys: sub keys in the keys chain
    """
    if not keys:
        dic[key] = val
        return

    dict_insert(dic.setdefault(key, {}), val, *keys)


# TODO: remove "settings" references in project
def validate_settings_dir(settings_dir=None):
    """Checks & returns the full path to the settings dir.

    Path is set in the following priority:
    1. Method argument
    2. System environment variable

    :param settings_dir: path given as argument by a user
    :return: path to settings dir (str)
    :raise: IRFileNotFoundException: when the path to the settings dir doesn't
            exist
    """
    settings_dir = settings_dir or os.environ.get(
        kcli.conf.KHALEESI_DIR_ENV_VAR)

    if not os.path.exists(settings_dir):
        raise exceptions.IRFileNotFoundException(
            settings_dir,
            "Settings dir doesn't exist: ")

    return settings_dir


def update_settings(settings, file_path):
    """merge settings in 'file_path' with 'settings'

    :param settings: settings to be merge with (configure.Configuration)
    :param file_path: path to file with settings to be merged
    :return: merged settings
    """
    LOG.debug("Loading setting file: %s" % file_path)
    if not os.path.exists(file_path):
        raise exceptions.IRFileNotFoundException(file_path)

    loaded_file = configure.Configuration.from_file(file_path).configure()
    settings = settings.merge(loaded_file)

    return settings


def generate_settings(settings_files, extra_vars):
    """Generate one settings object (configure.Configuration) by merging all
    files in settings file & extra-vars

    files in 'settings_files' are the first to be merged and after them the
    'extra_vars'

    :param settings_files: list of paths to settings files
    :param extra_vars: list of extra-vars
    :return: Configuration object with merging results of all settings
    files and extra-vars
    """
    settings = configure.Configuration.from_dict({})

    for settings_file in settings_files:
        settings = update_settings(settings, settings_file)

    for extra_var in extra_vars:
        if extra_var.startswith('@'):
            settings_file = normalize_file(extra_var[1:])
            settings = update_settings(settings, settings_file)

        else:
            if '=' not in extra_var:
                raise exceptions.IRExtraVarsException(extra_var)
            key, value = extra_var.split("=")
            dict_insert(settings, value, *key.split("."))

    # Dump & load again settings, because 'in_string_lookup' can't work with
    # 'Configuration' object.
    dumped_settings = yaml.safe_dump(settings, default_flow_style=False)
    settings = yaml.safe_load(dumped_settings)

    return settings


def in_string_lookup(settings):
    """convert strings contain the '!lookup' tag in them and don't
    already converted into Lookup objects.
    (in case of strings that contain and don't start with '!lookup')

    :param settings: a settings dictionary to search and convert lookup from
    """
    if kcli.yamls.Lookup.settings is None:
        kcli.yamls.Lookup.settings = settings

    my_iter = settings.iteritems() if isinstance(settings, dict) \
        else enumerate(settings)

    for idx_key, value in my_iter:
        if isinstance(value, dict):
            in_string_lookup(settings[idx_key])
        elif isinstance(value, list):
            in_string_lookup(value)
        elif isinstance(value, str):
            parser = re.compile('\{\{\s*\!lookup\s*[\w.]*\s*\}\}')
            lookups = parser.findall(value)

            if lookups:
                settings[idx_key] = kcli.yamls.Lookup(value)


# todo: convert into a file object to be consumed by argparse
def normalize_file(file_path):
    """Return a normalized absolutized version of a file

    :param file_path: path to file to be normalized
    :return: normalized path of a file
    :raise: IRFileNotFoundException if the file doesn't exist
    """
    if not os.path.isabs(file_path):
        abspath = os.path.abspath(file_path)
        LOG.debug(
            'Setting the absolute path of "%s" to: "%s"'
            % (file_path, abspath)
        )
        file_path = abspath

    if not os.path.exists(file_path):
        raise exceptions.IRFileNotFoundException(file_path)

    return file_path


# todo: move into lookup
def lookup2lookup(settings):
    """handles recursive lookups

    load and dump yaml's dictionary ('settings') until all lookups strings
    are been converted into Lookup objects

    :param settings: settings to convert all lookups from
    :return: an yml dictionary object without lookup strings
    """

    first_dump = True
    while True:
        if not first_dump:
            kcli.yamls.Lookup.settings = settings
            settings = yaml.load(output)

        in_string_lookup(settings)
        output = yaml.safe_dump(settings, default_flow_style=False)

        if first_dump:
            first_dump = False
            continue

        if not cmp(settings, kcli.yamls.Lookup.settings):
            break

    return output

#!/usr/bin/env python

import logging
import os
import re
import sys

import yaml
import configure

from kcli import logger
from kcli import conf
from kcli.exceptions import *
from kcli.execute.execute import PLAYBOOKS
from kcli import parse
# Contains meta-classes so we need to import it without using.
from kcli import yamls

SETTING_FILE_EXT = ".yml"
LOG = logger.LOG
kcli_conf = conf.config

# Representer for Configuration object
yaml.SafeDumper.add_representer(
    configure.Configuration,
    lambda dumper, value:
    yaml.representer.BaseRepresenter.represent_mapping
    (dumper, u'tag:yaml.org,2002:map', value))


def dict_lookup(dic, key, *keys):
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
    if not keys:
        dic[key] = val
        return

    if key not in dic:
        dic[key] = {}

    dict_insert(dic[key], val, *keys)


def validate_settings_dir(settings_dir=None):
    """
    Checks & returns the full path to the settings dir.
    Path is set in the following priority:
    1. Method argument
    2. System environment variable
    3. Settings dir in the current working dir
    :param settings_dir: path given as argument by a user
    :return: path to settings dir (str)
    :raise: IRFileNotFoundException: when the path to the settings dir doesn't
            exist
    """
    settings_dir = settings_dir or os.environ.get(
        'KHALEESI_SETTINGS') or os.path.join(os.getcwd(), "settings", "")

    if not os.path.exists(settings_dir):
        raise exceptions.IRFileNotFoundException(
            settings_dir,
            "Settings dir doesn't exist: ")

    return settings_dir


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
                lookup_value = dict_lookup(
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


class OptionNode(object):
    def __init__(self, path, parent=None):
        self.path = path
        self.option = self.path.split("/")[-1]
        self.parent = parent
        self.parent_value = None
        if parent:
            self.option = "-".join([self.parent.option, self.option])
        self.values = self._get_values()
        self.children = {i: dict() for i in self._get_sub_options()}

        if self.parent:
            self.parent_value = self.path.split("/")[-2]
            self.parent.children[self.parent_value][self.option] = self

    def _get_values(self):
        """
        Returns a sorted list of values available for the current option
        """
        values = [a_file.split(SETTING_FILE_EXT)[0]
                  for a_file in os.listdir(self.path)
                  if os.path.isfile(os.path.join(self.path, a_file)) and
                  a_file.endswith(SETTING_FILE_EXT)]

        values.sort()
        return values

    def _get_sub_options(self):
        """
        Returns a sorted list of sup-options available for the current option
        """
        options = [options_dir for options_dir in os.listdir(self.path)
                   if os.path.isdir(os.path.join(self.path, options_dir)) and
                   options_dir in self.values]

        options.sort()
        return options


class OptionsTree(object):
    def __init__(self, settings_dir, option):
        self.root = None
        self.name = option
        self.action = option[:-2] if option.endswith('er') else option
        self.options_dict = {}
        self.root_dir = os.path.join(settings_dir, self.name)

        self.build_tree()
        self.init_options_dict(self.root)

    def build_tree(self):
        """
        Builds the OptionsTree
        """
        self.add_node(self.root_dir, None)

    def add_node(self, path, parent):
        """
        Adds OptionNode object to the tree
        :param path: Path to option dir
        :param parent: Parent option (OptionNode)
        """
        node = OptionNode(path, parent)

        if not self.root:
            self.root = node

        for child in node.children:
            sub_options_dir = os.path.join(node.path, child)
            sub_options = [a_dir for a_dir in os.listdir(sub_options_dir) if
                           os.path.isdir(os.path.join(sub_options_dir, a_dir))]

            for sub_option in sub_options:
                self.add_node(os.path.join(sub_options_dir, sub_option), node)

    def init_options_dict(self, node):
        """
        Initialize "options_dict" dictionary to store all options and their
        valid values
        :param node: OptionNode object
        """
        if node.option not in self.options_dict:
            self.options_dict[node.option] = {}

        if node.parent_value:
            self.options_dict[node.option][node.parent_value] = node.values

        if 'ALL' not in self.options_dict[node.option]:
            self.options_dict[node.option]['ALL'] = set()

        self.options_dict[node.option]['ALL'].update(node.values)

        for pre_value in node.children:
            for child in node.children[pre_value].values():
                self.init_options_dict(child)

    def get_options_ymls(self, options):
        ymls = []
        if not options:
            return ymls

        keys = options.keys()
        keys.sort()

        def step_in(key, node):
            keys.remove(key)
            if node.option != key.replace("_", "-"):
                raise exceptions.IRMissingAncestorException(key)

            ymls.append(os.path.join(node.path, options[key] + ".yml"))
            child_keys = [child_key for child_key in keys
                          if child_key.startswith(key) and
                          len(child_key.split("_")) == len(key.split("_")) + 1
                          ]

            for child_key in child_keys:
                step_in(child_key, node.children[options[key]][
                    child_key.replace("_", "-")])

        step_in(keys[0], self.root)
        LOG.debug("%s tree settings files:\n%s" % (self.name, ymls))

        return ymls

    def __str__(self):
        return yaml.safe_dump(self.options_dict, default_flow_style=False)


def merge_settings(settings, file_path):
    LOG.debug("Loading setting file: %s" % file_path)
    if not os.path.exists(file_path):
        raise exceptions.IRFileNotFoundException(file_path)

    loaded_file = configure.Configuration.from_file(file_path).configure()
    settings = settings.merge(loaded_file)

    return settings


def generate_settings_file(settings_files, extra_vars):
    settings = configure.Configuration.from_dict({})

    for settings_file in settings_files:
        settings = merge_settings(settings, settings_file)

    for extra_var in extra_vars:
        if extra_var.startswith('@'):
            settings_file = normalize_file(extra_var[1:])
            settings = merge_settings(settings, settings_file)

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
    """
    Convert strings contain the '!lookup' tag in them and don't
    already converted into Lookup objects.
    """
    if Lookup.settings is None:
        Lookup.settings = settings

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
                settings[idx_key] = Lookup(value)


def normalize_file(file_path):
    """
    Return a normalized absolutized version of a file
    """
    if not os.path.isabs(file_path):
        abspath = os.path.abspath(file_path)
        LOG.debug(
            "Setting the absolute path of \"%s\" to: \"%s\""
            % (file_path, abspath)
        )
        file_path = abspath

    if not os.path.exists(file_path):
        raise exceptions.IRFileNotFoundException(file_path)

    return file_path


def lookup2lookup(settings):
    first_dump = True
    while True:
        if not first_dump:
            Lookup.settings = settings
            settings = yaml.load(output)

        in_string_lookup(settings)
        output = yaml.safe_dump(settings, default_flow_style=False)

        if first_dump:
            first_dump = False
            continue

        if not cmp(settings, Lookup.settings):
            break

    return output


def main():
    options_trees = []
    settings_files = []
    settings_dir = validate_settings_dir(kcli_conf.get('DEFAULTS',
                                                       'SETTINGS_DIR'))

    for option in kcli_conf.options('ROOT_OPTS'):
        options_trees.append(OptionsTree(settings_dir, option))

    parser = parse.create_parser(options_trees)
    args = parser.parse_args()

    verbose = int(args.verbose)

    if args.verbose == 0:
        args.verbose = logging.WARNING
    elif args.verbose == 1:
        args.verbose = logging.INFO
    else:
        args.verbose = logging.DEBUG

    LOG.setLevel(args.verbose)

    # settings generation stage
    if args.which.lower() != 'execute':
        for input_file in args.input:
            settings_files.append(normalize_file(input_file))

        for options_tree in options_trees:
            options = {key: value for key, value in vars(args).iteritems()
                       if value and key.startswith(options_tree.name)}

            settings_files += (options_tree.get_options_ymls(options))

        LOG.debug("All settings files to be loaded:\n%s" % settings_files)

        settings = generate_settings_file(settings_files, args.extra_vars)

        output = lookup2lookup(settings)

        if args.output_file:
            with open(args.output_file, 'w') as output_file:
                output_file.write(output)
        else:
            print output

    exec_playbook = (args.which == 'execute') or \
                    (not args.dry_run and args.which in kcli_conf.options(
                        'AUTO_EXEC_OPTS'))

    # playbook execution stage
    if exec_playbook:
        if args.which == 'execute':
            execute_args = parser.parse_args()
        elif args.which not in PLAYBOOKS:
            LOG.debug("No playbook named \"%s\", nothing to execute.\n"
                      "Please choose from: %s" % (args.which, PLAYBOOKS))
            return
        else:
            args_list = ["execute"]
            if verbose:
                args_list.append('-%s' % ('v' * verbose))
            if 'inventory' in args:
                inventory = args.inventory
            else:
                inventory = 'local_hosts' if args.which == 'provision' \
                    else 'hosts'
            args_list.append('--inventory=%s' % inventory)
            args_list.append('--' + args.which)
            args_list.append('--collect-logs')
            if args.output_file:
                LOG.debug('Using the newly created settings file: "%s"'
                          % args.output_file)
                args_list.append('--settings=%s' % args.output_file)
            else:
                from time import time

                tmp_settings_file = 'kcli_settings_' + str(time()) + \
                                    SETTING_FILE_EXT
                with open(tmp_settings_file, 'w') as output_file:
                    output_file.write(output)
                LOG.debug('Temporary settings file "%s" has been created for '
                          'execution purpose only.' % tmp_settings_file)
                args_list.append('--settings=%s' % tmp_settings_file)

            execute_args = parser.parse_args(args_list)

        LOG.debug("execute parser args: %s" % args)
        execute_args.func(execute_args)

        if not args.output_file and args.which != 'execute':
            LOG.debug('Temporary settings file "%s" has been deleted.'
                      % tmp_settings_file)
            os.remove(tmp_settings_file)


if __name__ == '__main__':
    main()

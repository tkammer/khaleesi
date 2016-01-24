#!/usr/bin/env python
import argparse
import os
import sys
import conf


assert "playbooks" == os.path.basename(conf.PLAYBOOKS_DIR), \
    "Bad path to playbooks"

VERBOSITY = 0

def file_exists(prs, filename):
    if not os.path.exists(filename):
        prs.error("The file %s does not exist!" % filename)
    return filename


def main():
    args = parser.parse_args()
    args.func(args)


parser = argparse.ArgumentParser()
parser.add_argument('-v', '--verbose', default=VERBOSITY, action="count",
                    help="verbose mode (-vvv for more,"
                         " -vvvv to enable connection debugging)")
parser.add_argument("--settings",
                    default=conf.KCLI_SETTINGS_YML,
                    type=lambda x: file_exists(parser, x),
                    help="settings file to use. default: %s"
                         % conf.KCLI_SETTINGS_YML)
subparsers = parser.add_subparsers(metavar="COMMAND")


if __name__ == '__main__':
    sys.exit(main())

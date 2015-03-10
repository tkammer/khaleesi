#!/usr/bin/python

# (c) 2015, Ariel Opincaru <aopincar@redhat.com>
#
# This module is a wrapper to the beaker-client tool
#
# For installation, configuration and other details please visit:
# https://beaker-project.org/docs/user-guide/bkr-client.html


import sys
from datetime import datetime
from requests.exceptions import HTTPError
from tempfile import NamedTemporaryFile
from xmlrpclib import Fault

import bkr.client.commands
from bkr.client import conf
from bkr.client.main import BeakerCommandContainer, BeakerOptionParser
from bkr.common import __version__

from optparse import IndentedHelpFormatter

# register default command plugins
BeakerCommandContainer.register_module(bkr.client.commands, prefix="cmd_")

PASS = 0
FAIL = 1

LOAN_COMMENT = "Loan granted by Ansible"

command_container = BeakerCommandContainer(conf=conf)
formatter = IndentedHelpFormatter(max_help_position=60, width=120)
parser = BeakerOptionParser(version=__version__, conflict_handler='resolve',
                            command_container=command_container,
                            default_command="help", formatter=formatter)


def run(cmd_list):
    """
    this function redirect the stdout & stderr and run the given command
    :param cmd_list: command to executes in a list
    :return: tuple - stdout, stderr (as strings)
    """
    # redirect output & error to temporary files
    sys.stdout = stdout = NamedTemporaryFile(mode='r+')
    sys.stderr = stderr = NamedTemporaryFile(mode='r+')

    cmd, cmd_opts, cmd_args = parser.parse_args(args=cmd_list)

    try:
        cmd.run(*cmd_args, **cmd_opts.__dict__)
    finally:
        # restore redirection
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__

    stdout.seek(0)
    stderr.seek(0)

    return stdout.read(), stderr.read()


def list_free_systems(groups=None):
    """
    This function search for free systems in a given group names.
    (search in all groups if a group name hasn't given)
    :param parser: a parser object (BeakerOptionParser)
    :param groups: list of group names
    :return: a sorted list of free systems
    """
    out = err = str()
    cmd_list = list()
    base_cmd = 'list-systems --free'

    if groups:
        for group in groups:
            cmd_list.append(base_cmd + ' --group=' + group)
    else:
        cmd_list.append(base_cmd)

    for cmd in cmd_list:
        try:
            tmp_out, tmp_err = run(cmd.split())

        # if a group has no free system, SystemExit exception is thrown
        except SystemExit:
            continue

        out += tmp_out
        err += tmp_err

    return sorted(out.split())


def list_my_systems():
    """
    list owned systems
    :param parser: a parser object (BeakerOptionParser)
    :return: a sorted list of owned systems
    """
    cmd_list = ['list-systems', '--mine']

    try:
        out, err = run(cmd_list)

    # if user hasn't owned any system, SystemExit exception is thrown
    except SystemExit:
        pass

    return sorted(out.split())


def reserve_a_system(fqdn):
    """
    the function reserves the given system
    :param parser: a parser object (BeakerOptionParser)
    :param fqdn: a fully qualified domain name (str)
    :return: 0/1 - Success/Fail
    """
    reserve_cmd = ['system-reserve', fqdn]

    try:
        run(reserve_cmd)
    except Exception:
        #  TODO: check what exception is thrown if can't reserves a system
        raise

    return PASS


def release_a_system(fqdn):
    """
    the function releases the given system
    :param parser: a parser object (BeakerOptionParser)
    :param fqdn: a fully qualified domain name (str)
    :return: 0/1 - Success/Fail
    """
    release_cmd = ['system-release', fqdn]

    try:
        run(release_cmd)

    # xmlrpclib.Fault exception is thrown when fail to release a system
    except Fault:
        return FAIL

    return PASS


def reserve_systems(free_systems, amount):
    """
    the function reserves "amount" number of systems from the given free
    systems list
    :param parser: a parser object (BeakerOptionParser)
    :param free_systems: list of free systems
    :param amount: number of systems to reserve
    :return: list of reserved systems
    """
    reserved_systems = list()

    if len(free_systems) < amount:
        # There aren't enough free systems to reserve
        return reserved_systems

    for free_system in free_systems:

        if not (loan_a_system(free_system) or reserve_a_system(free_system)):
            reserved_systems.append(free_system)

        if len(reserved_systems) == amount:
            return reserved_systems

    # Not enough systems have reserved, releasing all reserved systems.
    release_systems(reserved_systems)

    return reserved_systems


def release_systems(reserved_systems):
    """
    the function releases the given reserved systems
    :param parser: a parser object (BeakerOptionParser)
    :param reserved_systems: list of reserved systems
    :return: list of systems which haven't successfully released
    """
    failed_to_release = list()

    for reserved_system in reserved_systems:

        if return_a_system(reserved_system)\
                or release_a_system(reserved_system):

            failed_to_release.append(reserved_system)

    return failed_to_release


def loan_a_system(fqdn):
    """
    the function loans the given system
    :param parser: a parser object (BeakerOptionParser)
    :param fqdn: a fully qualified domain name (str)
    :return: 0/1 - Success/Fail
    """
    comment_msg = LOAN_COMMENT + " " + str(datetime.now())
    loan_cmd = ['loan-grant', '--comment=' + comment_msg, fqdn]

    try:
        out, err = run(loan_cmd)
    except Exception:
        #  TODO: check what exception is thrown if fails to loan a system
        raise

    return FAIL if err else PASS


def return_a_system(fqdn):
    """
    return a loaned system
    :param parser: a parser object (BeakerOptionParser)
    :param fqdn: a fully qualified domain name (str)
    :return: 0/1 - Success/Fail
    """
    return_cmd = ['loan-return', fqdn]

    try:
        out, err = run(return_cmd)

    # HTTPError exception is thrown when loan return fails
    except HTTPError:
        return FAIL

    return FAIL if err else PASS

#!/usr/bin/python

# (c) 2015, Ariel Opincaru <aopincar@redhat.com>
#
# This module is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This software is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this software.  If not, see <http://www.gnu.org/licenses/>.
#
# This module is a wrapper to the beaker-client tool
#
# For installation, configuration and other details please visit:
# https://beaker-project.org/docs/user-guide/bkr-client.html


import sys
from datetime import datetime
from optparse import IndentedHelpFormatter
from requests.exceptions import HTTPError
from tempfile import NamedTemporaryFile
from xmlrpclib import Fault

from ansible.module_utils.basic import *

import bkr.client.commands
from bkr.client import conf
from bkr.client.main import BeakerCommandContainer, BeakerOptionParser
from bkr.common.bexceptions import BeakerException
from bkr.common import __version__


DOCUMENTATION = '''
---
module: beaker
short_description: Ansible's module for Beaker
description:
    - The purpose of this module is to add the ability
      to reserve/release Beaker's systems.
version_added: "1.0"
author: Ariel Opincaru
notes:
requirements:
    - Beaker server configured and running
    - beaker-client package installed
options:
    action:
        description:
            - The action to perform
        required: true
        choices: ['reserve', 'release']
        version_added: 1.0
    amount:
        description:
            - Amount of systems to reserve
            - Goes with the 'action' option
        required: false
        default: 1
        version_added: 1.0
    groups:
        description:
            - Group(s) to search for free systems
            - Goes with 'reserve' action
            - Comma separated values if more than one value has been given
        required: false
        default: 'all'
        version_added: 1.0
    systems:
        description:
            - Systems to release (fqdn)
            - Goes with 'release' action
            - if option not provided, will release all us
            - Comma separated values if more than one value has been given
        required: false
        version_added: 1.0
'''


EXAMPLES = '''
# Reserve 1 free system from the rhosqe group
beaker: action=reserve groups=rhosqe amount=1

# Release 2 reserved systems
beaker: action=release systems=machine1.lab.redhat.com,machine2.lab.redhat.com

# Release all systems of the current user
beaker: action=release
'''


# register default command plugins
BeakerCommandContainer.register_module(bkr.client.commands, prefix="cmd_")

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
    is_failure = False
    reserve_cmd = ['system-reserve', fqdn]

    try:
        run(reserve_cmd)
    except Exception:
        #  TODO: check what exception is thrown if can't reserves a system
        raise

    return is_failure


def release_a_system(fqdn):
    """
    the function releases the given system
    :param parser: a parser object (BeakerOptionParser)
    :param fqdn: a fully qualified domain name (str)
    :return: 0/1 - Success/Fail
    """
    is_failure = False
    release_cmd = ['system-release', fqdn]

    try:
        run(release_cmd)

    # xmlrpclib.Fault exception is thrown when fail to release a system
    except Fault:
        is_failure = True

    return is_failure


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
    is_failure = False
    comment_msg = LOAN_COMMENT + " " + str(datetime.now())
    loan_cmd = ['loan-grant', '--comment=' + comment_msg, fqdn]

    try:
        out, err = run(loan_cmd)
        if err:
            is_failure = True
    except Exception:
        #  TODO: check what exception is thrown if fails to loan a system
        raise

    return is_failure


def return_a_system(fqdn):
    """
    return a loaned system
    :param parser: a parser object (BeakerOptionParser)
    :param fqdn: a fully qualified domain name (str)
    :return: 0/1 - Success/Fail
    """
    is_failure = False
    return_cmd = ['loan-return', fqdn]

    try:
        out, err = run(return_cmd)
        if err:
            is_failure = True

    # HTTPError exception is thrown when loan return fails
    except HTTPError:
        is_failure = True

    return is_failure


def main():
    module = AnsibleModule(
        argument_spec=dict(
            action=dict(required=True, type='str',
                        choices=['reserve', 'release']),
            amount=dict(required=False, type='int', default=1),
            groups=dict(required=False, type='list'),
            systems=dict(required=False, type='list', default=[])
        ),
        supports_check_mode=False
    )

    free_systems = None
    reserved_systems = None
    released_systems = None
    action = module.params['action']

    try:
        if action == 'reserve':
            amount = module.params['amount']
            groups = module.params['groups']
            cmds_list = list()
            cmd_list = 'list-systems --free'

            if groups:
                for a_group in groups:
                    cmds_list.append(cmd_list + ' --group=' + a_group)
            else:
                cmds_list.append(cmd_list)

            free_systems = list_free_systems(groups)
            if not free_systems:
                raise BeakerException("There aren't enough free systems")

            reserved_systems = reserve_systems(free_systems, amount)
            if not reserved_systems:
                raise BeakerException("Systems reservation has failed")

            # remove reserved system from free systems
            for reserved_system in reserved_systems:
                free_systems.remove(reserved_system)

        elif action == 'release':
            systems = module.params['systems']
            # releases all user's reserved systems
            if not systems:
                systems = list_my_systems()

            failed_to_release = release_systems(systems)

            released_systems = list()
            for system in systems:
                if system not in failed_to_release:
                    released_systems.append(system)

            if failed_to_release:
                raise BeakerException("Failed to release to following "
                                      "systems: %s"
                                      % ' '.join(failed_to_release))

    except (BeakerException, RuntimeError) as e:
        module.fail_json(msg=e.message)

    module.exit_json(changed=len(reserved_systems or released_systems) != 0,
                     free_systems=free_systems or None,
                     reserved_systems=reserved_systems or None,
                     released_systems=released_systems or None)


if __name__ == '__main__':
    main()

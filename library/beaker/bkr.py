#!/usr/bin/python

# (c) 2015, Ariel Opincaru <aopincar@redhat.com>
#
# This module is a wrapper to the beaker-client tool
#
# For installation, configuration and other details please visit:
# https://beaker-project.org/docs/user-guide/bkr-client.html


from datetime import datetime
from subprocess import Popen, PIPE


def execute_get_output(cmd_list):
    p = Popen(cmd_list, stdout=PIPE)
    stdout, stderr = p.communicate()
    if p.returncode or stderr:
        raise RuntimeError("Failed to execute: '%s'\n" % " ".join(cmd_list))
    return stdout

PASS = 0
FAIL = 1

BEAKER_CLIENT = 'bkr'
BEAKER_EXE = execute_get_output(['which', BEAKER_CLIENT]).split()[0]

LOAN_COMMENT = "Loan granted by Ansible's module"


class BeakerException(Exception):
    pass


def list_free_systems(groups):

    free_systems = set()

    for group in groups:
        cmd = [BEAKER_EXE, 'list-systems', '--group=' + group, '--free']
        for system in execute_get_output(cmd).split():
            free_systems.add(system)

    return list(free_systems)


def get_my_systems():

    cmd = [BEAKER_EXE, 'list-systems', '--mine']
    return execute_get_output(cmd).split()


def reserve_a_system(fqdn):
    cmd = [BEAKER_EXE, 'system-reserve', fqdn]
    try:
        execute_get_output(cmd)
    except RuntimeError:
        return FAIL
    return PASS


def release_a_system(fqdn):
    cmd = [BEAKER_EXE, 'system-release', fqdn]
    try:
        execute_get_output(cmd)
    except RuntimeError:
        return FAIL
    return PASS


def reserve_systems(free_systems, amount):
    if len(free_systems) < amount:
        raise BeakerException("There are'nt enough free systems to "
                              "reserve")

    reserved_systems = list()
    for free_system in free_systems:

        if not (loan_a_system(free_system) or reserve_a_system(free_system)):
            reserved_systems.append(free_system)

        if len(reserved_systems) == amount:
            return reserved_systems

    # Not enough systems have reserved, releasing all reserved systems.
    release_systems(reserved_systems)


def release_systems(reserved_systems):
    failed_to_release = list()

    for reserved_system in reserved_systems:

        if return_a_system(reserved_system) or release_a_system(
                reserved_system):
            failed_to_release.append(reserved_system)

    if failed_to_release:
        raise BeakerException("Failed to release the following "
                              "systems: " + " ".join(failed_to_release))


def loan_a_system(fqdn):
    comment_msg = LOAN_COMMENT + " " + str(datetime.now())
    cmd = [BEAKER_EXE, 'loan-grant', '--comment=' + comment_msg, fqdn]
    try:
        execute_get_output(cmd)
    except RuntimeError:
        return FAIL
    return PASS


def return_a_system(fqdn):

    cmd = [BEAKER_EXE, 'loan-return', fqdn]
    try:
        execute_get_output(cmd)
    except RuntimeError:
        return FAIL
    return PASS
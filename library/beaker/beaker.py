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

from ansible.module_utils.basic import *
from ansible.modules.beaker.bkr import *

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

    action = module.params['action']

    try:
        if action == 'reserve':
            amount = module.params['amount']
            groups = module.params['groups']

            free_systems = list_free_systems(groups)
            free_systems.sort()
            reserved_systems = reserve_systems(free_systems, amount)
            module.exit_json(changed=(reserved_systems is not None) and (
                len(reserved_systems) != 0), reserved_systems=reserved_systems)

        elif action == 'release':
            systems = module.params['systems']
            if not systems:  # release all systems
                systems = get_my_systems()

            release_systems(systems)
            module.exit_json(changed=len(systems) != 0)

    except (BeakerException, RuntimeError) as e:
        module.fail_json(msg=e.message)


if __name__ == '__main__':
    main()
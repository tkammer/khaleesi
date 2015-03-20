#!/usr/bin/python
# coding: utf-8 -*-

# (c) 2015, Tal Kammer <tkammer@redhat.com>
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

import requests


DOCUMENTATION = '''
---
module: foreman_provisioner
version_added: "0.1"
short_description: Provision servers via Foreman
description:
   - Provision servers via Foreman
options:
   username:
     description:
         - login username to authenticate to Foreman
     required: true
     default: admin
   password:
     description:
         - Password of login user
     required: true
   auth_url:
     description:
         - The Foreman api url
     required: true
   host_id:
     description:
         - Name or ID of the host as listed in foreman
     required: true
   rebuild:
     description:
         - Should we rebuilt the requested host
     default: true
     required: false
   mgmt_strategy:
     description:
         - Whether to use Foreman or system ipmi command.
     default: 'foreman'
     required: false
   mgmt_action:
     description:
         - Which command to send with the power-management selected by
         mgmt_strategy. For example: reset, reboot, cycle
     default: 'cycle'
     required: false
   wait_for_host:
     description:
         - Whether we should wait for the host given the 'rebuild' state was set.
     default: true
     required: false
'''


MIN_SUPPORTED_VERSION = 2
FOREMAN_MGMT_SUPPORTED_STRATEGIES = ['foreman']
WAIT_TO_FINISH_BUILDING = 10
WAIT_TO_FINISH_BOOTING = 10


class ForemanManager(object):
    """
    This class represents a simple interface for foreman* to easily rebuild /
    get / reserve hosts from foreman.
    *Foreman: http://theforeman.org/
    """
    def __init__(self, url, username, password, extra_headers=None, version=2):
        """
        :param url: the url of the foreman we wish to authenticate with
        :param username: the username we will use to login
        :param password: the password we will use to login
        :param extra_headers: if we require extra headers to be added to the
        http request
        :param version: the version of foreman API we wish to use (default: 2)
        :type version: int
        """
        if version < MIN_SUPPORTED_VERSION:
            raise Exception("API version: {0} "
                            "is not supported at the moment".format(version))

        self.session = requests.Session()
        self.session.auth = (username, password)

        headers = {'Accept': 'application/json',
                   'Content-type': 'application/json'}

        if extra_headers:
            headers.update(extra_headers)

        self.session.headers.update(headers)

        self.url = url.rstrip('/')
        self.default_uri = '/api/v2/hosts/'

    def reserve_host(self, host_id):
        """
        This method 'tags' a host as reserved in foreman
        :param host_id: the name of ID of the host we wish to reserve
        :returns: the host information on success, else empty body
        :rtype: list of dictionaries -- [{"host": {}}]
        """
        #TODO(tkammer): add the option to provide the query itself after "?"
        request_url = '{0}/api/hosts_reserve' \
                      '?query=name ~ {1}'.format(self.url, host_id)
        response = self.session.get(request_url, verify=False)
        body = response.json()
        return body

    def release_host(self, host_id):
        """
        This method removed the 'tag' made by 'reserve_host" in foreman
        :param host_id: the name or ID of the host we wish to release
        :returns: the host name
        :rtype: list of strings
        """
        request_url = '{0}/api/hosts_release' \
                      '?query=name ~ {1}'.format(self.url, host_id)
        response = self.session.get(request_url, verify=False)
        body = response.json()
        Exception(body)
        return body

    def get_host(self, host_id):
        """
        This method returns the host details as listed in the foreman
        :param host_id: the name or ID of the host we wish to get
        :returns: host information
        :rtype: dict
        """
        request_url = '{0}/{1}/{2}'.format(self.url, self.default_uri, host_id)
        response = self.session.get(request_url, verify=False)
        body = response.json()
        return body

    def update_host(self, host_id, update_info):
        """
        This method updates a host details in foreman
        :param host_id: the name or ID of the host we wish to update
        :param update_info: params we wish to update on foreman
        :type update_info: dict
        :returns: host information
        :rtype: dict
        """
        request_url = '{0}/{1}/{2}'.format(self.url, self.default_uri, host_id)
        response = self.session.put(request_url, data=update_info, verify=False)
        body = response.json()
        return body.get('host')

    def set_build_on_host(self, host_id, flag):
        """
        sets the 'build' flag of a host to a given :param flag:
        :param host_id: the id or name of the host as it is listed in foreman
        :param flag: a boolean value (true/false) to set the build flag with
        """
        host = self.update_host(host_id, json.dumps({'build': flag}))
        #TODO(tkammer): add verification that the host was updated

    def bmc(self, host_id, command):
        """
        execute a command through the BMC plugin (on/off/restart/shutdown/etc)
        :param host_id: the id or name of the host as it is listed in foreman
        :param command: the command to send through the BMC plugin, supported
        commands: 'status', 'on', 'off', 'cycle', 'reset', 'soft'
        """
        request_url = '{0}/{1}/{2}/power'.format(self.url, self.default_uri, host_id)
        command = json.dumps({'power_action': command})
        response = self.session.put(request_url, data=command, verify=False)
        #TODO(tkammer): add verification that the BMC command was issued

    def provision(self, host_id, mgmt_strategy, mgmt_action,
                  wait_for_host=True):
        """
        This method rebuilds a machine, doing so by running get_host and bmc.
        :param host_id: the name or ID of the host we wish to rebuild
        :param mgmt_strategy: the way we wish to reboot the machine
        (i.e: foreman, ipmi, etc)
        :param mgmt_action: the action we wish to use with the strategy
        (e.g: cycle, reset, etc)
        :param wait_for_host: whether the function will wait until host has
        finished rebuilding before exiting.
        :raises: Exception in case of machine could not be reached after rebuild
        """
        self.set_build_on_host(host_id, True)
        if mgmt_strategy == 'foreman':
            self.bmc(host_id, mgmt_action)
        else:
            raise Exception("{0} is not a supported "
                            "management strategy".format(mgmt_strategy))

        building_host = self.get_host(host_id)
        if wait_for_host:
            while building_host.get('build'):
                time.sleep(WAIT_TO_FINISH_BUILDING)
                building_host = self.get_host(host_id)

            command = "ping -q -c 30 -w 300 {0}".format(building_host.get('ip'))
            return_code = subprocess.call(command.split(" "))

            if return_code > 0:
                raise Exception("Could not reach {0}".format(host_id))


def main():
    module = AnsibleModule(
        argument_spec=dict(
            username=dict(default='admin'),
            password=dict(required=True),
            auth_url=dict(required=True),
            host_id=dict(required=True),
            rebuild=dict(default=True, choices=BOOLEANS),
            mgmt_strategy=dict(default='foreman',
                               choices=FOREMAN_MGMT_SUPPORTED_STRATEGIES),
            mgmt_action=dict(default='cycle', choices=['on', 'off', 'cycle',
                                                       'reset', 'soft']),
            wait_for_host=dict(default=True, choices=BOOLEANS)))

    foreman_client = ForemanManager(url=module.params['auth_url'],
                                    username=module.params['username'],
                                    password=module.params['password'])
    status_changed = False

    if module.boolean(module.params['rebuild']):
        status_changed = True
        foreman_client.provision(module.params['host_id'],
                                 module.params['mgmt_strategy'],
                                 module.params['mgmt_action'],
                                 module.boolean(module.params['wait_for_host']))

    #TODO(tkammer): implement RESERVE and RELEASE
    host = foreman_client.get_host(module.params['host_id'])
    if host.has_key('error'):
        module.fail_json(msg=host['error'])
        
    module.exit_json(changed=status_changed, host=host)


from ansible.module_utils.basic import *
main()

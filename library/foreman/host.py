#!/usr/bin/python

import subprocess
import time

from common import *

POWER_ACTIONS = dict(
    ON=('on', 'start'),
    OFF=('off', 'stop'),
    STATE=('state', 'status'),
    RESET=('soft', 'reboot', 'cycle', 'reset')
)


class Host(object):

    def __init__(self, f_obj, host, build, power):
        self.f_obj = f_obj
        self.host = host
        self.build = build
        self.power = power

        self.host_id = self.get_host_id()

    def _my_ping_waiter(self, count=5):
        while True:
            p = subprocess.Popen(['ping', '-c', str(count), self.host])
            p.wait()
            if not p.returncode:
                break

    def power_host(self, tries_int=20, wait=True):

        if not self.power:
            raise ForemanException("%s - No power action provided" % self.host)

        if not self.build and (self.power in POWER_ACTIONS['RESET']):
            raise ForemanException("%s - No reason to %s the host with "
                                   "\"build\" set to \"%s\"" % self.host,
                                   self.power, str(self.power))

        self.f_obj.hosts.power(self.host_id, self.power)

        if self.build:
            while True:
                time.sleep(tries_int)
                if not self.f_obj.hosts.show(self.host_id)['build']:
                    break

            # wait one more time if another reboot is needed  after the build
            if wait and (self.power in POWER_ACTIONS['RESET']):
                time.sleep(10)
                self._my_ping_waiter()

    def get_id_index(self, fltr, func_name, func_cls=None, s_field='results'):
        func_cls = self.f_obj if not func_cls else getattr(self.f_obj,
                                                           func_cls)
        func = getattr(func_cls, func_name)
        results = [i['id'] for i in func(search=fltr).get(s_field, {})]
        if len(results) != 1:
            err = "%s - %d id(s) was/were found (%s)" % (
                str(self.host),  len(results), str(func))
            raise ForemanException(err)
        return results[0]

    def get_id_show(self, os_id, s_field, name_attr):
        os_show_obj = self.f_obj.operatingsystems.show
        results = [i['id'] for i in os_show_obj(os_id)[s_field] if
                   i['name'] == name_attr]
        if len(results) != 1:
            err = "%s - %d id(s) was/were found (%s)" % (
                str(self.host),  len(results), str(os_show_obj))
            raise ForemanException(err)
        return results[0]

    def get_host_id(self):
        _search = 'name ~"{0}" or ip ~ "{0}"'.format(self.host)
        return self.get_id_index(fltr=_search, func_name='index_hosts')

    def get_host_conf(self):
        return self.f_obj.hosts.show(self.host_id)

    def update_host(self, updates):
        updates['build'] = self.build
        return self.f_obj.update_hosts(self.host_id, updates)

    def is_build_changed(self, pre_conf, post_conf):
        if post_conf['build'] != self.build:
            raise ForemanException("%s - build hasn't changed, was & "
                                   "remains '\%s'\ instead of \'%s\'\n"
                                   % (self.host, str(post_conf['build']),
                                      str(self.build)))
        return pre_conf['build'] != post_conf['build']
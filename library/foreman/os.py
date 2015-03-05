#!/usr/bin/python

# Ansible imports
from ansible.module_utils.basic import *
from ansible.modules.foreman.host import *
from ansible.modules.foreman.common import *

# Foreman import
from foreman.client import Foreman

DOCUMENTATION = '''
---
module: foreman
short_description: Ansible's module for Foreman
description:
    - TODO
version_added: "1.0"
author: Ariel Opincaru
notes:
requirements:
    - TODO
options:
    url:
        description:
            - Foreman server URL
        required: true
        version_added: 1.0
    username:
        description:
            - Username
        required: false
        default: ''
        version_added: 1.0
    password:
        description:
            - Password
        required: false
        default: ''
        version_added: 1.0
    version:
        description:
            - Foreman server version
        required: false
        default: None
        version_added: 1.0
    api_version:
        description:
            - API version
        required: false
        default: None
        version_added: 1.0
    use_cache:
        description:
            - If True, will use local api definitions, if False,
            will try to get them from the remote Foreman instance (it needs
            you to have disabled use_cache in the apipie configuration in your
            foreman instance)
        required: false
        default: True
        version_added: 1.0
    host:
        description:
            - Name/Address of the intended host
        required: true
        version_added: 1.0
    build:
        description:
            - Build the intended host
        required: false
        default: False
        version_added: 1.0
    reboot:
        description:
            - Reboot the intended host
        required: false
        default: False
        version_added: 1.0
    arch:
        description:
            - Architecture
        required: true
        version_added: 1.0
    os_name:
        description:
            - Operating system name
        required: true
        version_added: 1.0
    media:
        description:
            - Media
        required: true
        version_added: 1.0
    ptable:
        description:
            - Partition table
        required: true
        version_added: 1.0
'''

EXAMPLES = '''
# TODO
'''

OS_ATTRIBUTES = dict(
    arch_id='architecture_id',
    os_id='operatingsystem_id',
    media_id='medium_id',
    ptable_id='ptable_id'
)

REBOOT_CMD = 'cycle'


class OS(object):

    def __init__(self, host_obj, arch, os_name, media, ptable):

        self.h_obj = host_obj
        self.arch = arch
        self.os_name = os_name
        self.media = media
        self.ptable = ptable

        # Get IDs
        self.arch_id = self._get_arch_id()
        self.os_id = self._get_os_id()
        self.media_id = self._get_media_id()
        self.ptable_id = self._get_ptable_id()

        self.changed = False
        self.updates = {}
        self.prepare_update()

    def _get_arch_id(self):
        _search = 'name ~ "%s"' % str(self.arch)
        return self.h_obj.get_id_index(fltr=_search, func_name="index",
                                       func_cls="architectures")

    def _get_os_id(self):
        _search = 'name ~ "{0}" or description ~ "{''0}"'.format(self.os_name)
        return str(self.h_obj.get_id_index(fltr=_search, func_name='index',
                                           func_cls="operatingsystems"))

    def _get_media_id(self):
        return self.h_obj.get_id_show(self.os_id, 'media', self.media)

    def _get_ptable_id(self):
        return self.h_obj.get_id_show(self.os_id, 'ptables', self.ptable)

    def prepare_update(self, updates_dict=None):
        if updates_dict is None:
            for cls_attr, foreman_attr in OS_ATTRIBUTES.iteritems():
                self.updates[foreman_attr] = getattr(self, cls_attr)
        else:
            self.updates = updates_dict

    def get_os_conf(self):

        os_conf = {}
        cur_conf = self.h_obj.get_host_conf()

        for val in OS_ATTRIBUTES.values():
            os_conf[val] = cur_conf[val]
        if 'build' not in OS_ATTRIBUTES:
            os_conf['build'] = cur_conf['build']

        return os_conf

    def is_conf_changed(self, pre_conf, post_conf):
        changed = False

        for val in OS_ATTRIBUTES.values():
            if pre_conf[val] != post_conf[val]:
                if post_conf[val] == self.updates[val]:
                    changed = True
                else:
                    raise ForemanOSException("%s - Unexpected value for %s, "
                                             "expected: %s, actual: %s\n" %
                                             (self.h_obj.host, val,
                                              str(self.updates[val]),
                                              post_conf[val]))

        return self.h_obj.is_build_changed(pre_conf, post_conf) or changed

    def set_updates(self):
        if not self.updates:
            raise ForemanOSException("%s - No updates to set" %
                                     self.h_obj.host)
        self.h_obj.update_host(self.updates)

    def apply_updates(self):
        self.h_obj.power_host()


def main():
    module = AnsibleModule(
        argument_spec=dict(

            # Foreman Client Params
            url=dict(required=True, type='str'),
            username=dict(required=False, type='str', default=''),
            password=dict(required=False, default=''),
            version=dict(required=False, type='str', default=None),
            api_version=dict(required=False, type='str', default=None),
            use_cache=dict(required=False, default=True),

            # Host/Action Params
            host=dict(required=True, type='str'),
            build=dict(required=False, type='bool', default=False),
            reboot=dict(required=False, type='bool', default=False),

            # Operating System Params
            arch=dict(required=True, type='str'),
            os_name=dict(required=True, type='str'),
            media=dict(required=True, type='str'),
            ptable=dict(required=True, type='str')

        ),
        supports_check_mode=False
    )

    changed = False

    username = module.params['username']
    password = module.params['password']
    url = module.params['url']
    version = module.params['version']
    api_version = module.params['api_version']
    use_cache = module.params['use_cache']

    auth = (username, password) if username else None
    f_obj = Foreman(url, auth, version, api_version, use_cache)

    host = module.params['host']
    build = module.params['build']
    power = REBOOT_CMD if module.params['reboot'] else ''
    host_obj = Host(f_obj, host, build, power)

    arch = module.params['arch']
    os_name = module.params['os_name']
    media = module.params['media']
    ptable = module.params['ptable']
    f_os_obj = OS(host_obj, arch, os_name, media, ptable)

    try:
        pre_conf = f_os_obj.get_os_conf()
        f_os_obj.set_updates()
        post_conf = f_os_obj.get_os_conf()
        changed = f_os_obj.is_conf_changed(pre_conf, post_conf) or changed
        f_os_obj.apply_updates()

    except ForemanException as e:
        module.fail_json(msg=e.message)

    module.exit_json(changed=changed)

if __name__ == '__main__':
    main()

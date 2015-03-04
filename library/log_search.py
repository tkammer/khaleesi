#!/usr/bin/env python

import re

DOCUMENTATION = '''
---
module: custom_facts
version_added: "1.6"
short_description: Add a set of custom facts based on specific vars
description:
   - Given a specific file, look for a match pattern
'''

EXAMPLES = '''
# Look for errors in the log file
- log_search:
  log_file: /tmp/somelog
  text: Error
'''


def search_for_regex(filename, pattern):
    result = []
    for line_number, line in enumerate(open(filename)):
        for match in re.finditer(pattern, line):
            result.append((line_number+1, line))

    return result


def main():
    module = AnsibleModule(
        argument_spec = dict(
            log_file  = dict(required=True),
            text      = dict(required=True)
        )
    )

    result = None

    filename = module.params['log_file']
    text = module.params['text']

    result = search_for_regex(filename, text)

    if result or len(result) > 0:
        msg = 'Found %s matche(s)' % len(result)
        module.exit_json(msg=msg, result=result)
    else:
        module.fail_json(msg='No matches found')

from ansible.module_utils.basic import *
main()
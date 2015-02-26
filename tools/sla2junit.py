
import json
import sys
from xml.etree import ElementTree

"""
this script converts rally sla from JSON format to JUnit xml file

- BenchmarkScenario1
    - sla1 - PASS/FAIL
    - sla2 - PASS/FAIL
- BenchmarkScenario2
    - sla3 - PASS/FAIL
"""


def json2dict(json_sla):
    with open(json_sla) as js:
        data = json.load(js)

    tests = {}

    for sla in data:
        scenario = sla["benchmark"]
        tests.setdefault(scenario, {"status": True, "tests": {}})
        sla_status = sla["status"]
        tests[scenario]["status"] = (tests[scenario]["status"] and
                                     sla_status.lower() == "passed")
        tests[scenario]["tests"][sla["criterion"]] = dict(
            status=sla_status,
            detail=sla["detail"],
            pos=sla["pos"]
        )
    return tests


def dict2xml(tests):
    testrun = ElementTree.Element("testrun")
    for scenario, sdict in tests.iteritems():
        criteria = sdict["tests"]
        suit_status = "passed" if sdict["status"] else "failed"
        suite = ElementTree.SubElement(testrun, "suite",
                                       attrib=dict(status=suit_status,
                                                   name=scenario))
        for name, sla_results in criteria.iteritems():
            test = ElementTree.SubElement(suite, "test",
                                          attrib=dict(
                                              status=sla_results["status"],
                                              name=name,
                                              pos=str(sla_results["pos"])))
            test.text = sla_results["detail"]

    return testrun


def main():
    tests = json2dict(sys.argv[1])
    xml = ElementTree.ElementTree(dict2xml(tests))
    xml.write(sys.argv[2], encoding="UTF-8", xml_declaration=True)


if __name__ == '__main__':
    sys.exit(main())




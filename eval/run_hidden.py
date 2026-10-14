"""Run a task's hidden unittest file inside a work directory and print per-unit results as JSON.

Usage: python run_hidden.py <workdir>
The harness copies hidden_test.py (and any hidden_* data) into <workdir> first. A unit is one
sub-test, or one test method that has no sub-tests, so a table of 20 cases counts as 20 units.
"""
import json
import os
import sys
import unittest

workdir = os.path.abspath(sys.argv[1])
os.chdir(workdir)
sys.path.insert(0, workdir)


class Result(unittest.TestResult):
    def __init__(self):
        super().__init__()
        self.units = []
        self._has_sub = set()

    def _sub_key(self, test, subtest):
        parent = test.id()
        return parent, f"{parent} {subtest._subDescription()}" if hasattr(subtest, "_subDescription") else str(subtest)

    def addSubTest(self, test, subtest, err):
        super().addSubTest(test, subtest, err)
        parent, name = self._sub_key(test, subtest)
        self._has_sub.add(parent)
        self.units.append({"id": name, "ok": err is None})

    def addSuccess(self, test):
        super().addSuccess(test)
        if test.id() not in self._has_sub:
            self.units.append({"id": test.id(), "ok": True})

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.units.append({"id": test.id() + " (body)" if test.id() in self._has_sub else test.id(), "ok": False})

    def addError(self, test, err):
        super().addError(test, err)
        self.units.append({"id": test.id() + " (body)" if test.id() in self._has_sub else test.id(), "ok": False,
                           "error": str(err[1])[:200]})


def main():
    try:
        suite = unittest.defaultTestLoader.loadTestsFromName("hidden_test")
    except Exception as e:  # import error in the candidate's module
        print(json.dumps({"total": 1, "passed": 0, "units": [{"id": "import", "ok": False, "error": str(e)[:300]}]}))
        return
    res = Result()
    suite.run(res)
    # a module that failed to import shows up as an error on a _FailedTest
    total = len(res.units)
    passed = sum(1 for u in res.units if u["ok"])
    print(json.dumps({"total": total, "passed": passed, "units": res.units}))


main()

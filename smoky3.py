#!/usr/bin/env python3
import requests
from requests import get
from requests.compat import urljoin
from requests.exceptions import ConnectionError
from yaml import load as yaml_load
from yaml.scanner import ScannerError
from sys import argv, exit
import asyncio

# Not checking SSL validity
requests.packages.urllib3.disable_warnings()


class HttpSmokeTest(object):
    """
    Class that holds the tests
    """
    def __init__(self, hostname, host, proto='https'):
        self.hostname = hostname
        self.host = host
        self.proto = proto
        self.total = 0
        self.passed = 0
        self.results = []

    def _count(func):
        """
        Private decorator to keep running count
        """
        def do_count(self, *args, **kwargs):
            self.total += 1
            result = func(self, *args, **kwargs)
            if result[0]:
                self.passed += 1
            return result
        return do_count

    @_count
    def check_200(self, path):
        """
        Check path returns a 200
        """
        try:
            r = get(self.make_url(path), headers={'Host': self.host},
                    verify=False, allow_redirects=False)
        except ConnectionError as e:
            return (False, str(e))
        if r.status_code is 200:
            return (True, "")
        return (False, "Got {}".format(r.status_code))

    @_count
    def check_3xx(self, path, next_url):
        """
        Check first redirect of path is next_url
        """
        try:
            r = get(self.make_url(path), headers={'Host': self.host},
                    verify=False)
        except ConnectionError as e:
            return (False, str(e))
        chain = [res.url for res in r.history] + [r.url]
        if r.status_code is not 200:
            return (False, "Got a {}".format(r.status_code))
        if len(chain) == 1:
            return (False, "No redirect found")
        if chain[1] == next_url:
            return (True, "")
        return (False, "Got: {} ({})".format(chain[1], r.status_code))

    @_count
    def check_header(self, path, header, content):
        """
        Check header for path contains at least content
        """
        try:
            r = get(self.make_url(path), headers={'host': self.host},
                    allow_redirects=False)
        except ConnectionError as e:
            return (False, str(e))
        if header not in r.headers:
            return (False, "{} not found in headers".format(header))
        if content in r.headers[header]:
            return (True, "")
        return(False, "'{}' not found in {}".format(content, header))

    def make_url(self, path):
        """
        Form a URL
        """
        return urljoin("{}://{}".format(self.proto, self.hostname), path)


class Test(object):
    """
    Test class reads a YAML config and runs the asyncio loop to run the
    tests in parallel
    """
    def __init__(self, hostname, file):
        self.hostname = hostname
        self.results = dict()
        self.passed = dict()
        self.total = dict()
        self.loop = None
        try:
            with open(file) as f:
                self.tests = yaml_load(f)
        except (IOError, ScannerError) as e:
            print("Error reading YAML: {}".format(e))
            exit(101)

    def run(self, targets=None, concurrent=5):
        """
        Run tests (with concurrency)
        """
        targets = self.tests.keys() if not targets else targets

        for target in targets:
            if target.lower().startswith("https://"):
                proto = "https"
                host = target.split("//")[1]
            elif target.lower().startswith("http://"):
                proto = "http"
                host = target.split("//")[1]
            else:
                proto = "https"
                host = target

            # Somewhere to put our results
            self.results[target] = []
            # Get an instance of HttpSmokeTest to run tests
            s = HttpSmokeTest(hostname=self.hostname, host=host, proto=proto)

            for check in self.tests[target]:
                # Find our test in HttpSmokeTest
                try:
                    test = getattr(s, check)
                except AttributeError:
                    raise NotImplementedError(
                        "Check {} not implemented".format(check))

                # Start an async loop to run our tests
                semaphore = asyncio.Semaphore(concurrent)

                loop = asyncio.get_event_loop()

                tasks = []
                for task in self.tests[target][check]:
                    if type(task) is not list:
                        task = [task]
                    self.results[target].append(dict(
                        check=check,
                        task=task,
                    ))
                    tasks.append(Test._runtest(
                        loop, semaphore, test, task, self.results[target][-1]))

                loop.run_until_complete(asyncio.gather(*tasks))
                # Following line is commented beacuse of
                #   https://github.com/python/asyncio/issues/258
                # loop.close()
                self.passed[target] = s.passed
                self.total[target] = s.total

    @staticmethod
    @asyncio.coroutine
    def _runtest(loop, semaphore, test, task, result):
        """
        Run the test in executor (non-blocking)
        """
        with (yield from semaphore):
            t = loop.run_in_executor(None, test, *task)
            result['result'] = yield from t

    @staticmethod
    def pretty_status(cond):
        """
        Return a pretty [ OK ] of [ FAIL ] based on cond
        """
        OKGREEN = '\033[92m'
        FAIL = '\033[91m'
        ENDC = '\033[0m'
        BOLD = '\033[1m'

        if cond:
            return "{}[ OK ]{}".format(
                BOLD + OKGREEN, ENDC)
        return "{}[ FAIL ]{}".format(
            BOLD + FAIL, ENDC)

    def print_summary(self):
        self._print()

    def print_all(self):
        self._print(showpassed=True, showfailed=True)

    def print_failed(self):
        self._print(showfailed=True)

    def _print(self, showpassed=False, showfailed=False):
        """
        Long output of test results
        """
        for target in self.results:
            for r in self.results[target]:
                if (r['result'][0] and showpassed) or (
                  not r['result'][0] and showfailed):
                    print("{}:\t{}:\t{}\n\t{}\n{}".format(
                        target, r['check'],
                        Test.pretty_status(
                            r['result'][0]), ", ".join(r['task']),
                        (r['result'][1] + "\n" if r['result'][1] else "")))
        for target in t.total:
            print("{}/{} passed for {}".format(
                t.passed[target], t.total[target], target))

    def all_passed(self):
        for target in self.total:
            if self.total[target] != self.passed[target]:
                return False
        return True


if __name__ == "__main__":
    if len(argv) != 3:
        print("Usage: {} <hostname> <config>".format(argv[0]))
        exit(101)
    t = Test(hostname=argv[1], file=argv[2])
    t.run(concurrent=10)
    t.print_failed()
    if not t.all_passed():
        exit(102)

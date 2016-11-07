#!/usr/bin/python
#
# Copyright (c) 2016 All rights reserved
# This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
import time

import functest.utils.functest_logger as ft_logger

logger = ft_logger.Logger("sdnvpn-results").getLogger()


class Results(object):

    def __init__(self, line_length):
        self.line_length = line_length
        self.test_result = "PASS"
        self.summary = ""
        self.details = []
        self.num_tests = 0
        self.num_tests_failed = 0

    def get_ping_status(self,
                        vm_source, ip_source,
                        vm_target, ip_target,
                        expected="PASS", timeout=30):
        console_log = vm_source.get_console_output()

        if "request failed" in console_log:
            # Normally, cirros displays this message when userdata fails
            logger.debug("It seems userdata is not supported in "
                         "nova boot...")
            return False
        else:
            tab = ("%s" % (" " * 53))
            expected_result = 'can ping' if expected == 'PASS' \
                              else 'cannot ping'
            test_case_name = ("'%s' %s '%s'" %
                              (vm_source.name,
                               expected_result,
                               vm_target.name))
            logger.debug("%sPing\n%sfrom '%s' (%s)\n%sto '%s' (%s).\n"
                         "%s-->Expected result: %s.\n"
                         % (tab, tab, vm_source.name, ip_source,
                            tab, vm_target.name, ip_target,
                            tab, expected_result))
            while True:
                console_log = vm_source.get_console_output()
                # the console_log is a long string, we want to take
                # the last 4 lines (for example)
                lines = console_log.split('\n')
                last_n_lines = lines[-5:]
                if ("ping %s OK" % ip_target) in last_n_lines:
                    msg = ("'%s' can ping '%s'"
                           % (vm_source.name, vm_target.name))
                    if expected == "PASS":
                        logger.debug("[PASS] %s" % msg)
                        self.add_to_summary(2, "PASS", test_case_name)
                    else:
                        logger.debug("[FAIL] %s" % msg)
                        self.test_result = "FAIL"
                        self.add_to_summary(2, "FAIL", test_case_name)
                        logger.debug("\n%s" % last_n_lines)
                    break
                elif ("ping %s KO" % ip_target) in last_n_lines:
                    msg = ("'%s' cannot ping '%s'" %
                           (vm_source.name, vm_target.name))
                    if expected == "FAIL":
                        logger.debug("[PASS] %s" % msg)
                        self.add_to_summary(2, "PASS", test_case_name)
                    else:
                        logger.debug("[FAIL] %s" % msg)
                        self.test_result = "FAIL"
                        self.add_to_summary(2, "FAIL", test_case_name)
                    break
                time.sleep(1)
                timeout -= 1
                if timeout == 0:
                    self.test_result = "FAIL"
                    logger.debug("[FAIL] Timeout reached for '%s'. "
                                 "No ping output captured in the console log"
                                 % vm_source.name)
                    self.add_to_summary(2, "FAIL", test_case_name)
                    break

    def add_to_summary(self, num_cols, col1, col2=""):
        if num_cols == 0:
            self.summary += ("+%s+\n" % (col1 * (self.line_length - 2)))
        elif num_cols == 1:
            self.summary += ("| " + col1.ljust(self.line_length - 3) + "|\n")
        elif num_cols == 2:
            self.summary += ("| %s" % col1.ljust(7) + "| ")
            self.summary += (col2.ljust(self.line_length - 12) + "|\n")
            if col1 in ("FAIL", "PASS"):
                self.details.append({col2: col1})
                self.num_tests += 1
                if col1 == "FAIL":
                    self.num_tests_failed += 1

    def check_ssh_output(self, vm_source, ip_source,
                         vm_target, ip_target,
                         expected, timeout=30):
        console_log = vm_source.get_console_output()

        if "request failed" in console_log:
            # Normally, cirros displays this message when userdata fails
            logger.debug("It seems userdata is not supported in "
                         "nova boot...")
            return False
        else:
            tab = ("%s" % (" " * 53))
            test_case_name = ("[%s] returns 'I am %s' to '%s'[%s]" %
                              (ip_target, expected,
                               vm_source.name, ip_source))
            logger.debug("%sSSH\n%sfrom '%s' (%s)\n%sto '%s' (%s).\n"
                         "%s-->Expected result: %s.\n"
                         % (tab, tab, vm_source.name, ip_source,
                            tab, vm_target.name, ip_target,
                            tab, expected))
            while True:
                console_log = vm_source.get_console_output()
                # the console_log is a long string, we want to take
                # the last 4 lines (for example)
                lines = console_log.split('\n')
                last_n_lines = lines[-5:]
                if ("%s %s" % (ip_target, expected)) in last_n_lines:
                    logger.debug("[PASS] %s" % test_case_name)
                    self.add_to_summary(2, "PASS", test_case_name)
                    break
                elif ("%s not reachable" % ip_target) in last_n_lines:
                    logger.debug("[FAIL] %s" % test_case_name)
                    self.add_to_summary(2, "FAIL", test_case_name)
                    self.test_result = "FAIL"
                    break
                time.sleep(1)
                timeout -= 1
                if timeout == 0:
                    self.test_result = "FAIL"
                    logger.debug("[FAIL] Timeout reached for '%s'."
                                 " No ping output captured in the console log"
                                 % vm_source.name)
                    self.add_to_summary(2, "FAIL", test_case_name)
                    break

    def compile_summary(self, SUCCESS_CRITERIA):
        success_message = "All the subtests have passed."
        failure_message = "One or more subtests have failed."

        self.add_to_summary(0, "=")
        logger.info("\n%s" % self.summary)
        if self.test_result == "PASS":
            logger.info(success_message)
        else:
            logger.info(failure_message)

        status = "PASS"
        success = 100 - \
            (100 * int(self.num_tests_failed) / int(self.num_tests))
        if success < int(SUCCESS_CRITERIA):
            status = "FAILED"

        return {"status": status, "details": self.details}

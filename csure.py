#!/usr/bin/env python3

# Copyright 2020-2021 Spirent Communications, All Rights Reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License
from __future__ import print_function

import logging
import os
import sys
import argparse
import time
import datetime
from conf import settings

from cloudsure import configuration
from cloudsure import ProfileTemplatesApi
from cloudsure import TestcaseTemplatesApi
from cloudsure.rest import ApiException

VERBOSITY_LEVELS = {
    'debug': logging.DEBUG,
    'info': logging.INFO,
    'warning': logging.WARNING,
    'error': logging.ERROR,
    'critical': logging.CRITICAL
}

_CURR_DIR = os.path.dirname(os.path.realpath(__file__))
_LOGGER = logging.getLogger()

def parse_arguments():
    """
    Parse command line arguments.
    """
    parser = argparse.ArgumentParser(prog=__file__, formatter_class=
                                     argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--version', action='version', version='%(prog)s 0.1')
    parser.add_argument('--list-tests', action='store_true',
                        help='list all configured-tests')
    parser.add_argument('--list-cloud', action='store_true',
                        help='list the configured cloud ')
    args = vars(parser.parse_args())
    return args

def configure_logging(level):
    """Configure logging.
    """
    name, ext = os.path.splitext(settings.getValue('LOG_FILE_DEFAULT'))
    rename_default = "{name}_{uid}{ex}".format(name=name,
                                               uid=settings.getValue(
                                                   'LOG_TIMESTAMP'),
                                               ex=ext)
    log_file_default = os.path.join(
        settings.getValue('RESULTS_PATH'), rename_default)
    _LOGGER.setLevel(logging.DEBUG)
    stream_logger = logging.StreamHandler(sys.stdout)
    stream_logger.setLevel(VERBOSITY_LEVELS[level])
    stream_logger.setFormatter(logging.Formatter(
        '[%(levelname)-5s]  %(asctime)s : (%(name)s) - %(message)s'))
    _LOGGER.addHandler(stream_logger)
    file_logger = logging.FileHandler(filename=log_file_default)
    file_logger.setLevel(logging.DEBUG)
    file_logger.setFormatter(logging.Formatter(
        '%(asctime)s : %(message)s'))
    _LOGGER.addHandler(file_logger)

def handle_list_options(args):
    """ Process --list cli arguments if needed

    :param args: A dictionary with all CLI arguments
    """
    if args['list_cloud']:
        print("WIP - Cloud")
        sys.exit(0)

    if args['list_tests']:
        print("WIP - Tests")
        sys.exit(0)

def run_history(testcase_id, order='desc', duration=''):
    if not testcase_id:
        raise RuntimeError('Must specify a test case ID')

    print('Run history for {}'.format(testcase_id))
    eapi = ExecutionsApi()
    try:
        if duration:
            runs = eapi.get_testcase_execution_list(testcase_id=testcase_id,
                                                    sort_order=order.lower(),
                                                    sort_property='created_at',
                                                    range_property='created_at',
                                                    range_duration=duration).items
        else:
            runs = eapi.get_testcase_execution_list(testcase_id=testcase_id,
                                                    sort_order=order.lower(),
                                                    sort_property='created_at').items
        print('{:^5}|{:^60}|{:^34}|{:^21}|{:^15}|'.format(
            'Run',
            'Test case name',
            'Start time',
            'Duration (hh:mm:ss)',
            'Status'))
        print('-' * 140)
        if not runs:
            print('{:^140}'.format("No data matching filter criteria"))
        else:
            for i, run in enumerate(runs, start=1):
                run_duration = run.end_time - run.start_time
                print('{:^5d}|{:^60s}|{:^34s}|{:^21s}|{:^15s}|'.format(
                    i,
                    run.name,
                    str(run.start_time),
                    str(run_duration),
                    run.status))
        print('-' * 140)
    except ApiException as apie:
        raise RuntimeError("API exception: %s\n" % apie)
    except Exception as gene:
        print('query error: {}'.format(gene))
        return

def get_template_schema(template_type, template_id):
    if template_type == 'testcase':
        ttapi = TestcaseTemplatesApi()
        try:
            # Get a testcase-template
            tmpl = ttapi.get_testcase_template(template_id, x_spirent_metadata_only=False)
            return tmpl.input_schema
        except ApiException as apie:
            raise RuntimeError(
                "Exception when calling TestcaseTemplatesApi->get_testcase_template: %s\n" % apie)
    elif template_type == 'profile':
        ptapi = ProfileTemplatesApi()
        try:
            # Get a profile-template
            tmpl = ptapi.get_profile_template(template_id, x_spirent_metadata_only=False)
            return tmpl.input_schema
        except ApiException as apie:
            raise RuntimeError(
                "Exception when calling ProfileTemplatesApi->get_profile_template: %s\n" % apie)
    return {}

def create_project(testcase_templates, project_name, cleanup):
    """
    Create Project.

    """
    papi = ProjectsApi()
    tapi = TestcasesApi()
    project = None

    # Create an empty project
    try:
        project_body = EmptyProject(
            name=project_name,
            description='Demonstrates creation of a project with one or more testcases.')
        project = papi.create_project(project_body)
    except ApiException as apie:
        raise RuntimeError("Exception when calling ProjectsApi->create_project: %s\n" % apie)

    # Create test cases under the project
    try:
        for tmpl in testcase_templates:
            testcase_name = tmpl.replace('_', ' ').title()
            tc_input = {}  # this is where you'd provide valid test case input
            testcase_body = Testcase(name=testcase_name,
                                     project_id=project.id,
                                     testcase_template_id=tmpl,
                                     enabled=True,
                                     input=tc_input)
            try:
                tapi.create_testcase(testcase_body)
            except ApiException as apie:
                raise RuntimeError("Exception when calling TestcasesApi->create_testcase: %s\n" % apie)
        project = papi.get_project(project.id)
    finally:
        if cleanup:
            if project:
                papi.delete_project(project.id, delete_testcases=True)
    return project

def run_test(testcase_id, input_path, project_id, poll_interval_sec):
    if not testcase_id and not project_id:
        raise RuntimeError('Must specify either testcase or project ID')
    if testcase_id and project_id:
        raise RuntimeError('Must specify either testcase or project ID, but not both')
    if project_id and input_path:
        raise RuntimeError('Input is applicable only when testcase is specified')
    papi = ProjectsApi()
    tapi = TestcasesApi()
    eapi = ExecutionsApi()
    try:
        if testcase_id:
            testcase = tapi.get_testcase(testcase_id)
            if input_path:
                # Configure the testcase
                tc_input = None
                with open(input_path) as inpf:
                    tc_input = json.load(inpf)
                if tc_input:
                    testcase.input = tc_input
                    testcase = tapi.update_testcase(testcase.id, testcase)
                    print('Testcase configured successfully')

            execution = tapi.start_testcase(
                testcase.id,
                config=ExecutionOptions(step_mode=False))
            print('Executing {}'.format(testcase.name))
        elif project_id:
            project = papi.get_project(project_id)
            execution = papi.start_project(project_id)
            print('Executing {}'.format(project.name))
    except ApiException as apie:
        raise RuntimeError("API exception: %s\n" % apie)
    except Exception as gene:
        print('execution error: {}'.format(gene))
        return {}
    # Wait for execution to complete
    execution = wait_for_execution(eapi, execution.id, poll_interval_sec=poll_interval_sec)
    # Display overall execution status and the status of each test case execution
    print('Execution is {}'.format(execution.status))
    for tc_exec in execution.executions:
        tc_info = tapi.get_testcase(tc_exec.testcase_id)
        print('  {}: {} - {}'.format(tc_info.name, tc_exec.status, tc_exec.status_message))


def wait_for_execution(exec_api, execution_id, poll_interval_sec=1):
    VALID_STATUS = ['RUNNING', 'DONE', 'PAUSED']
    VALID_TC_STATUS = ['RUNNING', 'PAUSED', 'PASS', 'FAIL', 'ERROR', 'STOPPED', 'QUEUED']
    tc_exec = {}
    while True:
        try:
            execution = exec_api.get_execution(execution_id)
        except ApiException as apie:
            raise RuntimeError("Exception when calling ExecutionsApi->get_execution: %s\n" % apie)
        status = execution.status
        if status not in VALID_STATUS:
            raise RuntimeError('Invalid execution status: {}.'.format(status))
        if status == 'DONE' or status == 'PAUSED':
            return execution
        # We're dealing with a running testcase at this point.
        # Look for current testcase being executed and print its current step to stdout.
        executions = execution.executions
        if not executions:
            continue
        for exc in executions:
            tc_status = exc.status
            if tc_status not in VALID_TC_STATUS:
                raise RuntimeError('Invalid testcase execution status: {}.'.format(tc_status))
            if tc_status != 'RUNNING':
                continue
            step = exc.current_step
            if not step:
                continue
            if step.index == '-':
                step_info = '{} - {}'.format(step.name, step.description)
            else:
                step_info = 'Step {} of {}: {} - {}'.format(step.index, step.total,
                                                            step.name, step.description)
            tc_id = exc.testcase_id
            if not tc_id:
                continue
            # Only print an update if test moved to a new step
            prev_step_info = tc_exec.get(tc_id, '')
            if prev_step_info != step_info:
                tc_exec[tc_id] = step_info
                print(step_info)
        time.sleep(poll_interval_sec)

def main():
    """Main function.
    """
    args = parse_arguments()

    # define the timestamp to be used by logs and results
    date = datetime.datetime.fromtimestamp(time.time())
    timestamp = date.strftime('%Y-%m-%d_%H-%M-%S')
    settings.setValue('LOG_TIMESTAMP', timestamp)


    # configure settings
    settings.load_from_dir(os.path.join(_CURR_DIR, 'conf'))

    # if required, handle list-* operations
    handle_list_options(args)

    results_dir = "results_" + timestamp
    results_path = os.path.join(settings.getValue('LOG_DIR'), results_dir)
    settings.setValue('RESULTS_PATH', results_path)
    # create results directory
    if not os.path.exists(results_path):
        os.makedirs(results_path)

    configure_logging(settings.getValue('VERBOSITY'))

    # Perform Sanity Checks.


    # Start Tests

if __name__ == "__main__":
    main()

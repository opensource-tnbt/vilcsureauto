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

import logging
import os
import sys
import argparse
import time
import datetime
from conf import settings

from __future__ import print_function
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

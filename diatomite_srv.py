#!/usr/bin/env python2
"""
    diatomite - Monitoring server for the diatomite system.
    Monitors frequencies and reports on signal levels and activity
    using one or more Gnu Radio sources.

    Copyright (C) 2017 Duarte Alencastre

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <https://www.gnu.org/licenses/>.
                    GNU AFFERO GENERAL PUBLIC LICENSE
                       Version 3, 19 November 2007
"""

import logging
import argparse
import diatomite_site_probe as dia_sp


# TODO: remove tracefunc before release
def tracefunc(frame, event, arg, indent=[0]):
    import inspect
    import os
    try:
        class_name = frame.f_locals['self'].__class__.__name__
    except KeyError:
        class_name = None
 
    try:
        module_name = inspect.currentframe().f_back.f_globals["__file__"]
    except KeyError:
        module_name = None
 
    try:
        mn = os.path.basename(module_name)
    except:
        mn = module_name
 
    call_data = '{c}.{m} :{mn}'.format(c=class_name,
                                       m=frame.f_code.co_name,
                                       mn=mn)
 
    if event == "call":
        indent[0] += 2
        print "-" * indent[0] + "> call function {d}".format(d=call_data)
    elif event == "return":
        print "<" + "-" * indent[0], "exit function {d}".format(d=call_data)
        indent[0] -= 2
    return tracefunc


def arg_parser():
    """Parse command line arguments.
    Returns an argument dictionary"""

    msg = 'Parsing the arguments'
    logging.debug(msg)

    parser = argparse.ArgumentParser(description='Run a diatomite server.')
    parser.add_argument('-f', '--config-file',
                        help='specify configuration file',
                        dest='config_file', required=True)
    parser.add_argument('-D', '--daemonize',
                        help='Run the server as a Daemon',
                        dest='daemonize', action='store_true',
                        default=False)
    parser.add_argument('-v', '--verbose',
                        help='Increase logging verbosity',
                        dest='verbose', action='store_true',
                        default=False)
    args = parser.parse_args()

    return args


def main():
    """Main processing block for the server"""

    args = arg_parser()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    msg = 'Arguments:{args}'.format(args=args)
    logging.debug(msg)

    dia_conf = dia_sp.DiaConfParser()

    try:
        dia_conf.read_conf_file(args.config_file)
    except dia_sp.DiaConfParserError, exc:
        msg = 'FATAL: Unable to process configurations:{m}'.format(m=exc)
        raise

    this_site = dia_sp.DiatomiteSite(conf=dia_conf.get_config())

    this_site.start()

if __name__ == "__main__":

#     import sys
#     sys.setprofile(tracefunc)

    logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.INFO)

    main()

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
    logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.INFO)

    main()

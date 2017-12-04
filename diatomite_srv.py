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
import yaml
import radiosource
import freqlistener
import diatomite_aux_classes as dia_aux

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

def config_parser(conf_file):
    """Parse the configuration file
    Returns a configuration dictionary"""

    conf = {}

    msg = 'Parsing the configuration on file {file}'.format(file=conf_file)
    logging.debug(msg)

    try:
        with open(conf_file, 'r') as stream:
            try:
                conf = yaml.load(stream)
            except yaml.YAMLError, exc:
                msg = 'Error parsing configuration:{m}'.format(m=exc)
                logging.error(msg)
                raise
    except IOError, exc:
        msg = 'Error reading configuration file:{m}'.format(m=exc)
        logging.error(msg)
        raise

    msg = 'Configuration:{conf}'.format(conf=conf)
    logging.debug(msg)

    return conf

def setup_probe(probe, probe_conf):
    """Setup the probe
    probe --- the probe object
    probe_conf -- probe configuration
    """
    
    # list of supported source types
    # currently only RTL2838_R820T2
    supported_source_types = ['RTL2838_R820T2']
    
    try:
        probe.set_id(probe_conf['id'])
    except KeyError, exc:
        msg = ('FATAL: missing id for probe.'
               ' Missing key {exc} on configuration file').format(exc=exc)
        logging.error(msg)
        raise Exception(msg)

    try:
        radio_sources_conf = probe_conf['RadioSources']
    except KeyError, exc:
        msg = ('FATAL: missing Radio Sources for probe.'
               ' Missing key {exc} on configuration file').format(exc=exc)
        logging.error(msg)
        raise Exception(msg)

    # configure radio sources and add them to the probe
    for radio_source_key in radio_sources_conf:
        print radio_source_key
        
        try:
            r_source_type = radio_sources_conf[radio_source_key]['type']
        except KeyError, exc:
            msg = ('FATAL: missing Radio Source type for'
                   ' radio Source {rs}.'
                   ' Missing key {exc} on'
                   ' configuration file').format(exc=exc, rs=radio_source_key)
            logging.error(msg)
            raise Exception(msg)
        
        try:
            r_source_id =  radio_sources_conf[radio_source_key]['id']
        except KeyError, exc:
            msg = ('FATAL: missing Radio Source id for'
                   ' radio Source {rs}.'
                   ' Missing key {exc} on'
                   ' configuration file').format(exc=exc, rs=radio_source_key)
            logging.error(msg)
            raise Exception(msg)
        
        if r_source_type in supported_source_types:
            r_source = radiosource.RTL2838R820T2RadioSource(r_source_id)
                
        # TODO: add remaingin config to the radio source
        
        # TODO: add listeners to the radio source (in separate function)
      
        # add the radio sources to the probe
        probe.add_radio_source(r_source)


def main():
    """Main processing block for the server"""

    args = arg_parser()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    msg = 'Arguments:{args}'.format(args=args)
    logging.debug(msg)

    try:
        conf = config_parser(args.config_file)
    except (IOError, yaml.YAMLError), exc:
        msg = 'FATAL: Unable to process configurations:{m}'.format(m=exc)
        raise

    if 'site' in conf:
        try:
            probe_conf = conf['site']['probe']
        except KeyError, exc:
            msg = ('FATAL: configuration error, missing probe definition'
                   ' Missing key {exc} on configuration file').format(exc=exc)
            raise Exception(msg)
    else:
        msg = 'FATAL: configuration error, missing site definition'
        raise Exception(msg)

    this_probe = dia_aux.DiatomiteProbe()

    setup_probe(this_probe, probe_conf)
    
    # TODO: setup API

if __name__ == "__main__":
    logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.INFO)

    main()

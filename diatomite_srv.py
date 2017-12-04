#!/usr/bin/env python2

import radiosource
import diatomite_aux_classes as dia_aux
import freqlistener
import logging
import argparse
import yaml


def arg_parser():
    """Parse command line arguments.
    Returns an argument dictionary"""
    
    msg = 'Parsing the arguments'
    logging.debug(msg)
    
    parser = argparse.ArgumentParser(description='Run a diatomite server.')
    parser.add_argument('-f', '--config-file', 
                        help='specify configuration file',
                        dest = 'config_file', required=True)
    parser.add_argument('-D', '--daemonize', 
                        help='Run the server as a Daemon',
                        dest = 'daemonize', action = 'store_true', 
                        default = False)
    parser.add_argument('-v', '--verbose', 
                        help='Increase logging verbosity',
                        dest = 'verbose', action = 'store_true', 
                        default = False)
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

def main():
    
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

    msg = "This doesn't do anything. Yet..."
    logging.info(msg)
    


if __name__ == "__main__":
    logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.INFO)

    main()

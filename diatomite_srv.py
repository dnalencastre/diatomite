#!/usr/bin/env python2

import radiosource
import diatomite_aux_classes as dia_aux
import freqlistener
import logging as log
import argparse


def arg_parser():
    """Parse command line arguments.
    Returns an argument dictionary"""
    
    msg = 'Parsing the arguments'
    log.debug(msg)
    
    parser = argparse.ArgumentParser(description='Run a diatomite server.')
    parser.add_argument('-f', '--config-file', 
                        help='specify configuration file',
                        dest = 'config_file', required=True)
    parser.add_argument('-d', '--daemonize', 
                        help='Run the server as a Daemon',
                        dest = 'daemonize', action = 'store_true', 
                        default = False)
    args = parser.parse_args()

    return args

def config_parser(conf_file):
    """Parse the configuration file
    Returns a configuration dictionary"""
    
    conf = {}
    
    msg = 'Parsing the configuration on {file}'.format(file=conf_file)
    log.debug(msg)
    
    msg = "This doesn't do anything. Yet..."
    log.info(msg)
    
    return conf

def main():
    
    args = arg_parser()
    
    print 'Arguments:{args}'.format(args=args)
    
    conf = config_parser(args.config_file)
    
    msg = "This doesn't do anything. Yet..."
    log.info(msg)
    


if __name__ == "__main__":
#     log.basicConfig(format='%(levelname)s:%(message)s', level=log.INFO)
    log.basicConfig(format='%(levelname)s:%(message)s', level=log.DEBUG)


    main()
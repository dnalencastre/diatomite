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
import diatomite_api as dia_api

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

def setup_listeners(radio_source, listeners_conf):
    """Setup listeners for a source
    radio_source -- radio source being configured
    listeners_conf -- listeners configuration"""


    for listeners_key in listeners_conf:

        try:
            listener_id = listeners_conf[listeners_key]['id']
        except KeyError, exc:
            msg = ('FATAL: missing Listener id for'
                   ' Listener {rs}.'
                   ' Missing key {exc} on'
                   ' configuration file').format(exc=exc, rs=listener_id)
            logging.error(msg)
            raise Exception(msg)

        listener = freqlistener.FreqListener(listener_id)

        try:
            frequency = listeners_conf[listeners_key]['frequency']
        except KeyError, exc:
            msg = ('FATAL: missing Frequency definition for'
                   ' Listener {rs}.'
                   ' Missing key {exc} on'
                   ' configuration file').format(exc=exc, rs=listener_id)
            logging.error(msg)
            raise Exception(msg)

        msg = ('Frequency for listener "{id}"'
               ' configured as: {f} Hz').format(id=listener_id, f=frequency)
        logging.debug(msg)

        listener.set_frequency(frequency)

        try:
            modulation = listeners_conf[listeners_key]['modulation']
        except KeyError, exc:
            msg = ('Missing modulation definition for'
                   ' Listener {rs}.'
                   ' Missing key {exc} on'
                   ' configuration file').format(exc=exc, rs=listener_id)
            logging.warning(msg)
            modulation = None
        else:
            try:
                listener.set_modulation(modulation)
            except freqlistener.FreqListenerInvalidModulationError, exc:
                msg = ('Invalid modulation definition for'
                       ' Listener {rs}: {exc}').format(exc=exc, rs=listener_id)
                logging.error(msg)
                raise Exception(msg)

        try:
            bandwidth = listeners_conf[listeners_key]['bandwidth']
        except KeyError, exc:
            msg = ('FATAL: missing bandwidth definition for'
                   ' Listener {rs}.'
                   ' Missing key {exc} on'
                   ' configuration file').format(exc=exc, rs=listener_id)
            logging.error(msg)
            raise Exception(msg)

        listener.set_bandwidth(bandwidth)

        try:
            threshold = listeners_conf[listeners_key]['level_threshold']
        except KeyError, exc:
            msg = ('FATAL: missing threshold definition for'
                   ' Listener {rs}.'
                   ' Missing key {exc} on'
                   ' configuration file').format(exc=exc, rs=listener_id)
            logging.error(msg)
            raise Exception(msg)

        listener.set_signal_pwr_threshold(threshold)

        try:
            audio_enable = listeners_conf[listeners_key]['audio_output']
        except KeyError, exc:
            msg = ('Missing audio output definition for'
                   ' Listener {rs}.'
                   ' Missing key {exc} on'
                   ' configuration file').format(exc=exc, rs=listener_id)
            logging.warning(msg)
            modulation = None
            listener.set_audio_enable(False)
        else:
            if audio_enable == 'True' and modulation != None:

                listener.set_audio_enable(True)
            else:
                listener.set_audio_enable(False)

            msg = ('Audio output not enabled.'
                   'modulation:{m}, audio_output:{ao}').format(m=modulation,
                                                               ao=audio_enable)

        # TODO: add freqyency analyzer enable

        #add to listener to the radio source
        radio_source.add_frequency_listener(listener)

def setup_probe(probe, probe_conf):
    """Setup the probe
    probe --- the probe object
    probe_conf -- probe configuration
    """

    try:
        tap_path = probe_conf['tap_directory']
    except KeyError, exc:
        msg = 'Tap directory not configured'
        logging.info(msg)
        tap_path = None

    # TODO: set center frequency

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
            r_source_id = radio_sources_conf[radio_source_key]['id']
        except KeyError, exc:
            msg = ('FATAL: missing Radio Source id for'
                   ' radio Source {rs}.'
                   ' Missing key {exc} on'
                   ' configuration file').format(exc=exc, rs=radio_source_key)
            logging.error(msg)
            raise Exception(msg)

        # check if the radio source type is valid and set the class accordingly
        supported_devs = radiosource.RadioSourceSupportedDevs()
        try:
            radio_source_class = supported_devs.get_dev_class(r_source_type)
        except radiosource.RadioSourceSupportedDevsError, exc:
            raise

        # set the class to be use:
        msg = 'Will use radio source class "{rsc}"'.format(rsc=radio_source_class)
        logging.debug(msg)
        rs_class_ = getattr(radiosource, radio_source_class)
        r_source = rs_class_(r_source_id)

        if tap_path != None:
            try:
                r_source.set_tap_directory(tap_path)
            except radiosource.RadioSourceError, exc:
                msg = 'Error setting tap directory:{exc}'.format(exc=exc)

        try:
            frequency = radio_sources_conf[radio_source_key]['frequency']
        except KeyError, exc:
            msg = ('FATAL: missing Frequency definition for'
                   ' radio source {rs}.'
                   ' Missing key {exc} on'
                   ' configuration file').format(exc=exc, rs=radio_source_key)
            logging.error(msg)
            raise Exception(msg)

        r_source.set_frequency(float(frequency))

        try:
            audio_enable = radio_sources_conf[radio_source_key]['audio_output']
        except KeyError, exc:
            msg = ('Missing audio output definition for'
                   ' radio source {rs}.'
                   ' Missing key {exc} on'
                   ' configuration file').format(exc=exc, rs=r_source_id)
            logging.warning(msg)
            r_source.set_audio_enable(False)
        else:
            if audio_enable == 'True':
                r_source.set_audio_enable(False)

        # add listeners to the radio source
        try:
            listeners_conf = radio_sources_conf[radio_source_key]['listeners']
        except KeyError, exc:
            msg = ('Missing listeners definition for'
                   ' radio Source {rs}.'
                   ' Missing key {exc} on'
                   ' configuration file').format(exc=exc, rs='listeners')
            logging.error(msg)
            raise Exception(msg)

        setup_listeners(r_source, listeners_conf)

        # add the radio sources to the probe
        probe.add_radio_source(r_source)
    
    # start probes
    probe.start_sources()

def setup_api_srv(api_srv, conf):
    """Setup and start the api server
        api_srv --- the api server object
        probe_conf -- probe configuration
    """
    
    api_srv.start()

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

    api_srv = dia_api.ApiSvc(probe_conf)
    
    setup_api_srv(api_srv, probe_conf)

    setup_probe(this_probe, probe_conf)

    # TODO: setup API
    


if __name__ == "__main__":
    logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.INFO)

    main()

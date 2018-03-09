#!/usr/bin/env python2
"""
    diatomite - Probe and site classes for the diatomite system
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
import sys
import os
from multiprocessing import Queue
import yaml
import diatomite_api
import radiosource
import diatomite_aux as dia_aux


class DiaConfParserError(Exception):
    """Raised when unable to read a meaningful configuration"""
    pass


class Probes(object):
    """Object for collections of probe."""

    _probe_dict = {}

    def __init__(self, probes_conf=None, site_conf=None, site_id=None):
        """Initialize the Probes collection
        probes_conf -- a dictionary with a valid configuration
        site_conf -- a dictionary with the site configuration"""
        if (probes_conf is not None and site_conf is not None
                and site_id is not None):
            # read configuration
            self.configure(probes_conf, site_conf, site_id)

    def configure(self, probes_conf, site_conf, site_id):
        """Configure the Probes collection
        probes_conf -- a dictionary with a valid configuration
        site_conf -- a dictionary with the site configuration
        site_id -- the site id"""

        # initialize each probe
        # although there should only be one probe
        for probe_id in probes_conf:
            this_probe = DiatomiteProbe(probes_conf[probe_id], site_conf,
                                        site_id)
            self._probe_dict[probe_id] = this_probe

    def start(self):
        """Start this object and it's children"""
        for probe_id in self._probe_dict:
            self._probe_dict[probe_id].start()

    def stop(self):
        """Stop this object and it's children"""
        for probe_id in self._probe_dict:
            self._probe_dict[probe_id].stop()


class DiatomiteSite(object):
    """Define a site for diatomite probes.
    Used to give the site a name and to tie a probe to a location.
    A site may have multiple probes, but an object of this type does not need
    to be aware of any other diatomite probes existing other than the one
    being executed by the running process."""

    def __init__(self, conf=None):

        self._id = None

        # Location for this site
        self._location = dia_aux.Location()

        self._type = None
        self._probes = None
        # Site name
        self.site_name = ''

        if conf is not None:
            # read configuration
            self.configure(conf)

    def configure(self, conf):
        """Configure the site
        conf -- a dictionary with a valid configuration
                (use DiaConfParser to obtain a valid config)"""

        # get the id, although it's a dict of sites, there should
        # only be an item
        site_id = conf['sites'].keys()[0]
        self.set_id(site_id)

        site_conf = conf['sites'][site_id]

        self.set_location(site_conf['address'], site_conf['latitude'],
                          site_conf['longitude'], site_conf['coord_type'])

        self.set_type(site_conf['type'])

        self.set_probes(site_conf['probes'], conf['sites'])

    def set_id(self, site_id):
        """Set the site's id
        site_id - id string"""

        self._id = site_id

    def set_location(self, address, latitude, longitude, coord_type):
        """Set the Diatomite site's location string
        address -- address string
        latitude -- geographical coordinates latitude string
        longitude -- geographical coordinates longitude string
        coord_type -- geographical coordinates type"""

        self._location.set_address(address)
        self._location.set_latitude(latitude)
        self._location.set_longitude(longitude)
        self._location.set_coordinates_type(coord_type)

    def set_type(self, loc_type):
        """Set the Diatomite site's type string
        loc_type -- a string"""

        self._type = loc_type

    def get_id(self):
        """Return this site's id"""

        return self._id

    def set_probes(self, probes_conf, site_conf):
        """Set the probe info
        probes_conf -- a dictionary of probe configurations
        site_conf -- a dictionary with the site's configuration
        """
        self._probes = Probes(probes_conf, site_conf, self)

    def start(self):
        """Start this object and it's children"""
        self._probes.start()

    def stop(self):
        """Stop this object and it's children"""
        self._probes.stop()


class DiatomiteProbe(object):
    """Define a diatomite probe.
    A diatomite probe pertains to a DiatomiteSite.
    A diatomite probe has one or more radio sources
    """

    def __init__(self, conf=None, full_conf=None, dia_site=None):
        """Configure the Probe
        conf -- a dictionary with a valid probe configuration
        full_conf -- a dictionary with the full configuration
            received by diatomite
        """

        self._id = ''
        self._site = DiatomiteSite()
        self._radio_sources = None
        self._radio_source_sp_handle = []

        self._log_dir_path = None
        self._log_level = logging.WARNING
        self._tap_dir_path = None

        self._api_svc = None
        self._api_svc_input_pipe = None
        self._api_svc_output_pipe = None

        # pipe inputs for each radio source
        # index is the radio source ID
        self._source_inputs = {}

        # pipe outputs for each radio source
        # index is the radio source ID
        self._source_outputs = {}

        # output queue for all radio sources
        self._source_output_queue = Queue()

        if dia_site is not None:
            self.set_site(dia_site)

        if conf is not None and full_conf is not None:
            # read configuration
            self.configure(conf, full_conf)

    def configure(self, conf, full_conf):
        """Configure the Probe
        conf -- a dictionary with a valid probe configuration
        full_conf -- a dictionary with the full configuration
            received by diatomite
        """

        self.set_log_dir_path(conf['logging']['dir_path'])
        self.set_log_level(conf['logging']['log_level'])
        self._configure_logging()

        self.set_id(conf['id'])

        self.set_tap_dir_path(conf['tap_dir_path'])

        self.set_radio_sources(conf['RadioSources'])

        self.configure_api_srv(conf, full_conf)

        # TODO:this willl need to be moved to a proper start phase
        self.start_api_srv()

    def _configure_logging(self):
        """Configure log output for this probe"""

        log_file_path = os.path.join(self.get_log_dir_path() + os.path.sep +
                                     'diatomite.log')

        lfh = logging.FileHandler(log_file_path)
        lformatter = logging.Formatter('%(asctime)s - %(name)s'
                                       ' - %(levelname)s - %(message)s')
        lformatter = logging.Formatter('%(asctime)s - %(filename)s:%(lineno)s '
                                       ' - %(funcName)s - %(levelname)s'
                                       ' - %(message)s')

        lfh.setFormatter(lformatter)
        current_logger = logging.getLogger()
        current_logger.setLevel(self.get_log_level())

        # remove previous lg handlers
        for hdlr in current_logger.handlers[:]:
            current_logger.removeHandler(hdlr)

        # setup new handler
        current_logger.addHandler(lfh)

    def start_api_srv(self):
        """start the api service"""
        self._api_svc.start()

    def configure_api_srv(self, conf, full_conf):
        """Start the api server for this probe
        conf -- a dictionary with a valid probe configuration
        full_conf -- a dictionary with the full configuration
            received by diatomite"""

        self._api_svc_input_pipe = Queue()
        self._api_svc_output_pipe = Queue()

        self._api_svc = diatomite_api.ApiSvc(conf, full_conf,
                                             self._api_svc_input_pipe,
                                             self._api_svc_output_pipe)

    def set_radio_sources(self, radio_sources_dict):
        """set the radio sources info
        radio_sources_dict -- a dictionaty of radio sources configurations"""
        # pass radio sources configuration, output queue, and paths
        self._radio_sources = radiosource.RadioSources(radio_sources_dict,
                                                       self._source_output_queue,
                                                       self.get_log_dir_path(),
                                                       self.get_tap_dir_path())

    def set_id(self, pid):
        """Set the id of this probe
        pid -- id of the probe"""
        self._id = pid

    def set_site(self, site):
        """Set the site object to which this probe belongs to
        site -- a DiatomiteSite object"""

        if isinstance(site, DiatomiteSite):
            self._site = site
        else:
            msg = 'Invalid site type, must be DiatomiteSite.'
            raise TypeError(msg)

    def set_log_dir_path(self, log_dir_path):
        """Set the probe's log path
        log_dir_path - path to the logs directory"""

        if log_dir_path is None:
            msg = 'Tap path not set will log to current dir.'
            self._log_dir_path = os.getcwd()

        # check if path is absolute
        if os.path.isabs(log_dir_path):
            self._log_dir_path = log_dir_path
            msg = 'Tap directory is absolute'
            logging.debug(msg)
        else:
            # path is relative

            # check if it is to be the current directory
            if log_dir_path in ['.', './']:
                self._log_dir_path = os.getcwd()
                msg = 'Tap directory is cwd'
                logging.debug(msg)
            else:
                self._log_dir_path = os.path.join(os.getcwd(), log_dir_path)

    def set_tap_dir_path(self, tap_dir):
        """Set the probe's tap directory
        tap_dir - path to the tap directory"""

        self._tap_dir_path = tap_dir

    def get_id(self):
        """Return the id of this probe"""
        return self._id

    def get_site(self):
        """Return the parent site object"""
        return self._site

    def get_log_dir_path(self):
        """Return the probe's log directory path"""

        return self._log_dir_path

    def set_log_level(self, level):
        """Set the log level
        level -- a string with the log level"""

        if level.upper() == "DEBUG":
            self._log_level = logging.DEBUG
            msg = 'logging level will be set to {ll}.'.format(ll=level.upper())
            logging.info(msg)
        elif level.upper() == "INFO":
            self._log_level = logging.INFO
            msg = 'logging level will be set to {ll}.'.format(ll=level.upper())
            logging.info(msg)
        elif level.upper() == "WARNING":
            self._log_level = logging.WARNING
            msg = 'logging level will be set to {ll}.'.format(ll=level.upper())
            logging.info(msg)
        elif level.upper() == "ERROR":
            self._log_level = logging.ERROR
            msg = 'logging level will be set to {ll}.'.format(ll=level.upper())
            logging.info(msg)
        elif level.upper() == "CRITICAL":
            self._log_level = logging.CRITICAL
            msg = 'logging level will be set to {ll}.'.format(ll=level.upper())
            logging.info(msg)
        else:
            msg = ('FATAL: configuration error, malformed log_level'
                   ' configuration:{ll}. Setting to WARNING').format(ll=level)
            logging.warning(msg)
            self._log_level = logging.WARNING

    def get_log_level(self):
        """Return the log level"""

        return self._log_level

    def get_tap_dir_path(self):
        """Return the probe's tap directory path"""

        return self._tap_dir_path

    def add_radio_source(self, conf):
        """Add a radio source to this probe's radio source list.
        conf -- a dictionary with a valid configuration"""

        # pass the output queue to the source

        try:
            self._radio_sources.append(conf)
        except radiosource.RadioSourceListIdNotUniqueError:
            msg = ('FATAL:Radio source id {rsid} already present on this'
                   ' Probe!!').format(rsid=conf['id'].get_identifier())
            logging.error(msg)
            raise

        msg = ("RadioSource {i} added to probe's radio source"
               " list").format(i=conf['id'])
        logging.debug(msg)

    def start_sources(self):
        """Start all the sources"""

        self._radio_sources.start()
        self._source_inputs = self._radio_sources.get_source_input_pipes()
        self._source_outputs = self._radio_sources.get_source_output_pipes()

    def _monitor_radio_sources(self):
        """Monitor radio source output queue
        Gets messages from the monitor source output queue
        and processes them."""

        while True:

            # get stuff from queue
            # messages should be in a format:
            # {radio source id}:{listener_id}:....
            # only radio source id is mandatory
            queue_item = self._source_output_queue.get()

            msg = "got a queue item:{qi}".format(qi=queue_item)
            logging.debug(msg)

            if isinstance(queue_item, dia_aux.DiaRadioReceiverMsg):
                msg = ('Received message from a'
                       ' Radio Receiver:{m}').format(m=queue_item.get_json())

                # package message onto a DiaProbeMsg
                prb_id = self.get_id()
                sig_type = queue_item.get_msg_type()
                payload = queue_item
                new_p_msg = dia_aux.DiaProbeMsg(sig_type, prb_id, payload)

                # package message onto a SiteProbeMSg
                site_id = self.get_site().get_id()

                sig_type = queue_item.get_msg_type()
                payload = new_p_msg
                new_msg = dia_aux.DiaSiteMsg(sig_type, site_id, payload)

                msg = ('Site {si} sending {msg}'
                       ' message:{m}').format(si=site_id,
                                              msg=sig_type,
                                              m=new_msg.get_json())
                logging.debug(msg)

                # send the message to the API server
                self.send_data_to_api(new_msg)

    def send_data_to_api(self, data):
        """Sends data to the API server.
        data -- data to send"""

        if isinstance(data, dia_aux.DiaSiteMsg):
            self._api_svc_input_pipe.put(data)
            msg = 'sending data to parent:{d}'.format(d=data)
            logging.debug(msg)

    def stop_sources(self):
        """stop all the sources"""
        pass
        # TODO: add code to stop all radio sources

    def start(self):
        """Start the object and it's children"""
        # TODO: add remaining code to start
        self._radio_sources.start()

        self._monitor_radio_sources()

    def stop(self):
        """Stop the object and it's children"""
        # TODO: add remaining code to stop
        self._radio_sources.stop()


class DiaConfParser(object):
    """Handles parsing of configurations"""

    _has_valid_conf_file = False
    _initial_conf = {}
    _good_conf = {}

    def read_conf_file(self, filep):
        """Read configuration file, abstracted to allow various formats
        filep -- configuration file path"""

        if filep is None:
            msg = 'Config file not specified'
            raise DiaConfParserError(msg)

        msg = 'Reading config file:{cf}'.format(cf=filep)
        logging.debug(msg)

        # check if the file can be opened
        try:
            conf_file_h = open(filep, 'r')
        except IOError, exc:
            msg = ('Unable to open file {f}'
                   ' with: {m}').format(f=filep, m=str(exc))
            logging.error(msg)
            msg = sys.exc_info()
            logging.error(msg)
            raise

        # try and read as yaml config
        try:
            self.read_yaml_conf_file(conf_file_h)
        except yaml.YAMLError:
            pass
        else:
            try:
                self._good_conf = self._process_config(self._initial_conf)
            except DiaConfParserError, exc:
                msg = ('Unable to read a valid configuration'
                       ': {m}').format(m=str(exc))
                logging.error(msg)
                raise
            _has_valid_conf_file = True

        # other configuration files would be read here.

        # if we don't have a valid config file, raise an exception
        if not _has_valid_conf_file:
            msg = 'Unable to get a meaningful configuration'
            raise DiaConfParserError(msg)

    def _process_config_log(self, conf):
        """Check log configuration for completeness, add default values.
        conf -- a dict of configurations
        Returns a dict with logging configurations"""

        if 'dir_path' not in conf:
            conf['dir_path'] = ''

        if 'log_level' not in conf:
            conf['log_level'] = 'ERROR'
        else:
            if conf['log_level'].upper() not in ("DEBUG", "INFO", "WARNING",
                                                 "ERROR", "CRITICAL"):
                msg = ('FATAL: configuration error, malformed log_level'
                       ' configuration:{ll}.'
                       ' Setting to WARNING').format(ll=conf['log_level'])
                logging.warning(msg)
                conf['log_level'] = 'WARNING'

        return conf

    def _process_config(self, conf):
        """Check configuration file for completeness, add default values.
        conf -- a dict of configurations"""

        # check if 'site' section exists
        try:
            sites = conf['sites']
        except KeyError:
            msg = ('FATAL: configuration error, missing site definition'
                   ' section')
            raise DiaConfParserError(msg)

        # check if any sites are defined
        if not sites:
            msg = 'FATAL: configuration error, no sites configured'
            raise DiaConfParserError(msg)

        # process this site
        for s_key in sites:

            this_site = sites[s_key]
            # add the listener id to the data
            this_site['id'] = s_key

            # check for mandatory site fields
            if 'location' not in this_site:
                msg = ('FATAL: configuration error, missing site LOCATION '
                       'definition')
                raise DiaConfParserError(msg)
            if this_site['location'] == '':
                msg = ('FATAL: configuration error, missing site LOCATION '
                       'definition')
                raise DiaConfParserError(msg)
            # check for optional site fields and
            # fill the up with appropriate values if those are missing
            if 'address' not in this_site:
                this_site['address'] = 'N/A'
            if 'type' not in this_site:
                this_site['type'] = 'N/A'
            if 'longitude' not in this_site:
                this_site['longitude'] = 'N/A'
            if 'latitude' not in this_site:
                this_site['latitude'] = 'N/A'
            if 'coord_type' not in this_site:
                this_site['coord_type'] = 'N/A'

            # check if the 'probe' section exists
            try:
                probes = this_site['probes']
            except KeyError:
                msg = ('FATAL: configuration error, missing probe definition'
                       'section')
                raise DiaConfParserError(msg)

            # check if any probes are defined
            if not probes:
                msg = 'FATAL: configuration error, no probes configured'
                raise DiaConfParserError(msg)

            for p_key in probes:

                this_probe = probes[p_key]
                # add the listener id to the data
                this_probe['id'] = p_key

                # check for mandatory probe fields
                # note: currently no mandatory fields for the probe

                # check for optional site fields and
                # fill the up with appropriate values if those are missing
                if 'tap_dir_path' not in this_probe:
                    this_probe['tap_dir_path'] = ''

                if 'logging' not in this_probe:
                    new_log_conf = {
                        'log_level': "INFO",
                        'dir_path': "log",
                        }
                else:
                    new_log_conf = self._process_config_log(this_probe['logging'])

                this_probe['logging'] = new_log_conf

                # check for 'RadioSources' section
                try:
                    radio_sources = this_probe['RadioSources']
                except KeyError:
                    msg = ('FATAL: configuration error, missing RadioSources '
                           'section')
                    raise DiaConfParserError(msg)

                # check if there are radio sources
                if not radio_sources:
                    msg = ('FATAL: configuration error, empty RadioSources'
                           'section')
                    raise DiaConfParserError(msg)

                # check each radio source
                for rs_key in radio_sources:

                    this_r_source = radio_sources[rs_key]
                    # add radio source id to the data
                    this_r_source['id'] = rs_key

                    # define mandatory fields
                    if 'type' not in this_r_source:
                        msg = ('FATAL: configuration error, missing radio'
                               ' source Type definition')
                        raise DiaConfParserError(msg)
                    if this_r_source['type'] == '':
                        msg = ('FATAL: configuration error, missing'
                               ' radio source Type definition')
                        raise DiaConfParserError(msg)

                    # test if frequency is defined
                    if 'frequency' not in this_r_source:
                        msg = ('FATAL: configuration error, missing'
                               ' radio source Frequency definition')
                        raise DiaConfParserError(msg)
                    try:
                        # convert from string to a float
                        rs_freq = float(this_r_source['frequency'])
                    except ValueError:
                        msg = ('FATAL: configuration error, malformed'
                               ' radio source Frequency definition')
                        raise DiaConfParserError(msg)
                    else:
                        if not rs_freq.is_integer():
                            # check if number is integer
                            msg = ('FATAL: configuration error, malformed'
                                   ' radio source Frequency definition')
                            raise DiaConfParserError(msg)
                        else:
                            this_r_source['frequency'] = rs_freq
                            
                    # define optional fields
                    if 'conf' not in this_r_source:
                        this_r_source['conf'] = ''
                    if 'audio_output' not in this_r_source:
                        this_r_source['audio_output'] = False
                    else:
                        if this_r_source['audio_output'].lower() not in ('false', 'true'):
                            msg = ('FATAL: configuration error, malformed'
                                   ' radio source audio_output option')
                            raise DiaConfParserError(msg)
                        else:
                            if this_r_source['audio_output'].lower() == 'false':
                                this_r_source['audio_output'] = False
                            elif this_r_source['audio_output'].lower() == 'true':
                                this_r_source['audio_output'] = True

                    if 'freq_analyzer_tap' not in this_r_source:
                        this_r_source['freq_analyzer_tap'] = False
                    else:
                        if this_r_source['freq_analyzer_tap'].lower() not in ('false', 'true'):
                            msg = ('FATAL: configuration error, malformed'
                                   ' source freq_analyzer_tap option')
                            raise DiaConfParserError(msg)
                        else:
                            if this_r_source['freq_analyzer_tap'].lower() == 'false':
                                this_r_source['freq_analyzer_tap'] = False
                            elif this_r_source['freq_analyzer_tap'].lower() == 'true':
                                this_r_source['freq_analyzer_tap'] = True

                    # check if there are listeners
                    try:
                        listeners = this_r_source['listeners']
                    except KeyError:
                        msg = ('FATAL: configuration error, missing Listeners '
                               'section for radio'
                               ' source {rs}').format(rs=rs_key)
                        raise DiaConfParserError(msg)
                    if not listeners:
                        msg = ('FATAL: configuration error, missing listeners'
                               'section for radio'
                               ' source {rs}').format(rs=rs_key)
                        raise DiaConfParserError(msg)

                    # check each listener
                    for l_key in listeners:

                        this_listener = listeners[l_key]
                        # add the listener id to the data
                        this_listener['id'] = l_key

                        # define mandatory fields
                        if 'frequency' not in this_listener:
                            msg = ('FATAL: configuration error, missing'
                                   ' listener Frequency definition')
                            raise DiaConfParserError(msg)
                        try:
                            # convert from string to a float
                            l_freq = float(this_listener['frequency'])
                        except ValueError:
                            msg = ('FATAL: configuration error, malformed'
                                   ' listener Frequency definition')
                            raise DiaConfParserError(msg)
                        else:
                            if not l_freq.is_integer():
                                # check if number is integer
                                msg = ('FATAL: configuration error, malformed'
                                   ' listener Frequency definition')
                                raise DiaConfParserError(msg)
                            else:
                                this_listener['frequency'] = l_freq

                        if 'bandwidth' not in this_listener:
                            msg = ('FATAL: configuration error, missing'
                                   ' listener bandwidth definition')
                            raise DiaConfParserError(msg)
                        try:
                            # convert from string to a float
                            l_bw = float(this_listener['bandwidth'])
                        except ValueError:
                            msg = ('FATAL: configuration error, malformed'
                                   ' listener bandwidth definition')
                            raise DiaConfParserError(msg)
                        else:
                            if not l_bw.is_integer():
                                # check if number is integer
                                msg = ('FATAL: configuration error, malformed'
                                       ' listener bandwidth definition')

                                raise DiaConfParserError(msg)
                            else:
                                this_listener['bandwidth'] = l_bw

                        if 'level_threshold' not in this_listener:
                            msg = ('FATAL: configuration error, missing'
                                   ' listener level_threshold definition')
                            raise DiaConfParserError(msg)
                        try:
                            # convert from string to a float
                            l_threshold = float(this_listener['level_threshold'])
                        except ValueError:
                            msg = ('FATAL: configuration error, malformed'
                                   'listener level_threshold definition')
                            raise DiaConfParserError(msg)
                        else:
                            if not l_threshold.is_integer():
                                # check if number is integer
                                msg = ('FATAL: configuration error, malformed'
                                       'listener level_threshold definition')
                                raise DiaConfParserError(msg)
                            else:
                                this_listener['level_threshold'] = l_threshold                   

                        # define optional fields
                        if 'modulation' not in this_listener:
                            this_listener['modulation'] = ''
                        if (this_listener['modulation'].lower() not in 
                            dia_aux.BaseDemodulator.subclasses.keys()):
                    
                            this_listener['modulation'] = ''
                            msg = ('FATAL: configuration error, malformed'
                                   ' listener modulation option')
                            raise DiaConfParserError(msg)

                        if 'audio_output' not in this_listener:
                            this_listener['audio_output'] = False
                        else:
                            if this_listener['audio_output'].lower() not in ('false', 'true'):
                                msg = ('FATAL: configuration error, malformed'
                                       ' listener audio_output option')
                                raise DiaConfParserError(msg)
                            else:
                                if this_listener['audio_output'].lower() == 'false':
                                    this_listener['audio_output'] = False
                                elif this_listener['audio_output'].lower() == 'true':
                                    this_listener['audio_output'] = True
                        # check if the radio source is enabled
                        if this_listener['audio_output'] and not this_r_source['audio_output']:
                            this_listener['audio_output'] = False
                            msg = ('Radio source audio output is disabled, '
                                   ' and listener audio output requested.'
                                   ' Disabling audio output for the listener.')
                            logging.info(msg)
                        # check if modulation is configured
                        if this_listener['audio_output'] and this_listener['modulation'] == '':
                            this_listener['audio_output'] = False
                            msg = ('Listener modulation not defined, '
                                   ' and listener audio output requested.'
                                   ' Disabling audio output for the listener.')
                            logging.info(msg)

                        if 'freq_analyzer_tap' not in this_listener:
                            this_listener['freq_analyzer_tap'] = False
                        else:
                            if this_listener['freq_analyzer_tap'].lower() not in ('false', 'true'):
                                msg = ('FATAL: configuration error, malformed'
                                       ' listener freq_analyzer_tap option')
                                raise DiaConfParserError(msg)
                            else:
                                if this_listener['freq_analyzer_tap'].lower() == 'false':
                                    this_listener['freq_analyzer_tap'] = False
                                elif this_listener['freq_analyzer_tap'].lower() == 'true':
                                    this_listener['freq_analyzer_tap'] = True

        # return configuration
        return conf

    def read_yaml_conf_file(self, conf_file_h):
        """Reads a yaml configuration file and converts to
        a dictionary
        conf_file_h -- handle for the configuration file"""

        try:
            self._initial_conf = yaml.safe_load(conf_file_h)

        except yaml.YAMLError, exc:
            msg = ('Unable to read yaml file {f}'
                   ' with: {m}').format(f=conf_file_h.path, m=str(exc))

            logging.error(msg)
            msg = sys.exc_info()
            logging.error(msg)
            raise

    def get_config(self):
        """Return a fully formed configuration file"""

        if self._good_conf:
            return self._good_conf
        else:
            msg = 'No valid configuration available'
            raise DiaConfParserError(msg)

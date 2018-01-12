#!/usr/bin/env python2
"""
    diatomite - Auxiliary classes for the diatomite system
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


import os
import logging as log
import threading
import exceptions
import errno
import sys
from string import ascii_letters, digits
import freqlistener
import radiosource
from Crypto.SelfTest.Random.test__UserFriendlyRNG import multiprocessing
import yaml
import collections

class FreqListenerListIdNotUniqueError(Exception):
    """Raised when a FreqListener with an already occurring id is added to a
    FreqlistenerList."""
    pass


class RadioSourceListIdNotUniqueError(Exception):
    """Raised when a RadioSource with an already occurring id is added to a
    RadioRecieverList."""
    pass


class BadIdError(Exception):
    """Raised when an object is passed an id with unacceptable
    characters."""
    pass

class DiaConfParserError(Exception):
    """Raised when unable to read a meaningfull configuration"""
    pass


class RadioSpectrum(object):
    """Defines limits for the radio spectrum."""

    # upper limit at 1 Thz
    _upper_rf_limit = 1000000000000
    # lower limit at 3 Khz
    _lower_rf_limit = 3000

    def get_upper_frequency(self):
        """Return the upper frequency of this spectrum."""
        return self._upper_rf_limit

    def get_lower_frequency(self):
        """Return the lower frequency of this spectrum."""
        return self._lower_rf_limit


class DataTap(object):
    """Define an object to stream text data onto a named pipe
    Will output to a previously created named pipe/file.
    If an error occurs while creating the named pipe (other than that the
    file already exists), tap output thread will not be started."""

    _tap_file_extension = '.tap'

    def __init__(self, tap_id):
        """Setup the tap and Create the named pipe.
        tap_id -- id to """

        self._set_id(tap_id)

        # init the directory as the current directory
        self._tap_dir_path = os.getcwd()

        # set the stop event for the thread
        self._tap_thread_stop = threading.Event()

        # set the update event for the thread
        self._tap_value_update = threading.Event()

        self._tap_value = ''

        # set a lock
        self._tap_lock = threading.RLock()

        # set the file name
        self._set_file()

        # create a named pipe, check
        try:
            os.mkfifo(self._get_file())
        except exceptions.OSError, exc:

            if exc.errno == errno.EEXIST:
                msg = ('Data Tap {id}, File already exists , Failed creating'
                       ' named pipe for fft tap'
                       ' with: {m}').format(id=self._get_id(), m=str(exc))
                log.error(msg)
                msg = sys.exc_info()
                log.warning(msg)
        except Exception, exc:
            msg = ('Data Tap {id}, Failed creating named pipe for fft tap'
                   ' with: {m}').format(id=self._get_id(), m=str(exc))
            log.error(msg)
            msg = sys.exc_info()
            log.error(msg)
            raise

        # set the tap update on it's own thread
        self._update_tap_thread = threading.Thread(target=self._output_value,
                                                   name=self._get_id(),
                                                   args=(self._tap_thread_stop,
                                                         self._tap_value_update))
        self._update_tap_thread.daemon = True
        self._update_tap_thread.start()

        msg = 'Data Tap {id} tap setup done.'.format(id=self._get_id())
        log.debug(msg)

    def _set_file(self):
        """Set the file name"""
        # setup file name and path
        self._tap_file_name = self._get_id() + self._tap_file_extension
        self._tap_file_path = os.path.join(self._tap_dir_path,
                                           self._tap_file_name)

    def _get_file(self):
        """Get the file name and path for the tap"""
        return self._tap_file_path

    def _set_id(self, ident):
        """Sets the Data tap id.
        Converts alphabetic characters to lower case.
        ident -- the id.
                        Acceptable characters: ASCII characters, numbers,
                        underscore, dash."""

        if ident == '':
            msg = 'Identity is empty'
            log.error(msg)
            raise BadIdError(msg)
        if all(character in ascii_letters+digits+'_'+'-'
               for character in ident):
            self._id = ident.lower()
            msg = 'id set to {i}'.format(i=ident.lower())
            log.debug(msg)
        else:
            msg = 'Frequency id contains can only contain AZaz09-_'
            log.error(msg)
            raise BadIdError(msg)

    def set_directory(self, path):
        """Set the directory where tap files should be written to.
        path -- full path to the directory"""
        pass
        # TODO: write the set_tap_dir_path

    def _get_id(self):
        """Returns the data tap id."""
        return self._id

    def stop(self):
        """Cleanup the live fft values tap.
        Will remove the tap file from the file system"""

        # stop the thread
        self._tap_thread_stop.set()
        # remove tap file
        os.remove(self._tap_file_path)

    def _output_value(self, stop_event, update_event):
        """Updates the values present on the tap"""

        while not stop_event.is_set():

            # wait for the update event
            update_event.wait()

            output = '{v}\n'.format(v=self._get_value())

            with open(self._tap_file_path, 'w', 0) as f_handle:

                msg = ('writing on tap {t}').format(t=self._get_id())
                log.debug(msg)

                try:
                    f_handle.writelines(output)
                except IOError, exc:
                    if exc.errno == errno.EPIPE:
                        msg = ('Broken pipe on tap {t} with:'
                               ' {m}').format(t=self._get_id(), m=str(exc))
                        log.debug(msg)
                        msg = sys.exc_info()
                        msg = ('Broken pipe on tap'
                               ' {t}').format(t=self._get_id())
                        log.warning(msg)
                    else:
                        msg = ('Error writing on on tap {t} with:'
                               ' {m}').format(t=self._get_id(), m=str(exc))
                        log.error(msg)
                        raise

    def update_value(self, value):
        """Updates the values present on the fft tap.
        value - value to update the tap (string)"""

        # update the value
        self._tap_lock.acquire()
        self._tap_value = value
        self._tap_lock.release()

        # signal the worker thread
        self._tap_value_update.set()

    def _get_value(self):
        """Get the value, with locking"""
        self._tap_lock.acquire()
        value = self._tap_value
        self._tap_lock.release()

        return value

class FreqListeners(object):
    """Class for collections of frequency listeners."""

    _freq_listener_dict = {}
    _tap_dir_path = None
    _radio_source = None


    def configure(self, conf, radio_source,tap_dir_path):
        """Configure the frequency listener collection
        conf -- a dictionary with a valid configuration
                (use DiaConfParser to obtain a valid config)
        radio_source -- this listener's radio source 
        tap_dir_path -- path where taps wil be created"""

        self.set_tap_dir_path(tap_dir_path)
        self._radio_source = radio_source

        # initialize each frequency listener
        for freq_listener_id in conf:
            
            self.append(conf[freq_listener_id])

    def set_log_dir_path(self, log_dir_path):
        """Set the freq listenr's log path
        log_dir_path - path to the logs directory"""

        self._log_dir_path = log_dir_path

    def set_out_queue(self, source_output_queue):
        """Set output queue to be used by frequency listener
        source_output_queue -- a multiprocessing queue"""

        self._source_output_queue = source_output_queue

    def set_tap_dir_path(self, tap_dir):
        """Set the probe's tap directory
        tap_dir - path to the tap directory"""

        self._tap_dir_path = tap_dir

    def get_out_queue(self):
        """Return the queue to be used by frequency listener"""

        return self._source_output_queue

    def get_log_dir_path(self):
        """Return the probe's log directory path"""

        return self._log_dir_path
  
    def get_tap_dir_path(self):
        """Return the probe's tap directoty path"""

        return self._tap_dir_path

    def start(self):
        """Start this object and it's children"""
        for freq_listener_id in self._freq_listener_dict:
            self._freq_listener_dict[freq_listener_id].start()

    def stop(self):
        """Stop this object and it's children"""
        for freq_listener_id in self._freq_listener_dict:
            self._freq_listener_dict[freq_listener_id].stop()


    def append(self, conf):
        """Append a new frequency listener
        conf -- a dictionary with a valid configuration
            (use DiaConfParser to obtain a valid config)"""
        
        f_listener_id = conf['id']
        
        if f_listener_id in self._freq_listener_dict.keys():
            msg = 'Listener {id} already present'.format(id=f_listener_id)
            raise RadioSourceListIdNotUniqueError(msg)
        
        listener = freqlistener.FreqListener(conf, self._radio_source,
                                             self.get_tap_dir_path())
        self._freq_listener_dict[f_listener_id] = listener


# class FreqListenerList(list):
#     """Define a list of Frequency listener objects."""
# 
#     def append(self, listener):
#         """add a listener to the list.
#         listener -- FreqListener
#         append will not allow duplicate ids to be added."""
# 
#         current_id_list = self.get_listener_id_list()
# 
#         # Checking of type must occur before checking of id
#         if not isinstance(listener, freqlistener.FreqListener):
#             msg = 'item is not of type FreqListener'
#             log.error(msg)
#             raise TypeError(msg)
# 
#         # obtain the listener id
#         id_to_add = listener.get_id()
# 
#         if id_to_add in current_id_list:
#             msg = "Frequency Listener's id is not unique"
#             log.error(msg)
#             raise FreqListenerListIdNotUniqueError(msg)
# 
#         super(FreqListenerList, self).append(listener)
#         msg = 'FreqListener {i} added to list'.format(i=listener)
#         log.debug(msg)
# 
#     def get_listener_id_list(self):
#         """Obtain list of ids for all the members of the list"""
#         res = []
# 
#         for listener in self:
#             fid = listener.get_id()
#             res.append(fid)
# 
#         msg = 'Listener_id_list:{i}'.format(i=res)
#         log.debug(msg)
# 
#         return res
# 
#     def get_listener_by_id(self, lid):
#         """Return a listener by id
#         lid -- the id to search for"""
# 
#         res = None
# 
#         for listener in self:
#             this_id = listener.get_id()
#             if this_id == lid:
#                 return listener
# 
#         return res

class RadioSources(object):
    """Class for collections of radio sources."""

    _radio_source_dict = {}
    _log_dir_path = None
    _tap_dir_path = None
    _source_output_queue = None


    def configure(self,conf, out_queue, log_dir_path, tap_dir_path):
        """Configure the radio sources collection
        conf -- a dictionary with a valid configuration
                (use DiaConfParser to obtain a valid config)
        out_queue -- queue to be used as output for radio sources
        log_dir_path -- path where logs will be written
        tap_dir_path -- path where taps wil be created"""

        self.set_log_dir_path(log_dir_path)
        self.set_tap_dir_path(tap_dir_path)
        self.set_out_queue(out_queue)

        # initialize each radio source
        for radio_source_id in conf:
            
            self.append(conf[radio_source_id])

    def set_log_dir_path(self, log_dir_path):
        """Set the probe's log path
        log_dir_path - path to the logs directory"""

        self._log_dir_path = log_dir_path

    def set_out_queue(self, source_output_queue):
        """Set output queue to be used by radio sources
        source_output_queue -- a multiprocessing queue"""

        self._source_output_queue = source_output_queue

    def set_tap_dir_path(self, tap_dir):
        """Set the probe's tap directory
        tap_dir - path to the tap directory"""

        self._tap_dir_path = tap_dir

    def get_out_queue(self):
        """Return the queue to be used by radio sources"""

        return self._source_output_queue

    def get_log_dir_path(self):
        """Return the probe's log directory path"""

        return self._log_dir_path
  
    def get_tap_dir_path(self):
        """Return the probe's tap directoty path"""

        return self._tap_dir_path

    def start(self):
        """Start this object and it's children"""
        for radio_source_id in self._radio_source_dict:
            self._radio_source_dict[radio_source_id].start()

    def stop(self):
        """Stop this object and it's children"""
        for radio_source_id in self._radio_source_dict:
            self._radio_source_dict[radio_source_id].stop()


    def append(self, conf):
        """Append a new radio source
        conf -- a dictionary with a valid configuration
            (use DiaConfParser to obtain a valid config)"""
        
        r_source_type = conf['type']
        r_source_id = conf['id']
        
        if r_source_id in self._radio_source_dict.keys():
            msg = 'Radio Source {id} Already present'.format(id=r_source_id)
            raise RadioSourceListIdNotUniqueError(msg)
        
        # check if the radio source type is valid and set the class accordingly
        supported_devs = radiosource.RadioSourceSupportedDevs()
        try:
            radio_source_class = supported_devs.get_dev_class(r_source_type)
        except radiosource.RadioSourceSupportedDevsError:
            raise
        
        # set the class to be use:
        msg = 'Will use radio source class "{rsc}"'.format(rsc=radio_source_class)
        log.debug(msg)
        rs_class_ = getattr(radiosource, radio_source_class)
        r_source = rs_class_(conf,
                                           self.get_out_queue(),
                                           self.get_log_dir_path(),
                                           self.get_tap_dir_path())
        self._radio_source_dict[r_source_id] = r_source

# class RadioSourceList(list):
#     """Define a list of RadioSource objects."""
# 
#     def append(self, radio_source):
#         """add a radio source to the list
#         radio_source - a RadioSource to add to the list.
#         append will not allow duplicate ids to be added."""
# 
#         current_id_list = self.get_radio_source_id_list()
# 
#         if not isinstance(radio_source, radiosource.RadioSource):
#             msg = 'item is not of type RadioSource'
#             log.error(msg)
#             raise TypeError(msg)
# 
#         # obtain the listener id
#         id_to_add = radio_source.get_id()
# 
#         if id_to_add in current_id_list:
#             msg = "Radio source's id is not unique"
#             log.error(msg)
#             raise RadioSourceListIdNotUniqueError(msg)
# 
#         super(RadioSourceList, self).append(radio_source)
#         msg = 'RadioSource {i} added to list'.format(i=radio_source)
#         log.debug(msg)
# 
#     def get_radio_source_id_list(self):
#         """Obtain list of ids for all the members of the list"""
#         res = []
# 
#         for radio_source in self:
#             fid = radio_source.get_id()
#             res.append(fid)
# 
#         return res
# 
#     def get_radio_source_by_id(self, rsid):
#         """Return a radio source by id
#         rsid -- the id to search for"""
# 
#         res = None
# 
#         for radio_source in self:
#             this_id = radio_source.get_id()
#             if this_id == rsid:
#                 return radio_source
#         return res

class Location(object):
    """Define a location."""

    _address = ''
    _longitude = ''
    _latitude = ''
    _coord_type = ''

    def set_address(self, address):
        """Set the address value
        address -- a string"""
        
        self._address = address

    def set_longitude(self, longitude):
        """Set the longitude value
        longitude -- geographical coordinates longitude string"""
        
        self._longitude = longitude
        
    def set_latitude(self, latitude):
        """Set the longitude value
        latitude -- geographical coordinates latitude string"""
        
        self._latitude = latitude
        
    def set_coordinates_type(self, coord_type):
        """Set the coordinates type
        coord_type -- geographical coordinates type"""
        
        self._coord_type = coord_type

class Probes(object):
    """Object for collections of probe."""
    
    _probe_dict = {}

    def __init__(self, conf=None):
        if conf is not None:
            # read configuration
            self.configure(conf)    

    def configure(self,conf):
        """Configure the Probes collection
        conf -- a dictionary with a valid configuration
                (use DiaConfParser to obtain a valid config)"""

        # initialize each probe
        # although there should only be one probe
        for probe_id in conf:        
            this_probe = DiatomiteProbe(conf[probe_id])
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
    to be aware of all diatomite probes existing other than the one being 
    executed by the running process."""

    _id = None

    # Location for this site
    _location = Location()
    
    _type = None
    _probes = Probes()

    # Site name
    site_name = ''

    def __init__(self, conf=None):

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
        
        self.set_probes(site_conf['probes'])
        
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
        
    def set_probes(self, probe_dict):
        """Set the probe info
        probe_dict -- a dictionary of probe configurations"""
        
        self._probes.configure(probe_dict)

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

    _id = ''
    _site = DiatomiteSite()
    _radio_sources = RadioSources()
    #    TODO: AQUI, mudar de radio RadioSourceList pra RadioSources !!!
#     _radio_source_list = RadioSourceList()
    _radio_source_sp_handle = []
    
    _log_dir_path = None
    _tap_dir_path = None

    # pipe inputs for each radio source
    # index is the radio source ID
    _source_inputs = {}

    # pipe outputs for each radio source
    # index is the radio source ID
    _source_outputs = {}

    manager = multiprocessing.Manager()
    _source_output_queue = manager.Queue()

    def start(self):
        """Start the object and it's children"""
        # TODO: add remaining code to start
        self._radio_sources.start()

    def stop(self):
        """Stop the object and it's children"""
        # TODO: add remaining code to stop
        self._radio_sources.stop()

# class Probe(object):
#     """Defines a diatomite probe"""
# 
#     _id = None
#     _log_dir_path = None
#     _tap_dir_path = None
#     
#     def __init__(self, conf=None):
# 
#         if conf is not None:
#             # read configuration
#             self.configure(conf)
# 
#     def configure(self,conf):
#         """Configure the Probe
#         conf -- a dictionary with a valid configuration
#                 (use DiaConfParser to obtain a valid config)"""
#         
#         self.set_id(conf['id'])
#         self.set_log_dir_path(conf['log_dir_path'])
#         self.set_tap_dir_path(conf['tap_dir_path'])
# 
#         # TODO: set the radiosources !!!
# #         AQUI
#         print '--------'
#         print conf['RadioSources']
# 
#     def set_id(self, site_id):
#         """Set the site's id
#         site_id - id string"""
#         
#         self._id = site_id
#         
#     def set_log_dir_path(self, log_dir_path):
#         """Set the site's id
#         log_dir_path - path to the logs directory"""
#         
#         self._log_dir_path = log_dir_path
#         
#     def set_tap_dir_path(self, tap_dir):
#         """Set the site's id
#         tap_dir - path to the tap directory"""
#         
#         self._tap_dir_path = tap_dir

    def __init__(self, conf=None):

        if conf is not None:
            # read configuration
            self.configure(conf)

    def configure(self,conf):
        """Configure the Probe
        conf -- a dictionary with a valid configuration
                (use DiaConfParser to obtain a valid config)"""

        self.set_id(conf['id'])
        self.set_log_dir_path(conf['log_dir_path'])
        self.set_tap_dir_path(conf['tap_dir_path'])
        
        self.set_radio_sources(conf['RadioSources'])

    def set_radio_sources(self, radio_sources_dict):
        """set the radio sources info
        radio_sources_dict -- a dictionaty if radio sources configurations"""
        
        # pass radio sources configuration, output queue, and paths
        self._radio_sources.configure(radio_sources_dict, 
                                      self._source_output_queue,
                                      self.get_log_dir_path(),
                                      self.get_tap_dir_path())

    def set_id(self, pid):
        """Set the id of this probe
        pid -- id of the probe"""
        self._id = pid

    def set_log_dir_path(self, log_dir_path):
        """Set the probe's log path
        log_dir_path - path to the logs directory"""
         
        self._log_dir_path = log_dir_path
         
    def set_tap_dir_path(self, tap_dir):
        """Set the probe's tap directory
        tap_dir - path to the tap directory"""

        self._tap_dir_path = tap_dir


    def get_id(self):
        """Return the id of this probe"""

        return self._id

    def get_log_dir_path(self):
        """Return the probe's log directory path"""
        
        return self._log_dir_path
  
    def get_tap_dir_path(self):
        """Return the probe's tap directoty path"""
        
        return self._tap_dir_path

    def add_radio_source(self, conf):
        """Add a radio source to this probe's radio source list.
        conf -- a dictionary with a valid configuration"""

        # pass the output queue to the source

        try:
            self._radio_source_list.append(conf)
        except RadioSourceListIdNotUniqueError:
            msg = ('FATAL:Radio source id {rsid} already present on this'
                   ' Probe!!').format(rsid=conf['id'].get_identifier())
            log.error(msg)
            raise

        msg = ("RadioSource {i} added to probe's radio source"
               " list").format(i=conf['id'])
        log.debug(msg)

    def start_sources(self):
        """Start all the sources"""

        _source_outputs2 = {}

        # start the radio source subprocesses and get handles
        for radio_source in self._radio_source_list:
            # start
            radio_source.start()
            radio_source_id = radio_source.get_id()
            self._source_inputs[radio_source_id] = radio_source.get_input_pipe()
            self._source_outputs[radio_source_id] = radio_source.get_output_pipe()
            self._radio_source_sp_handle.append(radio_source.get_subprocess())

            _source_outputs2[radio_source_id] = self._source_outputs[radio_source_id]

        # listen on the pipes
        input_pipe_list = list(self._source_inputs.values())

        self._monitor_radio_sources()


    def _monitor_radio_sources(self):
        """Monitor radio source output queue
        Gets messages from the monitor source output queue and processes them."""

        while True:

            # get stuff from queue
            # messages should be in a format:
            # {radio source id}:{listener_id}:....
            # only radio source id is mandatory
            queue_item = self._source_output_queue.get()

            msg = "got a queue item:{qi}".format(qi=queue_item)
            log.debug(msg)

            msg_items = queue_item.split(':')
            msg_item_len = len(msg_items)

            if msg_item_len == 1:
                # only got the id of the radio source
                # shouldn't happen

                msg = ('Received message in queue that is malformed:'
                       ' {data}').format(data=msg_items[0])

                log.warning(msg)
            elif msg_item_len > 1:
                # got a message from the radio source

                # check if it is a known radio source
                if msg_items[0] in self._radio_source_list.get_radio_source_id_list():

                    rid = msg_items[0]

                    # check if the message is from a frequency listener on the source
                    rsource = self._radio_source_list.get_radio_source_by_id(rid)
                    if msg_items[1] in rsource.get_listener_id_list():

                        lid = msg_items[1]
                        msg = ('Received message from radio source {rid}:'
                               'Listener {lid}: data:'
                               '{data}').format(rid=rid,
                                                lid=lid,
                                                data=msg_items[2:])
                        log.debug(msg)

                        # check if is a know msg tag from a receiver
                        listener_msg_tags = ['SIG_STATUS']
                        if msg_items[2] in listener_msg_tags:
                            if msg_items[2] == 'SIG_STATUS':

                                sig_state = msg_items[3]
                                sig_level = msg_items[4]
                                msg = ('Received message from radio source'
                                       ' {rid}, Listener {lid}: SIGNAL {state}'
                                       ', level:{lvl} DBm').format(rid=rid,
                                                                   lid=lid,
                                                                   state=sig_state,
                                                                   lvl=sig_level)
                                log.debug(msg)

                                # TODO: send this to persistent data/API

                        else:
                            # unknown message from listener
                            msg = ('Received unknown message from source {rid},'
                                   ' Listener {lid}: data:'
                                   '{data}').format(rid=rid,
                                                    lid=lid,
                                                    data=msg_items[3:])
                            log.warning(msg)
                    else:
                        # message is not from a listener
                        radio_receiver_msg_tags = []

                        # check if is a know msg tag from the receiver
                        if msg_items[1] in radio_receiver_msg_tags:

                            # process the message tag
                            pass
                        else:
                            msg = ('Received unknown message from source {rid}:'
                                   'data:'
                                   '{data}').format(rid=msg_items[0],
                                                    data=msg_items[1:])
                            log.warning(msg)

                else:
                    # not a know radio source
                    msg = ('Received a message from an unknown'
                           ' source:{data}').format(data=msg_items)
                    log.warning(msg)

    def stop_sources(self):
        """stop all the sources"""
        pass
        # TODO: add method to stop all radio sources
        
class DiaConfParser(object):
    """Handles parsing of configurations"""

    _has_valid_conf_file = False
    _initial_conf = {}
    _good_conf = {}

    def read_conf_file(self, filep):
        """Read configuration file, abstracted to allow various formats
        filep -- configuration file path"""
        
        if filep == None:
            msg = 'Config file not specified'
            raise DiaConfParserError(msg)
        
        msg = 'Reading config file:{cf}'.format(cf=filep)
        log.debug(msg)
        
        # check if the file can be opened
        try:
            conf_file_h = open(filep, 'r')
        except IOError, exc:
            msg = ('Unable to open file {f}'
                   ' with: {m}').format(f=filep, m=str(exc))
            log.error(msg)
            msg = sys.exc_info()
            log.error(msg)
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
                log.error(msg)
                raise
            _has_valid_conf_file = True



        # other configuration files would be read here.

        # if we don't have a valid config file, raise an exception
        if not _has_valid_conf_file:
            msg = 'Unable to get a meaningful configuration'
            raise DiaConfParserError(msg)
        
    def _process_config(self, conf):
        """Check configuration file for completeness, add default values."""

        # check if 'site' section exists
        try:
            sites= conf['sites']
        except KeyError:
            msg = ('FATAL: configuration error, missing site definition'
                   ' section')
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
                this_site['address']='N/A'
            if 'type' not in this_site:
                this_site['type']='N/A'
            if 'longitude' not in this_site:
                this_site['longitude']='N/A'
            if 'latitude' not in this_site:
                this_site['latitude']='N/A'
            if 'coord_type' not in this_site:
                this_site['coord_type']='N/A'               
      
            # check if the 'probe' section exists
            try:
                probes = this_site['probes']
            except KeyError:
                msg = ('FATAL: configuration error, missing probe definition'
                       'section')
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
                if 'log_dir_path' not in this_probe:
                    this_probe['log_dir_path'] = ''

                # check for 'RadioSources' section
                try:
                    radio_sources =  this_probe['RadioSources']
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
                        msg = ('FATAL: configuration error, missing radio source Type'
                               ' definition')
                        raise DiaConfParserError(msg)
                    if this_r_source['type'] == '':
                        msg = ('FATAL: configuration error, missing radio source Type'
                               ' definition')
                        raise DiaConfParserError(msg)
        
                    if 'frequency' not in this_r_source:
                        msg = ('FATAL: configuration error, missing radio source'
                               ' Frequency definition')
                        raise DiaConfParserError(msg)
                    if isinstance(this_r_source['frequency'], (int, long)):
                        msg = ('FATAL: configuration error, malformed radio source'
                               ' Frequency definition')
                        raise DiaConfParserError(msg)                
        
                    # define optional fields
                    if 'conf' not in this_r_source:
                        this_r_source['conf']=''
                    if 'audio_output' not in this_r_source:
                        this_r_source['audio_output'] = False
                    else:
                        if this_r_source['audio_output'].lower() not in ('false', 'true'):
                            msg = ('FATAL: configuration error, malformed radio source'
                                   ' audio_output option')
                            raise DiaConfParserError(msg)
                        else:
                            if this_r_source['audio_output'].lower() == 'false':
                                this_r_source['audio_output'] = False
                            elif this_r_source['audio_output'].lower() == 'true':
                                this_r_source['audio_output'] = True
                                                   
                    # check if there are listeners
                    try:
                        listeners = this_r_source['listeners']
                    except KeyError:
                        msg = ('FATAL: configuration error, missing Listeners '
                               'section for radio source {rs}').format(rs=rs_key)
                        raise DiaConfParserError(msg)
                    if not listeners:
                        msg = ('FATAL: configuration error, missing listeners'
                               'section for radio source {rs}').format(rs=rs_key)
                        raise DiaConfParserError(msg)
        
                    # check each listener
                    for l_key in listeners:
        
                        this_listener = listeners[l_key]
                        # add the listener id to the data
                        this_listener['id'] = l_key
        
                        # define mandatory fields
                        if 'frequency' not in this_listener:
                            msg = ('FATAL: configuration error, missing listener'
                                   ' Frequency definition')
                            raise DiaConfParserError(msg)
                        if isinstance(this_listener['frequency'], (int, long)):
                            msg = ('FATAL: configuration error, malformed listener'
                                   ' Frequency definition')
                            raise DiaConfParserError(msg)
                    
                        if 'bandwidth' not in this_listener:
                            msg = ('FATAL: configuration error, missing listener'
                                   ' bandwidth definition')
                            raise DiaConfParserError(msg)
                        if isinstance(this_listener['bandwidth'], (int, long)):
                            msg = ('FATAL: configuration error, malformed listener'
                                   ' bandwidth definition')
                            raise DiaConfParserError(msg)
        
                        if 'level_threshold' not in this_listener:
                            msg = ('FATAL: configuration error, missing listener'
                                   ' level_threshold definition')
                            raise DiaConfParserError(msg)              
                        if isinstance(this_listener['level_threshold'], (int, long)):
                            msg = ('FATAL: configuration error, malformed listener'
                                   ' level_threshold definition')
                            raise DiaConfParserError(msg)  
        
                        # define optional fields
                        if 'modulation' not in this_listener:
                            this_listener['modulation'] = ''
                        if this_listener['modulation'] not in ('FM'):
                            this_listener['modulation'] = ''
        
                        if 'audio_output' not in this_listener:
                            this_listener['audio_output'] = False
                        else:
                            if this_listener['audio_output'].lower() not in ('false', 'true'):
                                msg = ('FATAL: configuration error, malformed listener'
                                       ' audio_output option')
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
                            log.info(msg)
                        # check if modulation is configured
                        if this_listener['audio_output'] and this_listener['modulation'] == '':
                            this_listener['audio_output'] = False
                            msg = ('Listener modulation not defined, '
                                   ' and listener audio output requested.'
                                   ' Disabling audio output for the listener.')
                            log.info(msg)
        
                        if 'freq_analyzer_tap' not in this_listener:
                            this_listener['freq_analyzer_tap'] = False
                        else:
                            if this_listener['freq_analyzer_tap'].lower() not in ('false', 'true'):
                                msg = ('FATAL: configuration error, malformed listener'
                                       ' freq_analyzer_tap option')
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

            log.error(msg)
            msg = sys.exc_info()
            log.error(msg)
            raise
    
    def get_config(self):
        """Return a fully formed configuration file"""
        
        if self._good_conf:
            return self._good_conf
        else:
            msg = 'No valid configuration available'
            raise DiaConfParserError(msg)
        
                   

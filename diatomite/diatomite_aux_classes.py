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
        self._tap_directory = os.getcwd()

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
        self._tap_file_path = os.path.join(self._tap_directory,
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
        # TODO: write the set_tap_directory

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


class FreqListenerList(list):
    """Define a list of Frequency listener objects."""

    def append(self, listener):
        """add a listener to the list.
        listener -- FreqListener
        append will not allow duplicate ids to be added."""

        current_id_list = self.get_listener_id_list()

        # Checking of type must occur before checking of id
        if not isinstance(listener, freqlistener.FreqListener):
            msg = 'item is not of type FreqListener'
            log.error(msg)
            raise TypeError(msg)

        # obtain the listener id
        id_to_add = listener.get_id()

        if id_to_add in current_id_list:
            msg = "Frequency Listener's id is not unique"
            log.error(msg)
            raise FreqListenerListIdNotUniqueError(msg)

        super(FreqListenerList, self).append(listener)
        msg = 'FreqListener {i} added to list'.format(i=listener)
        log.debug(msg)

    def get_listener_id_list(self):
        """Obtain list of ids for all the members of the list"""
        res = []

        for listener in self:
            fid = listener.get_id()
            res.append(fid)

        msg = 'Listener_id_list:{i}'.format(i=res)
        log.debug(msg)

        return res

    def get_listener_by_id(self, lid):
        """Return a listener by id
        lid -- the id to search for"""

        res = None

        for listener in self:
            this_id = listener.get_id()
            if this_id == lid:
                return listener

        return res


class RadioSourceList(list):
    """Define a list of RadioSource objects."""

    def append(self, radio_source):
        """add a radio source to the list
        radio_source - a RadioSource to add to the list.
        append will not allow duplicate ids to be added."""

        current_id_list = self.get_radio_source_id_list()

        if not isinstance(radio_source, radiosource.RadioSource):
            msg = 'item is not of type RadioSource'
            log.error(msg)
            raise TypeError(msg)

        # obtain the listener id
        id_to_add = radio_source.get_id()

        if id_to_add in current_id_list:
            msg = "Radio source's id is not unique"
            log.error(msg)
            raise RadioSourceListIdNotUniqueError(msg)

        super(RadioSourceList, self).append(radio_source)
        msg = 'RadioSource {i} added to list'.format(i=radio_source)
        log.debug(msg)

    def get_radio_source_id_list(self):
        """Obtain list of ids for all the members of the list"""
        res = []

        for radio_source in self:
            fid = radio_source.get_id()
            res.append(fid)

        return res

    def get_radio_source_by_id(self, rsid):
        """Return a radio source by id
        rsid -- the id to search for"""

        res = None

        for radio_source in self:
            this_id = radio_source.get_id()
            if this_id == rsid:
                return radio_source
        return res

class Location(object):
    """Define a location."""

    address = ''
    longitude = ''
    latitude = ''

    # define if it is a static or mobile location
    type = ''


class DiatomiteSite(object):
    """Define a site for diatomite probes.
    Used to give the site a name and to tie a probe to a location.
    A site may have multiple probes, but an object of this type does not need
    to be aware of all diatomite probes."""

    # Location for this site
    location = Location()

    # Site name
    site_name = ''


class DiatomiteProbe(object):
    """Define a diatomite probe.
    A diatomite probe pertains to a DiatomiteSite.
    A diatomite probe has one or more radio sources
    """

    _id = ''
    _site = DiatomiteSite()
    _radio_source_list = RadioSourceList()
    _radio_source_sp_handle = []

    # pipe inputs for each radio source
    # index is the radio source ID
    _source_inputs = {}

    # pipe outputs for each radio source
    # index is the radio source ID
    _source_outputs = {}

    manager = multiprocessing.Manager()
    _source_output_queue = manager.Queue()

    def set_id(self, pid):
        """Set the id of this probe
        pid -- id of the probe"""
        self._id = pid

    def get_id(self):
        """Return the id of this probe"""

        return self._id

    def add_radio_source(self, radio_source):
        """Add a FreqListener to this Radio source's listener list.
        listener -- FreqListener"""

        # pass the output queue to the source
        radio_source.set_ouptut_queue(self._source_output_queue)

        try:
            self._radio_source_list.append(radio_source)
        except RadioSourceListIdNotUniqueError:
            msg = ('FATAL:Radio source id {rsid} already present on this'
                   ' Probe!!').format(rsid=radio_source.get_identifier())
            log.error(msg)
            raise

        msg = ("RadioSource {i} added to probe's radio source"
               " list").format(i=radio_source)
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

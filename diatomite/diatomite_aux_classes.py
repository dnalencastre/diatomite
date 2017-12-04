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
    
    def set_id(self,id):
        """Set the id of this probe
        id -- id of the probe"""
        self._id = id
        
    def get_id(self):
        """Return the id of this probe"""
        
        return self._id

    def add_radio_source(self, radio_source):
        """Add a FreqListener to this Radio source's listener list.
        listener -- FreqListener"""

        # TODO: check for duplicate ids when adding

        self._radio_source_list.append(radio_source)
        msg = ("RadioSource {i} added to probe's radio source"
               " list").format(i=radio_source)
        log.debug(msg)

    def start_sources(self):
        """Start all the sources"""
        pass
        # TODO: add method to start all radio sources

    def stop_sources(self):
        """stop all the sources"""
        pass
        # TODO: add method to stop all radio sources

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

import logging
import os
import sys
import errno
import threading
import exceptions
from string import ascii_letters, digits

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
    _id = None
    _tap_dir_path = None

    # set the stop event for the thread
    _tap_thread_stop = threading.Event()

    # set the update event for the thread
    _tap_value_update = threading.Event()

    _tap_value = ''

    _tap_lock = None

    _tap_file_name = None
    _tap_file_path = None

    def __init__(self, tap_id, tap_dir_path=None):
        """Setup the tap and Create the named pipe.
        tap_id -- id to """

        if tap_dir_path is not None:
            self.set_directory(tap_dir_path)
        else:
            # init the directory as the current directory
            self._tap_dir_path = os.getcwd()

        self._set_id(tap_id)

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
                logging.error(msg)
                msg = sys.exc_info()
                logging.warning(msg)
        except Exception, exc:
            msg = ('Data Tap {id}, Failed creating named pipe for fft tap'
                   ' with: {m}').format(id=self._get_id(), m=str(exc))
            logging.error(msg)
            msg = sys.exc_info()
            logging.error(msg)
            raise

        # set the tap update on it's own thread
        self._update_tap_thread = threading.Thread(target=self._output_value,
                                                   name=self._get_id(),
                                                   args=(self._tap_thread_stop,
                                                         self._tap_value_update
                                                        ))
        self._update_tap_thread.daemon = True
        self._update_tap_thread.start()

        msg = 'Data Tap {id} tap setup done.'.format(id=self._get_id())
        logging.debug(msg)

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
            logging.error(msg)
            raise BadIdError(msg)
        if all(character in ascii_letters+digits+'_'+'-'
               for character in ident):
            self._id = ident.lower()
            msg = 'id set to {i}'.format(i=ident.lower())
            logging.debug(msg)
        else:
            msg = 'Frequency id contains can only contain AZaz09-_'
            logging.error(msg)
            raise BadIdError(msg)

    def set_directory(self, path):
        """Set the directory where tap files should be written to.
        path -- full path to the directory"""

        self._tap_dir_path = path

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
                logging.debug(msg)

                try:
                    f_handle.writelines(output)
                except IOError, exc:
                    if exc.errno == errno.EPIPE:
                        msg = ('Broken pipe on tap {t} with:'
                               ' {m}').format(t=self._get_id(), m=str(exc))
                        logging.debug(msg)
                        msg = sys.exc_info()
                        msg = ('Broken pipe on tap'
                               ' {t}').format(t=self._get_id())
                        logging.warning(msg)
                    else:
                        msg = ('Error writing on on tap {t} with:'
                               ' {m}').format(t=self._get_id(), m=str(exc))
                        logging.error(msg)
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

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
import datetime
from string import ascii_letters, digits
from enum import Enum
import json

class BadIdError(Exception):
    """Raised when an object is passed an id with unacceptable
    characters."""
    pass


class DiaSysStatus(Enum):
    """Defines possible system and subsystem states for Diatomite"""
    INIT = 1 # when listener/receiver is initialized
    START = 2 # when listener/receiver is starting
    RUN = 3 # when listener/receiver is running
    SHUTDOWN = 4 # when listener/receiver is stopping
    STOP = 5 # when listener/receiver is stopped


class DiaSigStatus(Enum):
    """Defines possible signal states for Diatomite"""
    INIT = 1 # when listener is initialized
    START = 2 # when listener is starting
    PRESENT = 3 # when signal is detected as present
    ABSENT = 4 # when signal is not detected
    INOP = 5 # When listener is not operating


class DiaMsgType(Enum):
    """Defines possible message types"""
    LNR_SIG_STATE = 1 # listener signal state, reporting on a listener's signal state information
    LNR_SIG_STATUS_CHANGE = 2 # listener signal state change, reporting that a listener's signal status has changed from the  previous status
    LNR_STATE_CHANGE = 3 # reporting a change on listener state
    RCV_STATE_CHANGE = 4 # reporting a change on receiver state

class DiaSigInfo(object):
    """Defines signal state info
    This class will contain either current or historical info"""

    _data = {
        # status of the signal, a DiaSigStatus object
        'status': None,
        # time at which the change was effected
        'time': None,
        # signal level in DBM
        'sig_level' : None
        }

    def __init__(self, sig_status, sig_level, time):
        """Initializes the signal information
        sig_status -- a DiaSigStatus object
        sig_level -- signal level, in DBm
        time -- the time when the status change was affected/detected
            in iso format utc timezone"""
        
        if not isinstance(sig_status, DiaSigStatus):
            msg = 'Invalid signal status type, must be DiaSigStatus'
            raise TypeError(msg)

        self._data['status'] = sig_status
        self._data['sig_level'] = sig_level
        self._data['time'] = time

    def get_json(self):
        """Return a json representation of this data"""
        return json.dumps(self._data)

    def get_status(self):
        """returns the status info"""
        return self._data['status']

    def get_time(self):
        """returns the time at which the state change was affected/detected"""
        return self._data['time']

    def get_level(self):
        """Returns the signal level"""
        return self._data['sig_level']

    def set_json(self, data):
        """Sets the data from json"""
        self._data = json.loads(data)


class DiaSysInfo(object):
    """Defines receiver and listener state info
    This class will contain either current or historical info"""

    _data = {
        # status of the receiver or listener, a DiaSysStatus object
        'status': None,
        # time at which the change was effected
        'time': None
        }

    def __init__(self, sys_status, time):
        """Initializes the system information
        sys_status -- a DiaSysStatus object
        time -- the time when the status change was affected/detected
            in iso format utc timezone"""

        if not isinstance(sys_status, DiaSysStatus):
            msg = 'Invalid system status type, must be DiaSysStatus'
            raise TypeError(msg)

        self._data['satus'] = sys_status
        self._data['time'] = time

    def get_json(self):
        """Return a json representation of this data"""
        return json.dumps(self._data)

    def get_status(self):
        """returns the status info"""
        return self._data['status']

    def get_time(self):
        """returns the time at which the state change was affected/detected"""
        return self._data['time']

    def set_json(self, data):
        """Sets the data from json"""
        self._data = json.loads(data)


class DiaSigState(object):
    """Defines a signal status, both current state and previous state"""

    _data = {
            # the current status, a DiaSysInfo Object
            'current': None,
            # the previous status, a DiaSysInfo Object
            'previous': None
        }

    def __init__(self):
        """"Initialize the state,
        both current and previous will be initialized as DiaSysStatus.INIT,
        and a current time"""

        current_time = datetime.datetime.utcnow().isoformat()
        level = 0

        self._data['current'] = DiaSigInfo(DiaSysStatus.INIT, level, current_time)
        self._data['previous'] = DiaSigInfo(DiaSysStatus.INIT, level, current_time)

    def set_current(self, sig_info):
        """Sets the current state to a new state, and updates the previous
        sig_info -- a DiaSigInfo object"""

        if not isinstance(sig_info, DiaSigInfo):
            msg = 'Invalid system info type, must be DiaSigInfo'
            raise TypeError(msg)

        self._data['previous'] = self._data['current']
        self._data['current'] = sig_info

    def get_current(self):
        """returns the current state
        returns a DiaSigInfo object"""

        return self._data['current']

    def get_json(self):
        """Return a json representation of this data"""

        current = self._data['current'].get_json()        
        previous = self._data['previous'].get_json()

        ret_data = {
                'current': current,
                'previous' : previous
            }

        return json.dumps(ret_data)

    def set_json(self, data):
        """Sets the data from json"""
        t_data = json.loads(data)

        current_time = datetime.datetime.utcnow().isoformat()

        current = DiaSysInfo(DiaSigStatus.INIT, current_time)
        current.set_json(t_data['current'])

        previous = DiaSysInfo(DiaSigStatus.INIT, current_time)
        previous.set_json(t_data['previous'])

        self._data['current'] = current
        self._data['previous'] = previous


class DiaListenerMsg(object):
    """Class to encapsulate data sent by a listener"""

    _data = {
            # the type of signal to send, of type DiaMsgType
            'msg_type': None,
            
            # the id for the listener that originated the message 
            'lnr_id': None,
            
            # the payload of the message
            'payload': None
        }

    def __init__(self, sig_type, lnr_id, payload):
        """initialize the object
        sig_type -- signal type, a DiaMsgType object
        lnr_id -- Listener Id
        payload -- data to send, either a json string or a DiaListernerMsg"""
 
        if not isinstance(sig_type, DiaMsgType):
            msg = 'Invalid message type, must be DiaMsgType'
            raise TypeError(msg)

        self._data['lnr_id'] = lnr_id
        self._data['msg_type'] = sig_type       
        self._data['payload'] = payload
        
    def get_msg_type(self):
        """Return the message type, a DiaMsgType"""
        return self._data['msg_type']
    
    def get_lnr_id(self):
        """Return sending listener's id"""
        return self._data['lnr_id']
    
    def get_payload(self):
        """Return the payload"""
        return self._data['payload']

    def get_json(self):
        """Return a json representation of this data"""
        return json.dumps(self._data)

    def set_json(self, data):
        """Sets the data from json"""
        self._data = json.loads(data)        


class DiaRadioReceiverMsg(object):
    """Class to encapsulate data sent by a receiver"""
    
    _data = {
            # the type of signal to send, of type DiaMsgType
            'msg_type': None,
            
            # the id for the RadioReceiver that originated the message 
            'rrv_id': None,
            
            # the payload of the message, json or dict
            'payload': None
        }

    def __init__(self, msg_type, rcv_id, payload):
        """initialize the object
        msg_type -- message type, a DiaMsgType object
        rrv_id -- RadioReceiver Id
        payload -- data to send, either a json string or a DiaListernerMsg"""

        if not isinstance(msg_type, DiaMsgType):
            msg = 'Invalid message type, must be DiaMsgType'
            raise TypeError(msg)

        self._data['rrv_id'] = rcv_id
        self._data['msg_type'] = msg_type

        if isinstance(payload, DiaListenerMsg):
            self._data['payload'] = payload.get_json()
        else:
            self._data['payload'] = payload

    def get_msg_type(self):
        """Return the message type, a DiaMsgType"""
        return self._data['msg_type']

    def get_rcv_id(self):
        """Return sending radio receiver's id"""
        return self._data['rrv_id']
    
    def get_payload(self):
        """Return the payload"""
        return self._data['payload']

    def get_json(self):
        """Return a json representation of this data"""
        return json.dumps(self._data)

    def set_json(self, data):
        """Sets the data from json"""
        self._data = json.loads(data)


class DiaSysState(object):
    """Defines a receiver and listener status, both current state
    and the previous state"""

    _data = {
            # the current status, a DiaSysInfo Object
            'current': None,
            # the previous status, a DiaSysInfo Object
            'previous': None
        }

    def __init__(self):
        """"Initialize the state,
        both current and previous will be initialized as DiaSysStatus.INIT,
        and a current time"""

        current_time = datetime.datetime.utcnow().isoformat()

        self._data['current'] = DiaSysInfo(DiaSysStatus.INIT, current_time)
        self._data['previous'] = DiaSysInfo(DiaSysStatus.INIT, current_time)

    def set_current(self, sys_info):
        """Sets the current state to a new state, and updates the previous
        sys_info -- a DiaSysInfo object"""

        if not isinstance(sys_info, DiaSysInfo):
            msg = 'Invalid system info type, must be DiaSysInfo'
            raise TypeError(msg)

        self._data['previous'] = self._data['current']
        self._data['current'] = sys_info

    def get_current(self):
        """returns the current state
        returns a DiaSysInfo object"""

        return self._data['current']

    def get_json(self):
        """Return a json representation of this data"""

        current = self._data['current'].get_json()        
        previous = self._data['previous'].get_json()

        ret_data = {
                'current': current,
                'previous' : previous
            }

        return json.dumps(ret_data)

    def set_json(self, data):
        """Sets the data from json"""
        t_data = json.loads(data)

        current_time = datetime.datetime.utcnow().isoformat()

        current = DiaSysInfo(DiaSysStatus.INIT, current_time)
        current.set_json(t_data['current'])

        previous = DiaSysInfo(DiaSysStatus.INIT, current_time)
        previous.set_json(t_data['previous'])

        self._data['current'] = current
        self._data['previous'] = previous


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

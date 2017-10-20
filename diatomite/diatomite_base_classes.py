#!/usr/bin/env python2
"""
    diatomite - monitoring radio frequency activity
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

import logging as log
import time
import datetime
from multiprocessing import Process, Pipe
from string import ascii_letters, digits
from gnuradio import gr
from gnuradio import blocks
from gnuradio import filter as grfilter
from gnuradio.fft import logpwrfft
import threading
import osmosdr
import os
import sys
import exceptions
import errno

class FreqListenerInvalidModulation(Exception):
    """Raised when  a FreqListener is passed an invalid modulation."""
    pass


class RadioSourceFrequencyOutOfBounds(Exception):
    """Raised when a RadioSource is given a FreqListener that has frequency and
    bandwidth that don't fit within the radio source's frequency abilites."""
    pass

class BadIdError(Exception):
    """Raised when an object is passed an id with unacceptable
    characters."""
    pass

class RadioSourceListIdNotUniqueError(Exception):
    """Raised when a RadioSource with an already occurring id is added to a
    RadioRecieverList."""
    pass


class RadioSourceRadioFailureError(Exception):
    """Raised when an error related to a radio device occurs."""
    pass


class FreqListenerListIdNotUniqueError(Exception):
    """Raised when a FreqListener with an already occurring id is added to a
    FreqlistenerList."""
    pass

class FreqListenerError(Exception):
    """Raised when a FreqListener encounters an error."""
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


class RadioReceiverSate(object):
    """Define possible states for a radio a receiver."""
    PRE_INIT = 0
    OK = 1
    FAILED = 2


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
                msg = ('File already exists , Failed creating named pipe for fft tap with:'
                       ' {m}').format(m=str(exc))
                log.error(msg)
                msg = sys.exc_info()
                log.warning(msg)
        except Exception, exc:
            msg = ('Failed creating named pipe for fft tap with:'
                   ' {m}').format(m=str(exc))
            log.error(msg)
            msg = sys.exc_info()
            log.error(msg)
            raise

        # set the tap update on it's own thread
        self._update_tap_thread = threading.Thread(target=self._output_value,
                                                   name = self._get_id(),
                                                   args=(self._tap_thread_stop,
                                                         self._tap_value_update))
        self._update_tap_thread.daemon = True
        self._update_tap_thread.start()
        
        msg = 'FFT tap setup done.'
        log.debug(msg)

    def _set_file(self):
        """Set the file name"""
        # setup file name and path
        self._tap_file_name = self._get_id() + self._tap_file_extension
        self._tap_file_path = os.path.join(self._tap_directory, self._tap_file_name)
        
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
            
            with open(self._tap_file_path, 'w') as f_handle:
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
                        log.warning(msg)
                    else:
                        raise
            # TODO: find how to recover from broken pipe


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

class FreqListener(object):
    """Define the subsystem to listen to a given radio frequency.
    This includes the GNU radio blocks to tune and capture information
    from a radio signal.
    """

    # id for this listener
    _id = ''

    # frequency in hz
    _frequency = 1

    # bandwidth
    _bandwidth = 1

    # modulation
    _modulation = ''
    
    # TODO: unify fft probe and tap initialization and teardown

    # frequency offset from the radio source
    _frequency_offset = 0

    def __init__(self, listener_id):
        """init the FreqListener
        listener_id -- the frequency listener id.
                Acceptable characters: ASCII characters, numbers,
                underscore, dash."""

        self.set_id(listener_id)
        self._decimation = 1
        self._samp_rate = 500000
        self._transition_bw = 2000
        self._filter_taps = grfilter.firdes.low_pass(1,
                                                     self._samp_rate,
                                                     (self._samp_rate
                                                      / (2*self._decimation)),
                                                     self._transition_bw)
        self._radio_source_bw = 0
        self._radio_source_block = None
        self._gr_top_block = None

        self._log_fft = None
        self._fft_size = 1024
        self._fft_ref_scale = 2
        self._fft_frame_rate = 30
        self._fft_avg_alpha = 1.0
        self._fft_average = False
        
        # probe poll rate in hz
        self._probe_poll_rate = 10
        self._fft_signal_level = None
        
        self._create_fft_tap = False
        
        # write the taps to the current directory
        self._tap_directory = os.getcwd()
        
        self._fft_tap = None
        
        self._status = 'PRE_INIT'
        
        self._probe_stop = threading.Event()

    def set_id(self, listener_id):
        """Sets the frequency listener id.
        Converts alphabetic characters to lower case.
        listener_id -- the frequency listener id.
                        Acceptable characters: ASCII characters, numbers,
                        underscore, dash."""
        
        if listener_id == '':
            msg = 'Frequency id is empty'
            log.error(msg)
            raise BadIdError(msg)
        if all(character in ascii_letters+digits+'_'+'-'
               for character in listener_id):
            self._id = listener_id.lower()
            msg = 'id set to {i}'.format(i=listener_id.lower())
            log.debug(msg)
        else:
            msg = 'Frequency id contains can only contain AZaz09-_'
            log.error(msg)
            raise BadIdError(msg)
        
    def set_tap_directory(self, path):
        """Set the directory where tap files should be written to.
        path -- full path to the directory"""
        pass
        # TODO: write the set_tap_directory

    def set_frequency(self, frequency):
        """Sets the frequency for the listener.
        frequency -- frequency in Hz (integer)"""

        radio_spectrum = RadioSpectrum()
        # radio spectrum limits
        rs_lower_freq = radio_spectrum.get_lower_frequency()
        rs_upper_freq = radio_spectrum.get_upper_frequency()

        if not float(frequency).is_integer():
            msg = 'Frequency is not a whole number'
            log.error(msg)
            raise ValueError(msg)
        elif frequency < rs_lower_freq or frequency > rs_upper_freq:
            msg = ('Frequency must be above {fl} hz '
                   'and below {fu} hz').format(fl=rs_lower_freq,
                                               fu=rs_upper_freq)
            log.error(msg)
            raise ValueError(msg)
        else:
            self._frequency = int(frequency)
            msg = 'Frequency set to {i}'.format(i=frequency)
            log.debug(msg)

    def set_frequency_offset(self, radio_source_center_frequency):
        """Set the listener's offset frequency from the radio source's center
        frequency
        radio_source_center_frequency -- the radio source's center
                                         frequency in Hz"""

        # calculate offset
        if self._frequency < radio_source_center_frequency:
            self._frequency_offset = (radio_source_center_frequency
                                      - self._frequency) * -1
        elif self._frequency > radio_source_center_frequency:
            self._frequency_offset = (radio_source_center_frequency
                                      - self._frequency)
        else:
            self._frequency_offset = 0

        msg = 'Frequency offset set to {i}'.format(i=self._frequency_offset)
        log.debug(msg)

        # TODO: may need to notify working parts of the radio source

    def set_bandwidth(self, bandwidth):
        """Sets the bandwidth for the listener.
        bandwidth -- the bandwidth in Hz (integer)"""
        if not float(bandwidth).is_integer():
            msg = 'Bandwidth is not a whole number'
            log.error(msg)
            raise ValueError(msg)
        elif bandwidth < 1:
            msg = 'Bandwidth must be ate least 1 hz'
            log.error(msg)
            raise ValueError(msg)
        else:
            self._bandwidth = int(bandwidth)
            msg = 'Bandwidth set to {i}'.format(i=bandwidth)
            log.debug(msg)

    def set_modulation(self, modulation):
        """Sets the modulation for the listener.
        modulation -- the modulation"""

        acceptable_modulations = ['fm', 'am', 'usb', 'lsb']

        modulation = modulation.lower()

        if modulation in acceptable_modulations:
            self._modulation = modulation
            msg = 'Modulation set to {i}'.format(i=modulation)
            log.debug(msg)
        else:
            msg = ('modulation must be one of {m}').format(
                m=' '.join(acceptable_modulations))
            log.error(msg)
            raise FreqListenerInvalidModulation(msg)
        
    def set_source_block(self,source_block):
        """Set the gnu radio source block.
        source_block -- the gr source block of type osmosdr.osmosdr_swig.source_sptr"""
        
        if not type(source_block) == osmosdr.osmosdr_swig.source_sptr:
            msg = 'Wrong type for radio source block.'
            log.error(msg)
            raise TypeError(msg)
        else:
            self._radio_source_block = source_block
            msg = 'Radio Source block set.'
            log.debug(msg)         
    
    def set_gr_top_block(self,gr_top_block):
        """Set the gnu radio top block.
        gr_top_block -- the gr top block of gr.top_block"""       
        
        type_gr_top_block = type(gr_top_block)
        
        if not type_gr_top_block == gr.top_block:
            msg = ('gr_top_block must be of type gr.top_block,'
                   ' was {tgtb}').format(tgtb=type_gr_top_block)
            raise TypeError(msg)
        
        self._gr_top_block = gr_top_block
        msg = 'Top block set.'
        log.debug(msg)         

    def set_create_fft_tap(self,create_fft_tap):
        """Inform if taps are to be created
        create_fft_tap - if an fft tap is to be created True or False"""
        
        if isinstance(create_fft_tap, bool):
            self._create_fft_tap = create_fft_tap
        else:
            msg = 'create_fft_tap must be a boolean'
            raise TypeError(msg)
        
        msg = 'FFT tap creation set to {v}'.format(v=create_fft_tap)
        log.debug(msg)

    def get_id(self):
        """Returns the frequency listener id."""
        return self._id

    def get_frequency_offset(self):
        """Returns the listener's frequency offset from the radio source's
        center frequency in hz."""
        return self._frequency_offset

    def get_frequency(self):
        """Returns the frequency listener frequency in Hz."""
        return self._frequency

    def get_bandwidth(self):
        """Returns the frequency listener bandwidth in Hz."""
        return self._bandwidth

    def get_modulation(self):
        """Returns the frequency listener modulation."""
        return self._modulation

    def get_upper_frequency(self):
        """Computes and retrieves the upper frequency of the listener,
        taking into account the frequency and the bandwidth."""

        return self._frequency + (self._bandwidth/2)

    def get_lower_frequency(self):
        """Computes and retrieves the lower frequency of the listener,
        taking into account the frequency and the bandwidth."""

        return self._frequency - (self._bandwidth/2)

    def get_radio_source_bw(self):
        """Get the radio source bandwidth for this frequency listener"""
        return self._radio_source_bw

    def set_radio_source_bw(self, radio_source_bw):
        """Get the radio source bandwidth for this frequency listener"""
        self._radio_source_bw = radio_source_bw

    def _config_frequency_translation(self):
        """Configure the frequency translation filter."""
        self._freq_translation_filter = (
            grfilter.freq_xlating_fir_filter_ccc(self._decimation,
                                                 (self._filter_taps),
                                                 self.get_frequency_offset(),
                                                 self.get_radio_source_bw()))
        
        msg = 'Frequency translation set.'
        log.debug(msg)

    def get_create_fft_tap(self):
        """Get if the listener is to create an fft tap."""
        return self._create_fft_tap

    def _connect_frequency_translator_to_source(self):
        """Connect the frequency translation filter to the source.
        """
     
        try:
            self._gr_top_block.connect(self._radio_source_block, 
                                       self._freq_translation_filter)
        except Exception, exc:
            msg = ('Failed connecting radio source to filter with'
                   ' {m}').format(m=str(exc))
            log.debug(msg)
            raise

        msg = 'Frequency translation connected to source.'
        log.debug(msg)

    def _setup_rf_fft(self):
        """Setup an fft to check the RF status."""
        
        # start the fft
        try:
            self._log_fft  = logpwrfft.logpwrfft_c(
                sample_rate=self._samp_rate,
                fft_size=self._fft_size,
                ref_scale=self._fft_ref_scale,
                frame_rate=self._fft_frame_rate,
                avg_alpha=self._fft_avg_alpha,
                average=self._fft_average
            )
        except Exception, exc:
            msg = ('Failed setting up fft with'
                   ' {m}').format(m=str(exc))
            log.debug(msg)
            raise Exception(msg)
        
        msg = 'FFT set up completed.'
        log.debug(msg)
        
        # connect the fft to the freq translation filter
        try:
            self._gr_top_block.connect(self._freq_translation_filter, 
                                       self._log_fft)                 
        except Exception, exc:
            msg = ('Failed to connect the fft to freq translation, with:'
                   ' {m}').format(m=str(exc))
            log.debug(msg)
            raise Exception(msg)

        msg = 'FFT connected to Frequency translation.'
        log.debug(msg)


    def _retrieve_fft(self, stop_event):
        """Retrieve fft values"""
        
        while not stop_event.is_set():
            
            #TODO: fft value processing should go here
            
            current_time = datetime.datetime.utcnow().isoformat()
           
            val = self._fft_signal_probe.level()
            
            # update taps
            if self._create_fft_tap:
                tap_value = '{t};{v}\n'.format(t=current_time, v=val)

                self._fft_tap.update_value(tap_value)
                
                msg = 'updating data tap'
                log.debug(msg)
            
            stop_event.wait(1.0 / self._probe_poll_rate)

    def _setup_fft_tap(self):
        """Setup a tap to provide live fft values.
        Create a named pipe containing the latest set of fft values.
        Will output to a previously created named pipe/file.
        If an error occurs while creating the named pipe (other than that the
        file already exists), tap output thread will not be started."""

        msg = 'Setting up fft tap.'
        log.debug(msg)
        
        try:
            self._fft_tap = DataTap(self.get_id())
        except exceptions, exc:
            msg = 'Failed to setup tap for FFT with:{m}'.format(m=str(exc))
            log.error(msg)
            raise

        msg = 'FFT tap setup done.'
        log.debug(msg)

    def _teardown_fft_tap(self):
        """Cleanup the live fft values tap.
        Will remove the tap file from the file system"""
        
        # stop the thread
        
        self._fft_tap.stop()

    def _setup_signal_probe(self):
        """Setup probe to retrieve the fft data"""
        
        try:
            self._fft_signal_probe = blocks.probe_signal_vf(self._fft_size)
        except Exception, exc:
            msg = ('Failed to create fft probe, with:'
                   ' {m}').format(m=str(exc))
            log.debug(msg)
            raise Exception(msg)
   
        # connect the signal probe to the fft
        try:
            self._gr_top_block.connect(self._log_fft, 
                                       self._fft_signal_probe)                 
        except Exception, exc:
            msg = ('Failed to connect the fft to freq translation, with:'
                   ' {m}').format(m=str(exc))
            log.debug(msg)
            raise Exception(msg)
 
        msg = 'Launching fft data retrieval thread.'
        log.debug(msg)
          
        # set the fft retrieval on it's own thread
        self._retrieve_fft_thread = threading.Thread(target=self._retrieve_fft,
                                                     name = self.get_id(),
                                                     args=(self._probe_stop,))
        self._retrieve_fft_thread.daemon = True
        self._retrieve_fft_thread.start()
        
        msg = 'Signal probe setup done.'
        log.debug(msg)
    
    def _stop_signal_probe(self):
        """Stop the fft data probe"""

        # send the stop event to the thread
        self._probe_stop.set()
    
    def start(self):
        """Start the frequency listener."""

        # configure frequency translator
        try:
            self._config_frequency_translation()
        except Exception, exc:
            msg = ('Failed configuring frequency translation with'
                   ' {m}').format(m=str(exc))
            log.debug(msg)
            raise Exception(msg)

        # connect frequency translator to source
        try:
            self._connect_frequency_translator_to_source()
        except Exception, exc:
            msg = ('Failed connecting frequency translation to source'
                   'with {m}').format(m=str(exc))
            log.debug(msg)
            raise Exception(msg)
        
        # setup fft and connect it to frequency translator
        try:
            self._setup_rf_fft()
        except Exception, exc:
            msg = ('Failed to setup RF FFT'
                   'with {m}').format(m=str(exc))
            log.debug(msg)
            raise Exception(msg)

        # handle the fft tap creation
        # thread for data tap must be present before
        # the thread that starts the signal probe
        if self._create_fft_tap:
            try:
                self._setup_fft_tap()
            except Exception, exc:
                msg = ('Failed to setup fft tap'
                       'with {m}').format(m=str(exc))
                log.debug(msg)
                raise Exception(msg)     

        try:
            self._setup_signal_probe()
        except Exception, exc:
            msg = ('Failed to setup signal probe'
                   'with {m}').format(m=str(exc))
            log.debug(msg)
            raise Exception(msg)
        
        self._status = 'RUNNING'
        
    def stop(self):
        """Stop the frequency listener """
        
        msg = 'stopping frequency listener {id}'.format(id=self.get_id())
        log.debug(msg)
        
        if self._status == 'RUNNING':
 
            if self._create_fft_tap:
            # stop the fft tap
                try:
                    self._teardown_fft_tap()
                except Exception, exc:
                    msg = ('Failed tearing down fft with:'
                           ' {m}').format(m=str(exc))
                    raise Exception(msg)
        
            # stop fft signal probe
            try:
                self._stop_signal_probe()
            except Exception, exc:
                msg = ('Failed stopping signal probe with:'
                       ' {m}').format(m=str(exc))
                raise Exception(msg)   

        else:
            msg = ("Will not stop listener, as status is"
                   " {s}").format(s=self._status)
            log.error(msg)
            msg = 'not yet done'
            raise FreqListenerError(msg)

   
        #TODO: add the fft data retrieval

class FreqListenerList(list):
    """Define a list of Frequency listener objects."""

    def append(self, listener):
        """add a listener to the list.
        listener -- FreqListener
        append will not allow duplicate ids to be added."""

        current_id_list = self.get_listener_id_list()

        # Checking of type must occur before checking of id
        if not isinstance(listener, FreqListener):
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


class RadioSource(object):
    """Define a radio source.
    This usually relates to the radio hardware
    """

    # Id of the radio source
    _id = ''

    # list of frequency listeners
    _listener_list = None

    _type = ''

    # define the bandwidth capability of the radio source, in hz
    _cap_bw = 0

    # define minimum and maximum frequencies that are
    # tunable by the radio source, in hz
    _cap_freq_min = 0
    _cap_freq_max = 0

    # define the currently tuned frequency
    _center_freq = 0

    # radio source arguments
    _source_args = ''
    
    _radio_state = None

    def __init__(self, radio_source_id):
        """Initialize the radio source object.
        radio_source_id -- the frequency listener id.
                        Acceptable characters: ASCII characters, numbers,
                        underscore, dash."""
        radio_spectrum = RadioSpectrum()
        self._type = 'base_radio_source'
        self._source_args = "numchan=" + str(1) + " " + ''
        self._cap_bw = 1000
        self._cap_freq_min = radio_spectrum.get_lower_frequency()
        self._cap_freq_max = radio_spectrum.get_upper_frequency()
        # set center frequency halfway between min and max
        self._center_freq = self._cap_freq_max - ((self._cap_freq_max
                                                   - self._cap_freq_min) / 2)
        self.set_id(radio_source_id)

        self._radio_state = RadioReceiverSate.PRE_INIT

        self._radio_source = None

        self._listener_list = FreqListenerList()

        msg = ('Initialized with type:{t}, cap_bw:{cb}, cap_freq_min:{cfmin},'
               ' cap_freq_max:{cfmax}, center_freq:{cf},'
               ' id:{id}').format(t=self._type, cb=self._cap_bw,
                                  cfmin=self._cap_freq_min,
                                  cfmax=self._cap_freq_max,
                                  cf=self._center_freq, id=radio_source_id)
        log.debug(msg)

    def _radio_init(self):
        """Initialize the radio hw."""

        self._gr_top_block = gr.top_block()
        # specific radio initialization to be added on this method on derived
        # classes
        self._radio_state = RadioReceiverSate.OK

    def set_id(self, radio_source_id):
        """Sets the radio source's  id.
        Converts alphabetic characters to lower case.
        radio_source_id -- the frequency listener id.
                        Acceptable characters: ASCII characters, numbers,
                        underscore, dash."""

        if radio_source_id == '':
            msg = 'Radio source id is empty'
            log.error(msg)
            raise BadIdError(msg)
        if all(character in ascii_letters+digits+'_'+'-'
               for character in radio_source_id):
            self._id = radio_source_id.lower()
            msg = 'id set to {i}'.format(i=radio_source_id.lower())
            log.debug(msg)
        else:
            msg = 'Frequency id contains contains unacceptable characters'
            log.error(msg)
            raise BadIdError(msg)
        
    def set_frequency(self, frequency):
        """Set the source's center frequency
        frequency -- frequency in Hz (integer)"""

        src_lower_freq = self.get_lower_frequency()
        src_upper_freq = self.get_upper_frequency()

        if not float(frequency).is_integer():
            msg = 'Frequency is not a whole number'
            log.error(msg)
            raise ValueError(msg)
        elif frequency < src_lower_freq or frequency > src_upper_freq:
            msg = ('Frequency must be above {fl} hz '
                   'and below {fu} hz').format(fl=src_lower_freq,
                                               fu=src_upper_freq)
            log.error(msg)
            raise ValueError(msg)
        else:
            self._frequency = int(frequency)
            msg = 'Frequency set to {i}'.format(i=frequency)
            log.debug(msg)

    def add_frequency_listener(self, listener):
        """Add a FreqListener to this Radio Source's listener list.
        listener -- FreqListener"""

        if listener.get_upper_frequency() > self._cap_freq_max:
            msg = ("The listener's upper frequency ({lf}) is above the "
                   "radio source's maximum frequency ({mf})").format(
                       lf=listener.get_upper_frequency(),
                       mf=self._cap_freq_max)
            log.error(msg)
            raise RadioSourceFrequencyOutOfBounds(msg)

        if listener.get_lower_frequency() < self._cap_freq_min:
            msg = ("The listener's lower frequency ({lf}) is below the "
                   "radio source's minimum frequency"
                   " ({mf})").format(lf=listener.get_upper_frequency(),
                                     mf=self._cap_freq_min)
            log.error(msg)
            raise RadioSourceFrequencyOutOfBounds(msg)

        # update the listener's offset
        listener.set_frequency_offset(self._center_freq)

        # pass the bandwidth to the listener
        listener.set_radio_source_bw(self._cap_bw)
        
        # pass the source block
        listener.set_source_block(self.get_source_block())
        
        # pass the top block
        listener.set_gr_top_block(self._gr_top_block)

        self._listener_list.append(listener)
        msg = 'FreqListener {i} added to list'.format(i=listener)
        log.debug(msg)

    def get_id(self):
        """Returns the radio source's id."""
        return self._id

    def get_upper_frequency(self):
        """Return the upper frequency on this radio source."""
        return self._cap_freq_max

    def get_lower_frequency(self):
        """Return the lower frequency on this radio source."""
        return self._cap_freq_min

    def get_bandwidth_capability(self):
        """Return the bandwidth capability for this radio source."""
        return self._cap_bw

    def get_type(self):
        """Return the type of this radio source."""
        return self._type

    def get_center_frequency(self):
        """Return the center frequency for this source."""
        return self._center_freq

    def get_listener_id_list(self):
        """Return a list of listener ids configured on this source"""
        return self._listener_list.get_listener_id_list()

    def get_source_block(self):
        """Return the gnu radio source block"""
        
        if self._radio_state == RadioReceiverSate.OK:
            return self._radio_source
        else:
            msg = 'Radio Source not started'
            raise RadioSourceRadioFailureError(msg)
        
    def get_gr_top_block(self):
        """Retrieve the Gnu radio top block for this source"""

        if self._radio_state == RadioReceiverSate.OK:
            return self._gr_top_block
        else:
            msg = 'Radio Source not started'
            raise RadioSourceRadioFailureError(msg)
    
    def _run_source_subprocess(self, input_conn, output_conn):
        """start the subprocess for the source."""
        # TODO: handle the lifecycle of the source
        
        msg = 'radio source subprocess for {id} starting.'.format(id=self.get_id())
        log.debug(msg)
        output_conn.send(msg)
        
        stop = False
        
        msg = 'starting frequency listeners'
        log.debug(msg)
                
        self.start_frequency_listeners()
        
        # wait for the end of the top block
        self._gr_top_block.start()
        
        # wait for the stop command
        while not stop:
            input_cmd = input_conn.recv()
            
            if input_cmd == 'STOP':
                stop = True
        
        if stop:
            self.stop_frequency_listeners()
            self._gr_top_block.stop()
    
        msg = 'radio source subprocess for {id} exiting.'.format(id=self.get_id())
        log.debug(msg)
        output_conn.send(msg)
    
    def start(self):
        """Start the radio source."""
        
        # setup and start the subprocess for this source

        self._subprocess_in, self._subprocess_out  = Pipe()
        self._source_subprocess = Process(target=self._run_source_subprocess,
                                          args=(self._subprocess_out,
                                                self._subprocess_in))
        try:
            self._source_subprocess.start()
        except Exception, exc:
            msg = ('Failed starting the source subprocesses with:'
                   ' {m}').format(m=str(exc))
            log.debug(msg)
            raise
            
            
    def stop(self):
        """Stop the radio listener"""
        msg = 'Stopping radio source {id}'.format(id=self.get_id())
        log.debug(msg)    
    
        self._subprocess_in.send('STOP')
    
    def stop_frequency_listeners(self):
        """Stop  individual frequency listeners."""
        
        msg = ('Stopping all frequency listeners for'
               'source {s}').format(s=self.get_id())
    
        #iterate through the listeners and start them
        for freq_listener in self._listener_list:

            try:
                freq_listener.stop()
            except Exception, exc:
                msg = ('Failed stopping frequency listener with:'
                       ' {m}').format(m=str(exc))
                log.debug(msg)
                raise
                
            msg = ('stopped frequency listener '
                   '{fid}').format(fid=freq_listener.get_id())
            log.debug(msg) 
    
    def start_frequency_listeners(self):
        """Start individual frequency listeners"""

        msg = ('Starting all frequency listeners for'
               'source {s}').format(s=self.get_id())

        #iterate through the listeners and start them
        for freq_listener in self._listener_list:
            freq_listener.start()
            msg = ('started frequency listener '
                   '{fid}').format(fid=freq_listener.get_id())
            log.debug(msg)
        


class RTL2838R820T2RadioSource(RadioSource):
    """Defines a radio source hardware with  RTL2838 receiver
     and a R820T2 tuner."""

    def __init__(self, radio_source_id):
        """Initialize the radio source object.
        radio_source_id -- the frequency listener id.
                        Acceptable characters: ASCII characters, numbers,
                        underscore, dash."""
        self._type = 'RTL2838_R820T2'
        self._source_args = "numchan=" + str(1) + " " + ''
        self._cap_bw = 2400000
        self._cap_freq_min = 25000
        self._cap_freq_max = 1750000000
        self._center_freq = self._cap_freq_max - ((self._cap_freq_max
                                                   - self._cap_freq_min) / 2)
        self.set_id(radio_source_id)

        self._freq_corr = 0
        self._dc_offset_mode = 0
        self._iq_balance_mode = 0
        self._gain_mode = False
        self._iq_gain_mode = 0
        self._gain = 10
        self._af_gain = 10
        self._bb_gain = 20
        self._antenna = ''
        self._bandwith = 0
        self._radio_source = None

        self._listener_list = FreqListenerList()

        msg = ('Initialized with type:{t}, cap_bw:{cb}, cap_freq_min:{cfmin},'
               ' cap_freq_max:{cfmax}, center_freq:{cf},'
               ' id:{id}').format(t=self._type, cb=self._cap_bw,
                                  cfmin=self._cap_freq_min,
                                  cfmax=self._cap_freq_max,
                                  cf=self._center_freq, id=radio_source_id)
        log.debug(msg)

    def _radio_init(self):
        """Initialize the radio hw."""
        super(RTL2838R820T2RadioSource, self)._radio_init()

        try:
            self._radio_source = osmosdr.source(self._source_args)
            # TODO: find a way to check if osmosdr.source init is successful
        except Exception, exc:
            msg = ('Failed to start source with:'
                   ' {m}').format(m=str(exc))
            log.error(msg)
            msg = sys.exc_info()
            log.error(msg)
            raise           
        
        radio_init_sucess = True

        if radio_init_sucess:
            self._radio_source.set_sample_rate(self.get_bandwidth_capability())
            self._radio_source.set_center_freq(self.get_center_frequency(), 0)

            self._radio_source.set_freq_corr(self._freq_corr, 0)
            self._radio_source.set_dc_offset_mode(self._dc_offset_mode, 0)
            self._radio_source.set_iq_balance_mode(self._iq_balance_mode, 0)
            self._radio_source.set_gain_mode(self._gain_mode, 0)
            self._radio_source.set_gain(self._gain, 0)
            self._radio_source.set_if_gain(self._af_gain, 0)
            self._radio_source.set_bb_gain(self._bb_gain, 0)
            self._radio_source.set_antenna(self._antenna, 0)
            self._radio_source.set_bandwidth(self._bandwith, 0)
            self._radio_state = RadioReceiverSate.OK
        else:
            self._radio_state = RadioReceiverSate.FAILED
            msg = 'Radio initialization failed'
            raise RadioSourceRadioFailureError(msg)


class RadioSourceList(list):
    """Define a list of RadioSource objects."""

    def append(self, radio_source):
        """add a radio source to the list
        radio_source - a RadioSource to add to the list.
        append will not allow duplicate ids to be added."""

        current_id_list = self.get_radio_source_id_list()

        if not isinstance(radio_source, RadioSource):
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

    _site = DiatomiteSite()
    _radio_source_list = RadioSourceList()

    def add_radio_source(self, radio_source):
        """Add a FreqListener to this Radio source's listener list.
        listener -- FreqListener"""

        #TODO: check for duplicate ids when adding

        self._radio_source_list.append(radio_source)
        msg = ("RadioSource {i} added to probe's radio source"
               " list").format(i=radio_source)
        log.debug(msg)

    #TODO: add method to start all radio sources
    
    #TODO: add method to stop all radio sources


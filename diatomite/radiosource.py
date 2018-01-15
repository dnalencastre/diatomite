#!/usr/bin/env python2
"""
    radiosource - Configure hardware radio sources for the diatomite system
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
import logging
import threading
import sys
from multiprocessing import Process, Queue
from string import ascii_letters, digits
from datetime import datetime
import osmosdr
from gnuradio import gr
from gnuradio import blocks
from gnuradio import filter as grfilter
from gnuradio.fft import logpwrfft
from gnuradio import audio
from gnuradio.filter import firdes
from gnuradio import analog
import diatomite_aux_classes as dia_aux
from Crypto.SelfTest.Random.test__UserFriendlyRNG import multiprocessing


class RadioSourceFrequencyOutOfBoundsError(Exception):
    """Raised when a RadioSource is given a FreqListener that has frequency and
    bandwidth that don't fit within the radio source's frequency abilites."""
    pass


class RadioSourceRadioFailureError(Exception):
    """Raised when an error related to a radio device occurs."""
    pass


class RadioSourceError(Exception):
    """Raised when a RadioSource encounters an error."""
    pass


class RadioSourceSupportedDevsError(Exception):
    """Raised when a RadioSourceSupportedDevs encounters an error."""
    pass


class RadioSourceSate(object):
    """Define possible states for a radio a receiver."""
    STATE_PRE_INIT = 0
    STATE_OK = 1
    STATE_FAILED = 2


class RadioSourceSupportedDevs(object):
    """Define the supported rf devices and their classes"""

    _supported_dev_dict = {'RTL2838': {'class': 'RTL2838RadioSource'}}

    def get_supported_devs(self):
        """returns a list of supported devices."""

        return self._supported_dev_dict.keys()

    def get_dev_class(self, dev_name):
        """Returns a string with the class name for a device."""

        if dev_name in self._supported_dev_dict.keys():
            return self._supported_dev_dict[dev_name]['class']
        else:
            msg = ('Unsupported radio device {rd}.'
                   ' Choose one of:{dl}').format(rd=dev_name,
                                                 dl=self.get_supported_devs())
            raise RadioSourceSupportedDevsError(msg)


class RadioSource(object):
    """Define a radio source.
    This usually relates to the radio hardware
    """

    _gr_top_block = None

    # set the spectrum limits to RF
    _radio_spectrum = dia_aux.RadioSpectrum()
    _cap_freq_min = _radio_spectrum.get_lower_frequency()
    _cap_freq_max = _radio_spectrum.get_upper_frequency()

    # set center frequency halfway between min and max
    _center_freq = _cap_freq_max - ((_cap_freq_max
                                     - _cap_freq_min) / 2)

    # define a human readable type for this source
    _type = 'base_radio_source'

    # configure the hardware device for this source
    _source_args = ''

    # define the bandwidth capability for this
    _cap_bw = 1000

    # Id of the radio source, will be set by __init__
    _id = ''

    # list of frequency listeners
    _listeners = dia_aux.FreqListeners()

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

    _tap_directory = None

    _radio_state = RadioSourceSate.STATE_PRE_INIT

    _radio_source = None

    _create_fft_tap = False

    _freq_analyzer_tap = None

    # FFT definitions
    _log_fft = None
    _fft_size = 1024
    _fft_ref_scale = 2
    _fft_frame_rate = 30
    _fft_avg_alpha = 1.0
    _fft_average = False

    # probe poll rate in hz
    _probe_poll_rate = 10
    _fft_signal_level = None

    _status = 'PRE_INIT'

    _audio_enable = False
    _spectrum_analyzer_enable = False

    _probe_stop = threading.Event()

    _audio_sink = None
    _audio_sink_connection_qty = 0

    _retrieve_fft_thread = None

    _subprocess_in = Queue()
    _subprocess_out = None

    _source_subprocess = None

    _fft_signal_probe = None

    _log_dir_path = None

    _tap_dir_path = None

    def __init__(self, conf, in_queue, out_queue, log_dir_path, tap_dir_path):
        """Initialize the radio source object.
        conf -- a dictionary with a valid configuration
                (use DiaConfParser to obtain a valid config)
        in_queue -- queue to be used as input for this radio source
        out_queue -- queue to be used as output for radio sources
        log_dir_path -- path where logs will be written
        tap_dir_path -- path where taps wil be created"""

        if (conf is not None and in_queue is not None
                and out_queue is not None and
                log_dir_path is not None and tap_dir_path is not None):
            self.configure(conf, in_queue, out_queue, log_dir_path,
                           tap_dir_path)
        else:
            msg = ('Incomplete initialization.conf:{c}, output queue:{q},'
                   ' log_dir_path:{lp},'
                   ' tap_dir_pat:{tp}').format(c=conf, q=out_queue,
                                               lp=log_dir_path,
                                               tp=tap_dir_path)
            raise RadioSourceError(msg)

    def configure(self, conf, in_queue, out_queue, log_dir_path, tap_dir_path):
        """Configure the radio source object.
        conf -- a dictionary with a valid configuration
                (use DiaConfParser to obtain a valid config)
        in_queue -- queue to be used as input for this radio source
        out_queue -- queue to be used as output for radio sources
        log_dir_path -- path where logs will be written
        tap_dir_path -- path where taps wil be created"""

        self.set_log_dir_path(log_dir_path)
        self.set_tap_dir_path(tap_dir_path)
        self.set_ouptut_queue(out_queue)
        self.set_input_queue(in_queue)

        self.set_id(conf['id'])

        self.set_audio_enable(conf['audio_output'])

        # radio must be initialized before setting the center
        self._radio_init()
        self.start()
        self.set_frequency(conf['frequency'])

        self._source_args = conf['conf']
#         self._source_args = "numchan=" + str(1) + " " + ''

        msg = ('Initialized with type:{t}, cap_bw:{cb}, cap_freq_min:{cfmin},'
               ' cap_freq_max:{cfmax}, center_freq:{cf},'
               ' id:{id}').format(t=self._type, cb=self._cap_bw,
                                  cfmin=self._cap_freq_min,
                                  cfmax=self._cap_freq_max,
                                  cf=self._center_freq, id=self.get_id())
        logging.debug(msg)

        # configure listeners
        self._listeners.configure(conf['listeners'], self, tap_dir_path)

    def _radio_init(self):
        """Initialize the radio hw."""

        self._gr_top_block = gr.top_block()
        # specific radio initialization to be added on this method on derived
        # classes
        self._radio_state = RadioSourceSate.STATE_OK

    def _setup_rf_fft(self):
        """Setup an fft to check the RF status."""

        # start the fft
        try:
            self._log_fft = logpwrfft.logpwrfft_c(
                sample_rate=self._cap_bw,
                fft_size=self._fft_size,
                ref_scale=self._fft_ref_scale,
                frame_rate=self._fft_frame_rate,
                avg_alpha=self._fft_avg_alpha,
                average=self._fft_average
            )
        except Exception, exc:
            msg = ('Failed setting up fft with'
                   ' {m}').format(m=str(exc))
            logging.debug(msg)
            raise Exception(msg)

        msg = ('Radio source {id} FFT set up '
               'completed.').format(id=self.get_id())
        logging.debug(msg)

        # connect the fft to the top block
        try:
            self._gr_top_block.connect(self.get_source_block(),
                                       self._log_fft)
        except Exception, exc:
            msg = ('Failed to connect the fft to the source, with:'
                   ' {m}').format(m=str(exc))
            logging.debug(msg)
            raise Exception(msg)

        msg = 'FFT connected to Frequency translation.'
        logging.debug(msg)

    def _retrieve_fft(self, stop_event):
        """Retrieve fft values"""

        low_freq = self.get_lower_frequency()
        high_freq = self.get_upper_frequency()
        band_w = self.get_bandwidth_capability()

        while not stop_event.is_set():

            # TODO: fft value processing should go here

            current_time = datetime.utcnow().isoformat()

            # logpower fft swaps the lower and upper halfs
            # of the spectrum, this fixes it
            vraw = self._fft_signal_probe.level()
            val = vraw[len(vraw)/2:]+vraw[:len(vraw)/2]

            # update taps
            if self.get_spectrum_analyzer_tap_enable():
                tap_value = '{t};{bw};{lf};{hf};{v}\n'.format(t=current_time,
                                                              v=val, bw=band_w,
                                                              lf=low_freq,
                                                              hf=high_freq)

                self._freq_analyzer_tap.update_value(tap_value)

                msg = 'updating data tap'
                logging.debug(msg)

            stop_event.wait(1.0 / self._probe_poll_rate)

    def _setup_freq_analyzer_tap(self):
        """Setup a tap to provide live frequency analyzer plot.
        Create a named pipe containing the latest set of fft values.
        Will output to a previously created named pipe/file.
        If an error occurs while creating the named pipe (other than that the
        file already exists), tap output thread will not be started."""

        msg = 'Setting up fft tap.'
        logging.debug(msg)

        try:
            self._freq_analyzer_tap = dia_aux.DataTap(self.get_id())
        except Exception, exc:
            msg = 'Failed to setup tap for FFT with:{m}'.format(m=str(exc))
            logging.error(msg)
            raise

        msg = 'Radio Source {id} FFT tap setup done.'.format(id=self.get_id())
        logging.debug(msg)

    def _teardown_freq_analyzer_tap(self):
        """Cleanup the live fft values tap.
        Will remove the tap file from the file system"""

        # stop the thread

        self._freq_analyzer_tap.stop()

    def _setup_rf_fft_probe(self):
        """Setup probe to retrieve the fft data"""

        try:
            self._fft_signal_probe = blocks.probe_signal_vf(self._fft_size)
        except Exception, exc:
            msg = ('Failed to create fft probe, with:'
                   ' {m}').format(m=str(exc))
            logging.debug(msg)
            raise Exception(msg)

        # connect the signal probe to the fft
        try:
            self._gr_top_block.connect(self._log_fft,
                                       self._fft_signal_probe)
        except Exception, exc:
            msg = ('Failed to connect the fft to radio source {id}, with:'
                   ' {m}').format(id=self.get_id(), m=str(exc))
            logging.debug(msg)
            raise Exception(msg)

        msg = ('Radio Source {id}, Launching fft data retrieval'
               ' thread.').format(id=self.get_id())
        logging.debug(msg)

        # set the fft retrieval on it's own thread
        self._retrieve_fft_thread = threading.Thread(target=self._retrieve_fft,
                                                     name=self.get_id(),
                                                     args=(self._probe_stop,))
        self._retrieve_fft_thread.daemon = True
        self._retrieve_fft_thread.start()

        msg = ('Radio Source {id} signal probe setup'
               ' done.').format(id=self.get_id())
        logging.debug(msg)

    def _stop_signal_probe(self):
        """Stop the fft data probe"""

        # send the stop event to the thread
        self._probe_stop.set()

    def set_log_dir_path(self, log_dir_path):
        """Set the probe's log path
        log_dir_path - path to the logs directory"""

        self._log_dir_path = log_dir_path

    def set_tap_dir_path(self, tap_dir):
        """Set the probe's tap directory
        tap_dir - path to the tap directory"""

        self._tap_dir_path = tap_dir

    def get_log_dir_path(self):
        """Return the probe's log directory path"""

        return self._log_dir_path

    def get_tap_dir_path(self):
        """Return the probe's tap directoty path"""

        return self._tap_dir_path

    def set_ouptut_queue(self, queue):
        """Set this radio source's output queue
        queue -- the output queue (multiprocessing.Queue)"""

        type_queue = type(queue)
        print 'qt={qt}'.format(qt=type_queue)

        # check if we were given an object of the right type
        if not isinstance(queue, multiprocessing.queues.Queue):

            msg = ('Queue must be a queue of multiprocessing.queues.Queue,'
                   ' was {tgtb}').format(tgtb=type_queue)
            raise TypeError(msg)

        self._subprocess_out = queue
        msg = 'output queue set to:{q}'.format(q=queue)
        logging.debug(msg)

    def set_input_queue(self, queue):
        """Set this radio source's input queue
        queue -- the output queue (multiprocessing.Queue)"""

        type_queue = type(queue)

        # check if we were given an object of the right type
        if not isinstance(queue, multiprocessing.queues.Queue):

            msg = ('Queue must be a queue of multiprocessing.queues.Queue,'
                   ' was {tgtb}').format(tgtb=type_queue)
            raise TypeError(msg)

        self._subprocess_in = queue
        msg = 'input queue set to:{q}'.format(q=queue)
        logging.debug(msg)

    def set_id(self, radio_source_id):
        """Sets the radio source's  id.
        Converts alphabetic characters to lower case.
        radio_source_id -- the frequency listener id.
                        Acceptable characters: ASCII characters, numbers,
                        underscore, dash."""

        if radio_source_id == '':
            msg = 'Radio source id is empty'
            logging.error(msg)
            raise dia_aux.BadIdError(msg)
        if all(character in ascii_letters+digits+'_'+'-'
               for character in radio_source_id):
            self._id = radio_source_id.lower()
            msg = 'id set to {i}'.format(i=radio_source_id.lower())
            logging.debug(msg)
        else:
            msg = 'Frequency id contains contains unacceptable characters'
            logging.error(msg)
            raise dia_aux.BadIdError(msg)

    def set_tap_directory(self, path):
        """Set the directory where tap files should be written to.
        path -- full path to the directory"""

        if path is None:
            msg = 'Tap path not set.'
            raise RadioSourceError(msg)

        # check if path is absolute
        if os.path.isabs(path):
            tmp_tap_directory = path
            msg = 'Tap directory is absolute'
            logging.debug(msg)
        else:
            # path is relative

            # check if it is to be the current directory
            if path in ['.', './']:
                tmp_tap_directory = os.getcwd()
                msg = 'Tap directory is cwd'
                logging.debug(msg)
            else:
                tmp_tap_directory = os.path.join(os.getcwd(), path)

        msg = 'Requested tap directory is {td}'.format(td=tmp_tap_directory)
        logging.debug(msg)

        #  check if path exists and is writable
        if not os.path.isdir(tmp_tap_directory):
            msg = ("Tap directory {td} does not exist or isn't"
                   " a directory").format(td=tmp_tap_directory)
            raise RadioSourceError(msg)

        if not os.access(tmp_tap_directory, os.W_OK):
            msg = ("Tap directory {td} is not"
                   " writable").format(td=tmp_tap_directory)
            raise RadioSourceError(msg)

        self._tap_directory = tmp_tap_directory

    def set_frequency(self, frequency):
        """Set the source's center frequency
        frequency -- frequency in Hz (integer)"""

        src_minimum_freq = self.get_minimum_frequency()
        src_maximum_freq = self.get_maximum_frequency()

        frequency = int(float(frequency))

        if not float(frequency).is_integer():
            msg = 'Frequency is not a whole number'
            logging.error(msg)
            raise ValueError(msg)
        elif frequency < src_minimum_freq or frequency > src_maximum_freq:
            msg = ('Frequency must be above {fl} hz '
                   'and below {fu} hz').format(fl=src_minimum_freq,
                                               fu=src_maximum_freq)
            logging.error(msg)
            raise ValueError(msg)

        self._center_freq = int(frequency)

        # tune the frequency
        self._radio_source.set_center_freq(frequency, 0)
        msg = 'Radio source frequency set and tuned to {i}'.format(i=frequency)
        logging.debug(msg)

        msg = ('Receiver {id} set center frequency at '
               '{f}').format(id=self.get_id(), f=self.get_center_frequency())
        logging.debug(msg)

        # TODO:  iterate the list of listeners and re-set the offset, to cover case when frequency is re-set when listeners are already working

    def set_audio_enable(self, audio_enable=True):
        """Set True if the audio sink is to be enabled, false otherwise.
        enable -- boolean (Default is True/enabled)"""

        if isinstance(audio_enable, bool):
            self._audio_enable = audio_enable
        else:
            msg = 'audio_enable must be a boolean'
            raise TypeError(msg)
        msg = ('Radio source {id} audio output enabled set to'
               ' {val}').format(val=audio_enable, id=self.get_id())
        logging.debug(msg)

    def set_spectrum_analyzer_tap_enable(self, create_tap=True):
        """Set True if the source frequency analyzer is to be enabled,
        false otherwise.
        enable -- boolean (Default is True/enabled)"""

        if self.get_tap_directory() is None:
            create_tap = False
            msg = 'Tap directory not set. Spectrum analyzer not available'
            logging.warning(msg)

        if isinstance(create_tap, bool):
            self._spectrum_analyzer_enable = create_tap
        else:
            msg = 'enable must be a boolean'
            raise TypeError(msg)
        msg = ('Radio source {id} frequency analyzer tap creation set to'
               ' {val}').format(val=create_tap, id=self.get_id())
        logging.debug(msg)

    def add_frequency_listener(self, listener):
        """Add a FreqListener to this Radio Source's listener list.
        listener -- FreqListener"""

        if listener.get_upper_frequency() > self._cap_freq_max:
            msg = ("The listener's upper frequency ({lf}) is above the "
                   "radio source's maximum frequency ({mf})").format(
                       lf=listener.get_upper_frequency(),
                       mf=self._cap_freq_max)
            logging.error(msg)
            raise RadioSourceFrequencyOutOfBoundsError(msg)

        if listener.get_lower_frequency() < self._cap_freq_min:
            msg = ("The listener's lower frequency ({lf}) is below the "
                   "radio source's minimum frequency"
                   " ({mf})").format(lf=listener.get_lower_frequency(),
                                     mf=self._cap_freq_min)
            logging.error(msg)
            raise RadioSourceFrequencyOutOfBoundsError(msg)

        # pass the radio source object
        # this will also set the gr_top_block and frequency offset
        # on this listener
        listener.set_radio_source(self)

        self._listeners.append(listener)
        msg = 'FreqListener {i} added to list'.format(i=listener)
        logging.debug(msg)

    def get_spectrum_analyser_tap_enable(self):
        """Return True if the spectrum analyzer tap is
        to be enabled."""
        return self._spectrum_analyzer_enable

    def get_input_pipe(self):
        """Return the input pipe for the listener."""

        return self._subprocess_in

    def get_output_pipe(self):
        """Return the output pipe for the listener."""

        return self._subprocess_out

    def get_id(self):
        """Returns the radio source's id."""
        return self._id

    def get_maximum_frequency(self):
        """Return the maximum frequency on this radio source."""
        return self._cap_freq_max

    def get_minimum_frequency(self):
        """Return the minimum frequency on this radio source."""
        return self._cap_freq_min

    def get_upper_frequency(self):
        """Computes and retrieves the upper frequency of the source,
        taking into account the frequency and the bandwidth."""

        return self._center_freq + (self._cap_bw/2)

    def get_lower_frequency(self):
        """Computes and retrieves the lower frequency of the source,
        taking into account the frequency and the bandwidth."""

        return self._center_freq - (self._cap_bw/2)

    def get_bandwidth_capability(self):
        """Return the bandwidth capability for this radio source."""
        return self._cap_bw

    def get_tap_directory(self):
        """Return the path to where taps are to be written"""
        return self._tap_directory

    def get_type(self):
        """Return the type of this radio source."""
        return self._type

    def get_center_frequency(self):
        """Return the center frequency for this source."""
        return self._center_freq

    def get_listener_id_list(self):
        """Return a list of listener ids configured on this source"""
        return self._listeners.get_listener_id_list()

    def get_audio_enable(self):
        """Return True if the audio sink is to be enabled."""
        return self._audio_enable

    def get_source_block(self):
        """Return the gnu radio source block"""

        if self._radio_state == RadioSourceSate.STATE_OK:
            return self._radio_source
        else:
            msg = 'Radio Source not started'
            raise RadioSourceRadioFailureError(msg)

    def get_gr_top_block(self):
        """Retrieve the Gnu radio top block for this source"""

        if self._radio_state == RadioSourceSate.STATE_OK:
            return self._gr_top_block
        else:
            msg = 'Radio Source not started'
            raise RadioSourceRadioFailureError(msg)

    def get_spectrum_analyzer_tap_enable(self):
        """Return True if the spectrum analyzer tap is to be enabled."""
        return self._spectrum_analyzer_enable

    def get_subprocess(self):
        """Return the handle to the Radio Source's subprocess."""

        if self._source_subprocess is not None:
            return self._source_subprocess
        else:
            msg = 'Radio Source subprocess not set'
            logging.debug(msg)

    def send_data(self, data):
        """Sends data output to the output pipe.
        data -- data to send"""

        # prepend with the source id
        out_data = self.get_id() + ':' + data
        self._subprocess_out.put(out_data)
        msg = 'sending data to parent:{d}'.format(d=out_data)
        logging.debug(msg)

    def _run_source_subprocess(self, input_conn, output_conn):
        """start the subprocess for a  source.
        input_conn - input pipe
        output_conn - output pipe"""

        if self.get_audio_enable():
            # for development purposes, output sound
            self.start_audio_sink()

        # handle frequency analyzer tap creation
        # thread for data tap must be present before
        # the thread that starts the signal probe
        if self.get_spectrum_analyzer_tap_enable():

            # setup fft and connect it to the source
            try:
                self._setup_rf_fft()
            except Exception, exc:
                msg = ('Failed to setup RF FFT'
                       'with {m}').format(m=str(exc))
                logging.debug(msg)
                raise Exception(msg)
            msg = ('Radio Source {id}, fft setup '
                   'finished').format(id=self.get_id())
            logging.debug(msg)

            try:
                self._setup_freq_analyzer_tap()
            except Exception, exc:
                msg = ('Failed to setup fft TAP'
                       'with {m}').format(m=str(exc))
                logging.debug(msg)
                raise Exception(msg)

            try:
                self._setup_rf_fft_probe()
            except Exception, exc:
                msg = ('Failed to setup signal probe'
                       'with {m}').format(m=str(exc))
                logging.debug(msg)
                raise Exception(msg)

            msg = ('Radio Source {id}, spectrum analyzer setup '
                   'finished').format(id=self.get_id())
            logging.debug(msg)

        else:
            msg = ('Radio Source {id}, spectrum analyzer not '
                   'requested').format(id=self.get_id())
            logging.debug(msg)

        msg = ('radio source subprocess for {id}'
               ' starting.').format(id=self.get_id())
        logging.debug(msg)

        output_conn.put(msg)

        stop = False

        msg = 'starting frequency listeners'
        logging.debug(msg)

        self.start_frequency_listeners()

        # wait for the end of the top block
        self._gr_top_block.start()

        # wait for the stop command
        while not stop:

            input_cmd = input_conn.get()

            if input_cmd == 'STOP':
                stop = True

        if stop:
            self.stop_frequency_listeners()
            self._gr_top_block.stop()
            self._source_subprocess.terminate()

        msg = ('radio source subprocess for {id}'
               ' exiting.').format(id=self.get_id())
        logging.debug(msg)
        output_conn.send(msg)

    def start(self):
        """Start the radio source.
        Returns the handle to the subprocess."""

        # setup and start the subprocess for this source

        self._source_subprocess = Process(target=self._run_source_subprocess,
                                          args=(self._subprocess_in,
                                                self._subprocess_out))

        try:
            self._source_subprocess.start()
        except Exception, exc:
            msg = ('Failed starting the source subprocesses with:'
                   ' {m}').format(m=str(exc))
            logging.debug(msg)
            raise

    def stop(self):
        """Stop the radio listener"""
        msg = 'Stopping radio source {id}'.format(id=self.get_id())
        logging.debug(msg)

        self._subprocess_in.put('STOP')

    def stop_frequency_listeners(self):
        """Stop  individual frequency listeners."""

        msg = ('Stopping all frequency listeners for'
               'source {s}').format(s=self.get_id())
        logging.info(msg)

        self._listeners.stop()

    def start_frequency_listeners(self):
        """Start individual frequency listeners"""

        msg = ('Starting all frequency listeners for'
               'source {s}').format(s=self.get_id())
        logging.info(msg)
        # iterate through the listeners and start them
        self._listeners.start()

    def start_audio_sink(self):
        """Start an audio sink for this source."""

        samp_rate = 48e3

        self._audio_sink = audio.sink(int(samp_rate), '', True)

        msg = ('started audio sink with sample rate of '
               '{sr}').format(sr=samp_rate)
        logging.debug(msg)

        # pass audio sink to listeners
        self._listeners.set_audio_sink(self._audio_sink)

    def get_audio_sink(self):
        """Returns the instance's audio sink."""
        return self._audio_sink

    def get_audio_sink_connection_qty(self):
        """Get the number of connections to the audio sink"""

        return self._audio_sink_connection_qty

    def add_audio_sink_connection(self):
        """Get an audio sink connection handler"""

        self._audio_sink_connection_qty += 1

        # first connection is 0
        return self._audio_sink_connection_qty - 1

    def remove_audio_sink_connection(self):
        """Remove an audio sink connection handler"""

        if self._audio_sink_connection_qty > 0:
            self._audio_sink_connection_qty -= 1
        else:
            msg = 'Audio sink connection quantity is already at 0'
            logging.error(msg)
            raise ValueError(msg)

    def do_snd_output(self):
        """Configure for sound output of the center frequency"""

        msg = '------->>>>>> start audio sink'
        logging.debug(msg)
        self.start_audio_sink()

        msg = '------->>>>>> start fm demod'
        logging.debug(msg)

        self._fm_demod()

        msg = '------->>>>>> startED fm demod'
        logging.debug(msg)

    def _fm_demod(self):
        """Do an FM demodulation for the center frequency on this source"""

        samp_rate = 500000

        rational_resampler_a = grfilter.rational_resampler_ccc(
            interpolation=int(samp_rate),
            decimation=int(self.get_bandwidth_capability()),
            taps=None,
            fractional_bw=None,
        )

        filter_taps = firdes.low_pass(1, analog, samp_rate, 100e3, 1e3)

        self._gr_top_block.connect((self._radio_source, 0),
                                   (rational_resampler_a, 0))

        msg = ('type of self._radio_source:'
               ' {trs}').format(trs=type(self._radio_source))
        logging.debug(msg)

        freq_xlating_fir_filter = grfilter.freq_xlating_fir_filter_ccc(1, (filter_taps), 0, samp_rate)

        self._gr_top_block.connect((rational_resampler_a, 0),
                                   (freq_xlating_fir_filter, 0))

        analog_wfm_rcv = analog.wfm_rcv(
            quad_rate=samp_rate,
            audio_decimation=10,
        )

        self._gr_top_block.connect((freq_xlating_fir_filter, 0),
                                   (analog_wfm_rcv, 0))

        rational_resampler_b = grfilter.rational_resampler_fff(
            interpolation=48,
            decimation=50,
            taps=None,
            fractional_bw=None,
        )

        self._gr_top_block.connect((analog_wfm_rcv, 0),
                                   (rational_resampler_b, 0))

        blocks_multiply_const = blocks.multiply_const_vff((1, ))

        self._gr_top_block.connect((rational_resampler_b, 0),
                                   (blocks_multiply_const, 0))

        # connect to audio sink
        audio_sink_connection = self.add_audio_sink_connection()
        self._gr_top_block.connect((blocks_multiply_const, 0),
                                   (self.get_audio_sink(),
                                    audio_sink_connection))

        msg = 'started demodulation'
        logging.debug(msg)


class RTL2838RadioSource(RadioSource):
    """Defines a radio source hardware with  RTL2838 receiver
     and a R820T2 tuner."""

    _type = 'RTL2838'
    _cap_bw = 2400000

    # TODO: get the range using osmosdr.get_freq_range()
    _cap_freq_min = 25000
    _cap_freq_max = 1750000000
    _center_freq = _cap_freq_max - ((_cap_freq_max
                                     - _cap_freq_min) / 2)
    _freq_corr = 0
    _dc_offset_mode = 0
    _iq_balance_mode = 0
    _gain_mode = False
    _iq_gain_mode = 0
    _gain = 10
    _af_gain = 1
    _bb_gain = 20
    _antenna = ''
    _bandwith = 0

    def __init__(self, conf, in_queue, out_queue, log_dir_path, tap_dir_path):
        """Initialize the radio source object.
        conf -- a dictionary with a valid configuration
                (use DiaConfParser to obtain a valid config)
        in_queue -- queue to be used as input for this radio source
        out_queue -- queue to be used as output for radio sources
        log_dir_path -- path where logs will be written
        tap_dir_path -- path where taps wil be created"""

        super(RTL2838RadioSource, self).__init__(conf, in_queue,
                                                 out_queue, log_dir_path,
                                                 tap_dir_path)

        msg = ('Initialized with type:{t}, cap_bw:{cb}, cap_freq_min:{cfmin},'
               ' cap_freq_max:{cfmax}, center_freq:{cf},'
               ' id:{id}').format(t=self._type, cb=self._cap_bw,
                                  cfmin=self._cap_freq_min,
                                  cfmax=self._cap_freq_max,
                                  cf=self._center_freq, id=self.get_id())
        logging.debug(msg)

    def _radio_init(self):
        """Initialize the radio hw."""
        super(RTL2838RadioSource, self)._radio_init()

        try:
            self._radio_source = osmosdr.source(self._source_args)
            # TODO: find a way to check if osmosdr.source init is successful
        except Exception, exc:
            msg = ('Failed to start source with:'
                   ' {m}').format(m=str(exc))
            logging.error(msg)
            msg = sys.exc_info()
            logging.error(msg)
            raise

        radio_init_sucess = True

        if radio_init_sucess:
            self._radio_source.set_sample_rate(self.get_bandwidth_capability())
            self._radio_source.set_center_freq(self.get_center_frequency(), 0)
            self._radio_source.set_freq_corr(0, 0)
            self._radio_source.set_dc_offset_mode(0, 0)
            self._radio_source.set_iq_balance_mode(0, 0)
            self._radio_source.set_gain_mode(False, 0)
            self._radio_source.set_gain(10, 0)
            self._radio_source.set_if_gain(1, 0)
            self._radio_source.set_bb_gain(20, 0)
            self._radio_source.set_antenna('', 0)
            self._radio_source.set_bandwidth(0, 0)

            self._radio_state = RadioSourceSate.STATE_OK
        else:
            self._radio_state = RadioSourceSate.STATE_FAILED
            msg = 'Radio initialization failed'
            raise RadioSourceRadioFailureError(msg)

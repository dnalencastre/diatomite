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


import os
import logging as log
import datetime
import threading
import exceptions
import errno
from multiprocessing import Process, Pipe
from string import ascii_letters, digits
from operator import isNumberType
import osmosdr
import sys
import numpy
from gnuradio import gr
from gnuradio import blocks
from gnuradio import filter as grfilter
from gnuradio.fft import logpwrfft
from gnuradio import audio
from gnuradio.filter import firdes
from gnuradio import analog


class FreqListenerInvalidModulationError(Exception):
    """Raised when  a FreqListener is passed an invalid modulation."""
    pass


class RadioSourceFrequencyOutOfBoundsError(Exception):
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


class RadioSourceSate(object):
    """Define possible states for a radio a receiver."""
    STATE_PRE_INIT = 0
    STATE_OK = 1
    STATE_FAILED = 2


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

    _decimation = 1
    _samp_rate = 500000
    _transition_bw = 2000
    _filter_taps = None
    _radio_source_bw = 0
    _radio_source_block = None
    _gr_top_block = None

    _log_fft = None
    _fft_size = 1024
    _fft_ref_scale = 2
    _fft_frame_rate = 30
    _fft_avg_alpha = 1.0
    _fft_average = False

    # probe poll rate in hz
    _probe_poll_rate = 10

    # Signal power threshold to determine if it's transmitting.
    _signal_pwr_threshold = None

    _create_fft_tap = False
    _spectrum_analyzer_enable = False

    # write the taps to the current directory
    _tap_directory = os.getcwd()

    _freq_analyzer_tap = None

    _status = 'PRE_INIT'

    _probe_stop = threading.Event()

    _audio_enable = False

    _radio_source = None

    _audio_sink = None

    _freq_translation_filter_input = None
    _freq_translation_filter_output = None

    _retrieve_fft_thread = None

    # frequency offset from the radio source
    _frequency_offset = 0

    _fft_signal_probe = None

    def __init__(self, listener_id):
        """init the FreqListener
        listener_id -- the frequency listener id.
                Acceptable characters: ASCII characters, numbers,
                underscore, dash."""

        self.set_id(listener_id)

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

    def set_radio_source(self, radio_source):
        """Sets the radio source to which this listener is connected to.
        radio_soure -- object of RadioSource class"""
        if isinstance(radio_source, RadioSource):
            self._radio_source = radio_source
        else:
            msg = 'radio_source must be a RadioSource object'
            raise TypeError(msg)
        msg = ('Listener {id} set to radios source'
               ' {rs}').format(rs=radio_source, id=self.get_id())
        log.debug(msg)

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

        self._frequency_offset = (radio_source_center_frequency -
                                  self._frequency) * - 1

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
            raise FreqListenerInvalidModulationError(msg)

    def set_source_block(self, source_block):
        """Set the gnu radio source block.
        source_block -- the gr source block of type
            osmosdr.osmosdr_swig.source_sptr"""

        type_source_block = type(source_block)

        # check if we were given an object of the right type
        if not type_source_block == osmosdr.osmosdr_swig.source_sptr:
            msg = ('radio source block must be of type '
                   ' osmosdr.osmosdr_swig.source_sptr,'
                   ' was {tsb}.').format(tsb=type_source_block)
            log.error(msg)
            raise TypeError(msg)
        else:
            self._radio_source_block = source_block
            msg = 'Radio Source block set.'
            log.debug(msg)

    def set_gr_top_block(self, gr_top_block):
        """Set the gnu radio top block.
        gr_top_block -- the gr top block of gr.top_block"""

        type_gr_top_block = type(gr_top_block)

        # check if we were given an object of the right type
        if not type_gr_top_block == gr.top_block:
            msg = ('gr_top_block must be of type gr.top_block,'
                   ' was {tgtb}').format(tgtb=type_gr_top_block)
            raise TypeError(msg)

        self._gr_top_block = gr_top_block
        msg = 'Top block set.'
        log.debug(msg)

    def set_spectrum_analyzer_tap_enable(self, create_tap=True):
        """Set True if the source frequency analyzer is to be enabled,
        false otherwise.
        enable -- boolean (Default is True/enabled)"""

        if isinstance(create_tap, bool):
            self._spectrum_analyzer_enable = create_tap
        else:
            msg = 'create_fft_tap must be a boolean'
            raise TypeError(msg)
        msg = ('Radio source {id} FFT tap creation set to'
               ' {v}').format(v=create_tap, id=self.get_id())
        log.debug(msg)

    def set_audio_sink(self, audio_sink):
        """Set the audio sink for sound output
        audio_sink -- the audio sink to use"""
        self._audio_sink = audio_sink

    def set_audio_output(self, audio_enable=True):
        """Set True if audio output is to be enabled, false otherwise.
        enable -- boolean (Default is True/enabled)"""

        if isinstance(audio_enable, bool):
            self._audio_enable = audio_enable
        else:
            msg = 'audio_enable must be a boolean'
            raise TypeError(msg)
        msg = ('Radio source {id} audio output enabled set to'
               ' {v}').format(v=audio_enable, id=self.get_id())
        log.debug(msg)

    def set_radio_source_bw(self, radio_source_bw):
        """set the radio source bandwidth for this frequency listener"""
        self._radio_source_bw = radio_source_bw

    def set_signal_pwr_threshold(self, pwr_threshold):
        """ set the threshold above which the signal is considered present
        pwr_threshold - the threshold, a negative number
        This number should be above the noise floor for the frequency, and
        can be determined by looking at the frequency analyzer and choosing
        a level between the noise floor and the peak of the signal.
        """
        if isNumberType(pwr_threshold):
            if pwr_threshold < 0:
                self._signal_pwr_threshold = pwr_threshold

    def get_audio_enable(self):
        """Return True if the audio output is to be enabled."""
        return self._audio_enable

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
        """Get the radio source bandwidth for this frequency listener."""
        return self._radio_source_bw

    def get_audio_sink(self):
        """Returns the instance's audio sink."""
        return self._audio_sink

    def get_signal_pwr_threshold(self):
        """ set the threshold above which the signal is considered present."""
        return self._signal_pwr_threshold

    def _config_frequency_translation(self):
        """Configure the frequency translation filter."""

        filter_samp_rate = 500e3
        gain = 1
        cutoff_freq = filter_samp_rate/(2 * self._decimation)
        _filter_taps = grfilter.firdes.low_pass(gain,
                                                filter_samp_rate,
                                                cutoff_freq,
                                                self._transition_bw)

        self._freq_translation_filter_input = (
            grfilter.freq_xlating_fir_filter_ccc(self._decimation,
                                                 (_filter_taps),
                                                 self.get_frequency_offset(),
                                                 self.get_radio_source_bw()))

        r_resampler = grfilter.rational_resampler_ccc(
                interpolation=int(filter_samp_rate),
                decimation=int(self.get_radio_source_bw()),
                taps=None,
                fractional_bw=None,
        )

        try:
            self._gr_top_block.connect(self._freq_translation_filter_input,
                                       r_resampler)
        except Exception, exc:
            msg = ('Failed connecting input filter to rational resampler'
                   ' {m}').format(m=str(exc))
            log.debug(msg)
            raise

        msg = 'Input filter connected to rational resampler.'
        log.debug(msg)

        self._freq_translation_filter_output = (
            grfilter.freq_xlating_fir_filter_ccc(self._decimation,
                                                 (_filter_taps),
                                                 0,
                                                 filter_samp_rate))
        try:
            self._gr_top_block.connect(r_resampler,
                                       self._freq_translation_filter_output)
        except Exception, exc:
            msg = ('Failed connecting rational resampler to output filter'
                   ' {m}').format(m=str(exc))
            log.debug(msg)
            raise

        msg = 'Input rational resampler connected to output filter.'
        log.debug(msg)

        msg = 'Frequency translation set.'
        log.debug(msg)

    def get_spectrum_analyser_tap_enable(self):
        """Return True if the spectrum analyser tap is
        to be enabled."""
        return self._spectrum_analyzer_enable

    def _connect_frequency_translator_to_source(self):
        """Connect the frequency translation filter to the source.
        """

        try:
            self._gr_top_block.connect(self._radio_source_block,
                                       self._freq_translation_filter_input)
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
            self._log_fft = logpwrfft.logpwrfft_c(
                sample_rate=self._samp_rate,
                fft_size=self._fft_size,
                ref_scale=self._fft_ref_scale,
                frame_rate=self._fft_frame_rate,
                avg_alpha=self._fft_avg_alpha,
                average=self._fft_average
            )
        except Exception, exc:
            msg = ('Failed setting up fft for listener {id} with'
                   ' {m}').format(id=self.get_id(), m=str(exc))
            log.debug(msg)
            raise Exception(msg)

        msg = ('Listener {id} FFT set up '
               'completed.').format(id=self.get_id())
        log.debug(msg)

        # connect the fft to the freq translation filter
        try:
            self._gr_top_block.connect(self._freq_translation_filter_output,
                                       self._log_fft)
        except Exception, exc:
            msg = ('Failed to connect the fft to freq translation, with:'
                   ' {m}').format(m=str(exc))
            log.debug(msg)
            raise Exception(msg)

        msg = 'FFT connected to Frequency translation.'
        log.debug(msg)

    def _check_signal_present(self, fft_val):
        """Check if the signal is present by comparing the power to the power
        threshold, evaluating the average level on a slice of the FFT around
        the center frequency.
        fft_val -- fft tuple/array to be checked
        """

        # slice lenght to evaluate (%)
        slice_percentage = 10

        fft_len = len(fft_val)

        slice_len = (fft_len * slice_percentage) / 100

        slice_start = (fft_len / 2) - int(slice_len / 2)
        slice_end = (fft_len / 2) + int(slice_len / 2)

        # compute average for the slice
        signal_avg = numpy.mean(fft_val[slice_start:slice_end])

        if signal_avg >= self.get_signal_pwr_threshold():
            self.notify_signal_present(signal_avg)
        else:
            self.notify_signal_absent(signal_avg)

    def notify_signal_present(self, signal_level):
        """Notify that the signal is present and the current level
        signal_level -- the signal level in DBm"""

        msg = 'Signal is PRESENT. Level {lvl} DBm'.format(lvl=signal_level)
        log.debug(msg)
        # TODO: pass the notification to the receiver

    def notify_signal_absent(self, signal_level):
        """Notify that the signal is absent and the current level
        signal_level -- the signal level in DBm"""

        msg = 'Signal is ABSENT. Level {lvl} DBm'.format(lvl=signal_level)
        log.debug(msg)
        # TODO: pass the notification to the receiver

    def _retrieve_fft(self, stop_event):
        """Retrieve fft values"""

        low_freq = self.get_lower_frequency()
        high_freq = self.get_upper_frequency()
        bw = self.get_bandwidth()

        while not stop_event.is_set():

            current_time = datetime.datetime.utcnow().isoformat()

            # logpower fft swaps the lower and upper halfs of
            # the spectrum, this fixes it
            vraw = self._fft_signal_probe.level()
            val = vraw[len(vraw)/2:]+vraw[:len(vraw)/2]

            # check if the signal is present
            self._check_signal_present(val)

            # update taps
            if self.get_spectrum_analyser_tap_enable():
                tap_value = '{t};{bw};{lf};{hf};{v}\n'.format(t=current_time,
                                                              v=val, bw=bw,
                                                              lf=low_freq,
                                                              hf=high_freq)

                self._freq_analyzer_tap.update_value(tap_value)

                msg = 'updating data tap'
                log.debug(msg)

            stop_event.wait(1.0 / self._probe_poll_rate)

    def _setup_freq_analyzer_tap(self):
        """Setup a tap to provide live frequency analyzer values.
        Create a named pipe containing the latest set of fft values.
        Will output to a previously created named pipe/file.
        If an error occurs while creating the named pipe (other than that the
        file already exists), tap output thread will not be started."""

        msg = 'Setting up fft tap.'
        log.debug(msg)

        try:
            self._freq_analyzer_tap = DataTap(self.get_id())
        except Exception, exc:
            msg = 'Failed to setup tap for FFT with:{m}'.format(m=str(exc))
            log.error(msg)
            raise

        msg = 'Listener {id} FFT tap setup done.'.format(id=self.get_id())
        log.debug(msg)

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

        msg = ('Listener {id}, Launching fft data retrieval'
               ' thread.').format(id=self.get_id())
        log.debug(msg)

        # set the fft retrieval on it's own thread
        self._retrieve_fft_thread = threading.Thread(target=self._retrieve_fft,
                                                     name=self.get_id(),
                                                     args=(self._probe_stop,))
        self._retrieve_fft_thread.daemon = True
        self._retrieve_fft_thread.start()

        msg = ('Listener {id} signal probe setup'
               ' done.').format(id=self.get_id())
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
        if self.get_spectrum_analyser_tap_enable():
            try:
                self._setup_freq_analyzer_tap()
            except Exception, exc:
                msg = ('Failed to setup fft tap'
                       'with {m}').format(m=str(exc))
                log.debug(msg)
                raise Exception(msg)

        # obtain the fft values
        # this is needed even if the spectrum analyzer is not enabled
        try:
            self._setup_rf_fft_probe()
        except Exception, exc:
            msg = ('Failed to setup signal probe'
                   'with {m}').format(m=str(exc))
            log.debug(msg)
            raise Exception(msg)

        self._status = 'RUNNING'

        # start sound output
        if self.get_audio_enable():
            self.do_snd_output()

    def stop(self):
        """Stop the frequency listener """

        msg = 'stopping frequency listener {id}'.format(id=self.get_id())
        log.debug(msg)

        if self._status == 'RUNNING':

            if self.get_spectrum_analyser_tap_enable():
                # stop the fft tap
                try:
                    self._teardown_freq_analyzer_tap()
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

        # TODO: add the fft data retrieval

    def do_snd_output(self):
        """Configure for sound output for the listener"""

        msg = 'fm demod will start for listener {id}'.format(id=self.get_id())
        log.debug(msg)

        self._fm_demod()

        msg = 'fm demod started for listener {id}'.format(id=self.get_id())
        log.debug(msg)

    def _fm_demod(self):
        """Do an FM demodulation for this listener"""

        samp_rate = 500000

        analog_wfm_rcv = analog.wfm_rcv(
            quad_rate=samp_rate,
            audio_decimation=10,
        )

        self._gr_top_block.connect((self._freq_translation_filter_output, 0),
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
        audio_sink_connection = self._radio_source.add_audio_sink_connection()
        self._gr_top_block.connect((blocks_multiply_const, 0),
                                   (self._radio_source.get_audio_sink(),
                                    audio_sink_connection))

        msg = 'started demodulation'
        log.debug(msg)


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

    _gr_top_block = None

    # set the spectrum limits to RF
    _radio_spectrum = RadioSpectrum()
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
    _listener_list = FreqListenerList()

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

    _radio_state = RadioSourceSate.STATE_PRE_INIT

    _radio_source = None

    _create_fft_tap = False

    # write the taps to the current directory
    _tap_directory = os.getcwd()
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

    _audio_sink_enable = False
    _spectrum_analyzer_enable = False

    _probe_stop = threading.Event()

    _audio_sink = None
    _audio_sink_connection_qty = 0

    _retrieve_fft_thread = None

    _subprocess_in, _subprocess_out = Pipe()
    _source_subprocess = None

    _fft_signal_probe = None

    def __init__(self, radio_source_id):
        """Initialize the radio source object.
        radio_source_id -- the frequency listener id.
                        Acceptable characters: ASCII characters, numbers,
                        underscore, dash."""
        self._source_args = "numchan=" + str(1) + " " + ''

        self.set_id(radio_source_id)

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
            log.debug(msg)
            raise Exception(msg)

        msg = ('Radio source {id} FFT set up '
               'completed.').format(id=self.get_id())
        log.debug(msg)

        # connect the fft to the top block
        try:
            self._gr_top_block.connect(self.get_source_block(),
                                       self._log_fft)
        except Exception, exc:
            msg = ('Failed to connect the fft to the source, with:'
                   ' {m}').format(m=str(exc))
            log.debug(msg)
            raise Exception(msg)

        msg = 'FFT connected to Frequency translation.'
        log.debug(msg)

    def _retrieve_fft(self, stop_event):
        """Retrieve fft values"""

        low_freq = self.get_lower_frequency()
        high_freq = self.get_upper_frequency()
        bw = self.get_bandwidth_capability()

        while not stop_event.is_set():

            # TODO: fft value processing should go here

            current_time = datetime.datetime.utcnow().isoformat()

            # logpower fft swaps the lower and upper halfs
            # of the spectrum, this fixes it
            vraw = self._fft_signal_probe.level()
            val = vraw[len(vraw)/2:]+vraw[:len(vraw)/2]

            # update taps
            if self.get_spectrum_analyzer_tap_enable():
                tap_value = '{t};{bw};{lf};{hf};{v}\n'.format(t=current_time,
                                                              v=val, bw=bw,
                                                              lf=low_freq,
                                                              hf=high_freq)

                self._freq_analyzer_tap.update_value(tap_value)

                msg = 'updating data tap'
                log.debug(msg)

            stop_event.wait(1.0 / self._probe_poll_rate)

    def _setup_freq_analyzer_tap(self):
        """Setup a tap to provide live frequency analyzer plot.
        Create a named pipe containing the latest set of fft values.
        Will output to a previously created named pipe/file.
        If an error occurs while creating the named pipe (other than that the
        file already exists), tap output thread will not be started."""

        msg = 'Setting up fft tap.'
        log.debug(msg)

        try:
            self._freq_analyzer_tap = DataTap(self.get_id())
        except Exception, exc:
            msg = 'Failed to setup tap for FFT with:{m}'.format(m=str(exc))
            log.error(msg)
            raise

        msg = 'Radio Source {id} FFT tap setup done.'.format(id=self.get_id())
        log.debug(msg)

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
            log.debug(msg)
            raise Exception(msg)

        # connect the signal probe to the fft
        try:
            self._gr_top_block.connect(self._log_fft,
                                       self._fft_signal_probe)
        except Exception, exc:
            msg = ('Failed to connect the fft to radio source {id}, with:'
                   ' {m}').format(id=self.get_id(), m=str(exc))
            log.debug(msg)
            raise Exception(msg)

        msg = ('Radio Source {id}, Launching fft data retrieval'
               ' thread.').format(id=self.get_id())
        log.debug(msg)

        # set the fft retrieval on it's own thread
        self._retrieve_fft_thread = threading.Thread(target=self._retrieve_fft,
                                                     name=self.get_id(),
                                                     args=(self._probe_stop,))
        self._retrieve_fft_thread.daemon = True
        self._retrieve_fft_thread.start()

        msg = ('Radio Source {id} signal probe setup'
               ' done.').format(id=self.get_id())
        log.debug(msg)

    def _stop_signal_probe(self):
        """Stop the fft data probe"""

        # send the stop event to the thread
        self._probe_stop.set()

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

        src_minimum_freq = self.get_minimum_frequency()
        src_maximum_freq = self.get_maximum_frequency()

        if not float(frequency).is_integer():
            msg = 'Frequency is not a whole number'
            log.error(msg)
            raise ValueError(msg)
        elif frequency < src_minimum_freq or frequency > src_maximum_freq:
            msg = ('Frequency must be above {fl} hz '
                   'and below {fu} hz').format(fl=src_minimum_freq,
                                               fu=src_maximum_freq)
            log.error(msg)
            raise ValueError(msg)

        self._center_freq = int(frequency)

        # tune the frequency
        self._radio_source.set_center_freq(frequency, 0)
        msg = 'Radio source frequency set and tuned to {i}'.format(i=frequency)
        log.debug(msg)

        msg = ('Receiver {id} set center frequency at '
               '{f}').format(id=self.get_id(), f=self.get_center_frequency())
        log.debug(msg)

        # TODO:  iterate the list of listeners and re-set the offset

    def set_audio_sink_enable(self, audio_enable=True):
        """Set True if the audio sink is to be enabled, false otherwise.
        enable -- boolean (Default is True/enabled)"""

        if isinstance(audio_enable, bool):
            self._audio_sink_enable = audio_enable
        else:
            msg = 'audio_enable must be a boolean'
            raise TypeError(msg)
        msg = ('Radio source {id} audio output enabled set to'
               ' {val}').format(val=audio_enable, id=self.get_id())
        log.debug(msg)

    def set_spectrum_analyzer_tap_enable(self, create_tap=True):
        """Set True if the source frequency analyzer is to be enabled,
        false otherwise.
        enable -- boolean (Default is True/enabled)"""

        if isinstance(create_tap, bool):
            self._spectrum_analyzer_enable = create_tap
        else:
            msg = 'enable must be a boolean'
            raise TypeError(msg)
        msg = ('Radio source {id} frequency analyzer tap creation set to'
               ' {val}').format(val=create_tap, id=self.get_id())
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
            raise RadioSourceFrequencyOutOfBoundsError(msg)

        if listener.get_lower_frequency() < self._cap_freq_min:
            msg = ("The listener's lower frequency ({lf}) is below the "
                   "radio source's minimum frequency"
                   " ({mf})").format(lf=listener.get_lower_frequency(),
                                     mf=self._cap_freq_min)
            log.error(msg)
            raise RadioSourceFrequencyOutOfBoundsError(msg)

        # update the listener's offset
        listener.set_frequency_offset(self._center_freq)

        # pass the bandwidth to the listener
        listener.set_radio_source_bw(self._cap_bw)

        # pass the source block
        listener.set_source_block(self.get_source_block())

        # pass the top block
        listener.set_gr_top_block(self._gr_top_block)

        # pass the radio source object
        listener.set_radio_source(self)

        self._listener_list.append(listener)
        msg = 'FreqListener {i} added to list'.format(i=listener)
        log.debug(msg)

    def get_spectrum_analyser_tap_enable(self):
        """Return True if the spectrum analyzer tap is
        to be enabled."""
        return self._spectrum_analyzer_enable

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

    def get_type(self):
        """Return the type of this radio source."""
        return self._type

    def get_center_frequency(self):
        """Return the center frequency for this source."""
        return self._center_freq

    def get_listener_id_list(self):
        """Return a list of listener ids configured on this source"""
        return self._listener_list.get_listener_id_list()

    def get_audio_sink_enable(self):
        """Return True if the audio sink is to be enabled."""
        return self._audio_sink_enable

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

    def _run_source_subprocess(self, input_conn, output_conn):
        """start the subprocess for a  source.
        input_conn - input pipe
        output_conn - output pipe"""

        if self.get_audio_sink_enable():
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
                log.debug(msg)
                raise Exception(msg)
            msg = ('Radio Source {id}, fft setup '
                   'finished').format(id=self.get_id())
            log.debug(msg)

            try:
                self._setup_freq_analyzer_tap()
            except Exception, exc:
                msg = ('Failed to setup fft TAP'
                       'with {m}').format(m=str(exc))
                log.debug(msg)
                raise Exception(msg)

            try:
                self._setup_rf_fft_probe()
            except Exception, exc:
                msg = ('Failed to setup signal probe'
                       'with {m}').format(m=str(exc))
                log.debug(msg)
                raise Exception(msg)

            msg = ('Radio Source {id}, spectrum analyzer setup '
                   'finished').format(id=self.get_id())
            log.debug(msg)

        else:
            msg = ('Radio Source {id}, spectrum analyzer not '
                   'requested').format(id=self.get_id())
            log.debug(msg)

        msg = ('radio source subprocess for {id}'
               ' starting.').format(id=self.get_id())
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

        msg = ('radio source subprocess for {id}'
               ' exiting.').format(id=self.get_id())
        log.debug(msg)
        output_conn.send(msg)

    def start(self):
        """Start the radio source."""

        # setup and start the subprocess for this source

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

        # iterate through the listeners and start them
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

        # iterate through the listeners and start them
        for freq_listener in self._listener_list:
            freq_listener.start()
            msg = ('started frequency listener '
                   '{fid}').format(fid=freq_listener.get_id())
            log.debug(msg)

    def start_audio_sink(self):
        """Start an audio sink for this source."""

        samp_rate = 48e3

        self._audio_sink = audio.sink(int(samp_rate), '', True)

        msg = ('started audio sink with sample rate of '
               '{sr}').format(sr=samp_rate)
        log.debug(msg)

        # pass audio sink to all listeners
        for freq_listener in self._listener_list:
            freq_listener.set_audio_sink(self._audio_sink)

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
            log.error(msg)
            raise ValueError(msg)

    def do_snd_output(self):
        """Configure for sound output of the center frequency"""

        msg = '------->>>>>> start audio sink'
        log.debug(msg)
        self.start_audio_sink()

        msg = '------->>>>>> start fm demod'
        log.debug(msg)

        self._fm_demod()

        msg = '------->>>>>> startED fm demod'
        log.debug(msg)

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
        log.debug(msg)

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
        log.debug(msg)


class RTL2838R820T2RadioSource(RadioSource):
    """Defines a radio source hardware with  RTL2838 receiver
     and a R820T2 tuner."""

    _type = 'RTL2838_R820T2'
    _cap_bw = 2400000
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

    def __init__(self, radio_source_id):
        """Initialize the radio source object.
        radio_source_id -- the frequency listener id.
                        Acceptable characters: ASCII characters, numbers,
                        underscore, dash."""

        super(RTL2838R820T2RadioSource, self).__init__(radio_source_id)

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

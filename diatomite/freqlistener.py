#!/usr/bin/env python2
"""
    freqlistener - Tuning into frequencies from an RF spectrum provided by
    a RadioSource and check levels.
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
import datetime
import threading
from string import ascii_letters, digits
from operator import isNumberType
import logging
import numpy
from gnuradio import gr
from gnuradio import blocks
from gnuradio import filter as grfilter
from gnuradio.fft import logpwrfft
from gnuradio import analog
import radiosource
import diatomite_aux_classes as dia_aux


class FreqListenerInvalidModulationError(Exception):
    """Raised when  a FreqListener is passed an invalid modulation."""
    pass


class FreqListenerError(Exception):
    """Raised when a FreqListener encounters an error."""
    pass


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

    _supported_modulations = ['fm', 'am']

    # TODO: unify fft probe and tap initialization and teardown

    _decimation = 1
    _samp_rate = 500000
    _transition_bw = 2000
    _filter_taps = None
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

    _freq_analyzer_tap = None

    _tap_directory = None

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

    def __init__(self, conf, radio_source, tap_dir_path):
        """init the FreqListener
        conf -- a dictionary with a valid configuration
                (use DiaConfParser to obtain a valid config)
        radio_source -- this listener's radio source 
        tap_dir_path -- path where taps wil be created"""

        if (conf is not None and radio_source is not None 
            and tap_dir_path is not None):
            self.configure(conf, radio_source, tap_dir_path)
        else:
            msg = ('Incomplete initialization.conf:{c}, output queue:{q},' 
                   ' tap_dir_pat:{tp}').format(c=conf, tp=tap_dir_path)
            raise FreqListenerError(msg)
        
    def configure(self, conf, radio_source, tap_dir_path):
        """Configure the radio sources collection
        conf -- a dictionary with a valid configuration
                (use DiaConfParser to obtain a valid config)
        radio_source -- this listener's radio source 
        tap_dir_path -- path where taps wil be created"""

        self.set_tap_dir_path(tap_dir_path)
       
        self.set_id(conf['id'])
        
        self.set_frequency(conf['frequency'])
        
        self.set_modulation(conf['modulation'])
        
        self.set_bandwidth(conf['bandwidth'])
        
        self.set_signal_pwr_threshold(conf['level_threshold'])
        
        self.set_spectrum_analyzer_tap_enable(conf['freq_analyzer_tap'])
        
        self.set_audio_enable(conf['audio_output'])
        
        self.set_radio_source(radio_source)
        
        msg = ('Initialized with freq {f}, bw:{bw}, modulation:{md},'
               ' tap_dir:{td}, tap_out:{to} , audio_out:{ao}'
               ' id:{id}').format(f=self.get_frequency(),
                                  bw=self.get_bandwidth(),
                                  md=self.get_modulation(),
                                  td=self.get_tap_dir_path(),
                                  to=self.get_spectrum_analyser_tap_enable(),
                                  ao=self.get_audio_enable(),
                                  id=self.get_id())
        logging.debug(msg)

        # configure listeners        

    def set_id(self, listener_id):
        """Sets the frequency listener id.
        Converts alphabetic characters to lower case.
        listener_id -- the frequency listener id.
                        Acceptable characters: ASCII characters, numbers,
                        underscore, dash."""

        if listener_id == '':
            msg = 'Frequency id is empty'
            logging.error(msg)
            raise dia_aux.BadIdError(msg)
        if all(character in ascii_letters+digits+'_'+'-'
               for character in listener_id):
            self._id = listener_id.lower()
            msg = 'id set to {i}'.format(i=listener_id.lower())
            logging.debug(msg)
        else:
            msg = 'Frequency id contains can only contain AZaz09-_'
            logging.error(msg)
            raise dia_aux.BadIdError(msg)

    def set_radio_source(self, radio_source):
        """Sets the radio source to which this listener is connected to.
        Also sets the top block and the frequency offset.
        radio_soure -- object of RadioSource class"""
        if isinstance(radio_source, radiosource.RadioSource):

            # set the radio source
            self._radio_source = radio_source

            # set the top block
            self._set_gr_top_block(self._radio_source.get_gr_top_block())

            # set the frequency offset
            self.set_frequency_offset(self._radio_source.get_center_frequency())

            # set the tap directory path
            try:
                self.set_tap_dir_path(self._radio_source.get_tap_dir_path())
            except FreqListenerError, exc:
                msg = 'Unable to set tap directory. {exc}'.format(exc=exc)
                logging.debug(msg)

        else:
            msg = 'radio_source must be a RadioSource object'
            raise TypeError(msg)
        msg = ('Listener {id} set to radio source'
               ' {rs}').format(rs=radio_source, id=self.get_id())
        logging.debug(msg)

    def set_tap_dir_path(self, path):
        """Set the directory where tap files should be written to.
        path -- full path to the directory"""

        msg = "Tap directory is to be '{p}'.".format(p=path)
        logging.debug(msg)

        if path is None:
            msg = 'Tap path not set.'
            raise FreqListenerError(msg)

        if path in ['.', './']:
            tmp_tap_directory = os.getcwd()

        # check if path is absolute
        if os.path.isabs(path):
            tmp_tap_directory = path
        else:
            # path is relative

            # check if it is to be the current directory
            if path in ['.', './']:
                tmp_tap_directory = os.getcwd()
                msg = 'Tap directory is cwd'
                logging.debug(msg)
            else:
                tmp_tap_directory = os.path.join(os.getcwd() + os.sep + path)


        #  check if path exists and is writable

        if not os.path.isdir(tmp_tap_directory):
            msg = ("Tap directory {td} does not exist or isn't"
                   " a directory").format(td=tmp_tap_directory)
            raise FreqListenerError(msg)

        if not os.access(tmp_tap_directory, os.W_OK):
            msg = ("Tap directory {td} is not"
                   " writable").format(td=tmp_tap_directory)
            raise FreqListenerError(msg)

        self._tap_directory = tmp_tap_directory

    def get_supported_modulations(self):
        """Retrieves the supported modulations"""

        return self._supported_modulations

    def set_frequency(self, frequency):
        """Sets the frequency for the listener.
        frequency -- frequency in Hz (integer)"""

        radio_spectrum = dia_aux.RadioSpectrum()
        # radio spectrum limits
        rs_lower_freq = radio_spectrum.get_lower_frequency()
        rs_upper_freq = radio_spectrum.get_upper_frequency()

        msg = ('Requested frequency for listener "{id}":'
               ' {f} Hz').format(id=self.get_id(), f=frequency)
        logging.debug(msg)

        if not float(frequency).is_integer():
            msg = 'Frequency is not a whole number'
            logging.error(msg)
            raise ValueError(msg)

        elif frequency < rs_lower_freq and frequency > rs_upper_freq:
            msg = ('Selected frequency ({f} hz) must be above {fl} hz '
                   'and below {fu} Hz').format(f=frequency,
                                               fl=rs_lower_freq,
                                               fu=rs_upper_freq)
            logging.error(msg)
            raise ValueError(msg)
        else:
            # As the frequency may be expressed as a string of float number
            # convert it from string to float to int
            self._frequency = int(float(frequency))
            msg = 'Frequency set to {i}'.format(i=frequency)
            logging.debug(msg)

    def set_frequency_offset(self, radio_source_center_frequency):
        """Set the listener's offset frequency from the radio source's center
        frequency
        radio_source_center_frequency -- the radio source's center
                                         frequency in Hz"""

        self._frequency_offset = (radio_source_center_frequency -
                                  self._frequency) * - 1

        msg = 'Frequency offset set to {i}'.format(i=self._frequency_offset)
        logging.debug(msg)

        # TODO: may need to notify working parts of the radio source

    def set_bandwidth(self, bandwidth):
        """Sets the bandwidth for the listener.
        bandwidth -- the bandwidth in Hz (integer)"""
        if not float(bandwidth).is_integer():
            msg = 'Bandwidth is not a whole number'
            logging.error(msg)
            raise ValueError(msg)
        elif bandwidth < 1:
            msg = 'Bandwidth must be ate least 1 hz'
            logging.error(msg)
            raise ValueError(msg)
        else:
            self._bandwidth = int(bandwidth)
            msg = 'Bandwidth set to {i}'.format(i=bandwidth)
            logging.debug(msg)

    def set_modulation(self, modulation):
        """Sets the modulation for the listener.
        modulation -- the modulation"""

        modulation = modulation.lower()

        if modulation in self._supported_modulations:
            self._modulation = modulation
            msg = 'Modulation set to {i}'.format(i=modulation)
            logging.debug(msg)
        else:
            msg = ('modulation must be one of {m}').format(
                m=' '.join(self._supported_modulations))
            logging.error(msg)
            raise FreqListenerInvalidModulationError(msg)

    def _set_gr_top_block(self, gr_top_block):
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
        logging.debug(msg)

    def set_spectrum_analyzer_tap_enable(self, create_tap=True):
        """Set True if the source frequency analyzer is to be enabled,
        false otherwise.
        enable -- boolean (Default is True/enabled)"""

        if self.get_tap_dir_path() is None:
            create_tap = False
            msg = 'Tap directory not set. Spectrum analyzer not available'
            logging.warning(msg)

        if isinstance(create_tap, bool):
            self._spectrum_analyzer_enable = create_tap
        else:
            msg = 'create_fft_tap must be a boolean'
            raise TypeError(msg)
        msg = ('Radio source {id} FFT tap creation set to'
               ' {v}').format(v=create_tap, id=self.get_id())
        logging.debug(msg)

    def set_audio_sink(self, audio_sink):
        """Set the audio sink for sound output
        audio_sink -- the audio sink to use"""
        self._audio_sink = audio_sink

    def set_audio_enable(self, audio_enable=True):
        """Set True if audio output is to be enabled, false otherwise.
        enable -- boolean (Default is True/enabled)"""

        if isinstance(audio_enable, bool):
            self._audio_enable = audio_enable
        else:
            msg = 'audio_enable must be a boolean'
            raise TypeError(msg)
        msg = ('Radio source {id} audio output enabled set to'
               ' {v}').format(v=audio_enable, id=self.get_id())
        logging.debug(msg)

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

    def get_tap_dir_path(self):
        """Return the path to where taps are to be written"""
        return self._tap_directory

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
        """Get the radio source bandwidth."""

        if isinstance(self._radio_source, radiosource.RadioSource):
            return self._radio_source.get_bandwidth_capability()
        else:
            msg = ('RadioSource for this listener not set,'
                   ' Unable to obtain Bandwidth')
            raise FreqListenerError(msg)

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
            logging.debug(msg)
            raise

        msg = 'Input filter connected to rational resampler.'
        logging.debug(msg)

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
            logging.debug(msg)
            raise

        msg = 'Input rational resampler connected to output filter.'
        logging.debug(msg)

        msg = 'Frequency translation set.'
        logging.debug(msg)

    def get_spectrum_analyser_tap_enable(self):
        """Return True if the spectrum analyser tap is
        to be enabled."""
        return self._spectrum_analyzer_enable

    def _connect_frequency_translator_to_source(self):
        """Connect the frequency translation filter to the source.
        """

        if isinstance(self._radio_source, radiosource.RadioSource):
            radio_source_block = self._radio_source.get_source_block()
        else:
            msg = ('RadioSource for this listener not set,'
                   ' Unable to obtain source block')
            raise FreqListenerError(msg)

        try:
            self._gr_top_block.connect(radio_source_block,
                                       self._freq_translation_filter_input)
        except Exception, exc:
            msg = ('Failed connecting radio source to filter with'
                   ' {m}').format(m=str(exc))
            logging.debug(msg)
            raise

        msg = 'Frequency translation connected to source.'
        logging.debug(msg)

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
            logging.debug(msg)
            raise Exception(msg)

        msg = ('Listener {id} FFT set up '
               'completed.').format(id=self.get_id())
        logging.debug(msg)

        # connect the fft to the freq translation filter
        try:
            self._gr_top_block.connect(self._freq_translation_filter_output,
                                       self._log_fft)
        except Exception, exc:
            msg = ('Failed to connect the fft to freq translation, with:'
                   ' {m}').format(m=str(exc))
            logging.debug(msg)
            raise Exception(msg)

        msg = 'FFT connected to Frequency translation.'
        logging.debug(msg)

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
        signal_level -- the signal level in DBm
        Passes a notification to the receiver of the format
            '{listener_id}:SIG_STATUS:PRESENT:{level as a number}'"""

        my_id = self.get_id()

        msg = ('{i}:Sending signal PRESENT notification. '
               'Level {lvl} DBm').format(i=my_id, lvl=signal_level)
        logging.debug(msg)

        out_msg = '{i}:SIG_STATUS:PRESENT:{lvl}'.format(i=my_id, lvl=signal_level)
        # pass the notification to the receiver
        self._radio_source.send_data(out_msg)

    def notify_signal_absent(self, signal_level):
        """Notify that the signal is absent and the current level
        signal_level -- the signal level in DBm
        Passes a notification to the receiver of the format
            'SIG_STATUS:ABSENT:{level as a number}'"""

        my_id = self.get_id()

        msg = ('{i}:Sending signal ABSENT notification. '
               'Level {lvl} DBm').format(i=my_id, lvl=signal_level)
        logging.debug(msg)

        out_msg = '{i}:SIG_STATUS:ABSENT:{lvl}'.format(i=my_id, lvl=signal_level)
        # pass the notification to the receiver
        self._radio_source.send_data(out_msg)

    def _retrieve_fft(self, stop_event):
        """Retrieve fft values"""

        low_freq = self.get_lower_frequency()
        high_freq = self.get_upper_frequency()
        band_w = self.get_bandwidth()

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
                                                              v=val, bw=band_w,
                                                              lf=low_freq,
                                                              hf=high_freq)

                self._freq_analyzer_tap.update_value(tap_value)

                msg = 'updating data tap'
                logging.debug(msg)

            stop_event.wait(1.0 / self._probe_poll_rate)

    def _setup_freq_analyzer_tap(self):
        """Setup a tap to provide live frequency analyzer values.
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

        msg = 'Listener {id} FFT tap setup done.'.format(id=self.get_id())
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
            msg = ('Failed to connect the fft to freq translation, with:'
                   ' {m}').format(m=str(exc))
            logging.debug(msg)
            raise Exception(msg)

        msg = ('Listener {id}, Launching fft data retrieval'
               ' thread.').format(id=self.get_id())
        logging.debug(msg)

        # set the fft retrieval on it's own thread
        self._retrieve_fft_thread = threading.Thread(target=self._retrieve_fft,
                                                     name=self.get_id(),
                                                     args=(self._probe_stop,))
        self._retrieve_fft_thread.daemon = True
        self._retrieve_fft_thread.start()

        msg = ('Listener {id} signal probe setup'
               ' done.').format(id=self.get_id())
        logging.debug(msg)

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
            logging.debug(msg)
            raise Exception(msg)

        # connect frequency translator to source
        try:
            self._connect_frequency_translator_to_source()
        except Exception, exc:
            msg = ('Failed connecting frequency translation to source'
                   'with {m}').format(m=str(exc))
            logging.debug(msg)
            raise Exception(msg)

        # setup fft and connect it to frequency translator
        try:
            self._setup_rf_fft()
        except Exception, exc:
            msg = ('Failed to setup RF FFT'
                   'with {m}').format(m=str(exc))
            logging.debug(msg)
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
                logging.debug(msg)
                raise Exception(msg)

        # obtain the fft values
        # this is needed even if the spectrum analyzer is not enabled
        try:
            self._setup_rf_fft_probe()
        except Exception, exc:
            msg = ('Failed to setup signal probe'
                   'with {m}').format(m=str(exc))
            logging.debug(msg)
            raise Exception(msg)

        self._status = 'RUNNING'

        # start sound output
        if self.get_audio_enable():
            self.do_snd_output()

    def stop(self):
        """Stop the frequency listener """

        msg = 'stopping frequency listener {id}'.format(id=self.get_id())
        logging.debug(msg)

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
            logging.error(msg)
            msg = 'not yet done'
            raise FreqListenerError(msg)

        # TODO: add the fft data retrieval

    def do_snd_output(self):
        """Configure for sound output for the listener"""

        msg = 'fm demod will start for listener {id}'.format(id=self.get_id())
        logging.debug(msg)

        self._fm_demod()

        msg = 'fm demod started for listener {id}'.format(id=self.get_id())
        logging.debug(msg)

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
        logging.debug(msg)

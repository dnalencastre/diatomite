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
from string import ascii_letters, digits
from gnuradio import gr
from gnuradio import filter as grfilter
import osmosdr


class FreqListenerBadIdError(Exception):
    """Raised when a FreqListener is passed an empty id or with unacceptable
    characters."""
    pass


class FreqListenerInvalidModulation(Exception):
    """Raised when  a FreqListener is passed an invalid modulation."""
    pass


class RadioSourceFrequencyOutOfBounds(Exception):
    """Raised when a RadioSource is given a FreqListener that has frequency and
    bandwidth that don't fit within the radio source's frequency abilites."""
    pass


class RadioSourceBadIdError(Exception):
    """Raised when a FreqListener is passed an id with unacceptable
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

    def set_id(self, listener_id):
        """Sets the frequency listener id.
        Converts alphabetic characters to lower case.
        listener_id -- the frequency listener id.
                        Acceptable characters: ASCII characters, numbers,
                        underscore, dash."""

        if listener_id == '':
            msg = 'Frequency id is empty'
            log.error(msg)
            raise FreqListenerBadIdError(msg)
        if all(character in ascii_letters+digits+'_'+'-'
               for character in listener_id):
            self._id = listener_id.lower()
            msg = 'id set to {i}'.format(i=listener_id.lower())
            log.debug(msg)
        else:
            msg = 'Frequency id contains can only contain AZaz09-_'
            log.error(msg)
            raise FreqListenerBadIdError(msg)

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
            msg = ('gr_top_block musb be of type gr.top_block,'
                   ' was {tgtb}').format(tgtb=type_gr_top_block)
            raise TypeError(msg)
        
        self._gr_top_block = gr_top_block

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

    def _connect_frequency_translator_to_source(self):
        """Connect the frequency translation filter to the source.
        """
     
        try:
            self._gr_top_block.connect(self._radio_source_block, 
                                       self._freq_translation_filter)
        except Exception, exc:
            msg = ('Failed connecting radio source to filter with'
                   ' {m}').format(m=str(exc))
            print msg
            raise

    def start_listener(self):
        """Start the frequency listener."""
    
        try:
            self._config_frequency_translation()
        except Exception, exc:
            msg = ('Failed configuring frequency translation with'
                   ' {m}').format(m=str(exc))
            print msg
            raise
        
        try:
            self._connect_frequency_translator_to_source()
        except Exception, exc:
            msg = ('Failed connecting frequency translation to source'
                   'with {m}').format(m=str(exc))
            print msg
            raise            
        
        #TODO: add fft connection
        
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
    _listener_list = FreqListenerList()

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
            raise RadioSourceBadIdError(msg)
        if all(character in ascii_letters+digits+'_'+'-'
               for character in radio_source_id):
            self._id = radio_source_id.lower()
            msg = 'id set to {i}'.format(i=radio_source_id.lower())
            log.debug(msg)
        else:
            msg = 'Frequency id contains contains unacceptable characters'
            log.error(msg)
            raise RadioSourceBadIdError(msg)

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
        
    def start_frequency_listeners(self):
        """Start individual frequency listeners"""

        #iterate through the listeners and start them
        for freq_listener in self._listener_list:
            freq_listener.start_listener()
            msg = ('Starting frequency listener '
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

        self._radio_source = osmosdr.source(self._source_args)
        # TODO: find a way to check if osmosdr.source init is successful
        
        # TODO: need to set a top_block object!!!

        radio_init_sucess = True
#        radio_init_sucess = False

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

    #TODO: add method to start radio sources

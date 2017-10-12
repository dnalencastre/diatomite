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

class FreqListenerBadIdError(Exception):
    """Raised when a FreqListener is passed an empty id or with unacceptable characters."""
    pass

class FreqListenerInvalidModulation(Exception):
    """Raised when  a FreqListener is passed an invalid modulation."""
    pass

class RadioReceiverFrequencyOutOfBounds(Exception):
    """Raised when a RadioReceiver is given a FreqListener that has frequency and
    bandwidth that don't fit within the receiver's frequency abilites."""
    pass

class RadioReceiverBadIdError(Exception):
    """Raised when a FreqListener is passed an id with unacceptable characters."""
    pass

class RadioReceiverListIdNotUniqueError(Exception):
    """Raised when a RadioReceiver with an already occurring id is added to a
    RadioRecieverList."""
    pass

class FreqListenerListIdNotUniqueError(Exception):
    """Raised when a FreqListener with an already occurring id is added to a
    FreqlistenerList."""
    pass


class RadioSpectrum(object):
    
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

class FreqListener:
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
            raise FreqListenerBadIdError, msg
        if all(character in ascii_letters+digits+'_'+'-' for character in listener_id):
            self._id = listener_id.lower()
            msg = 'id set to {i}'.format(i=listener_id.lower())
            log.debug(msg)
        else:
            msg = 'Frequency id contains can only contain AZaz09-_'
            log.error(msg)
            raise FreqListenerBadIdError, msg
        
    def set_frequency(self, frequency):
        """Sets the frequency for the listener.
        frequency -- frequency in Hz (integer)"""
        
        rs = RadioSpectrum()
        # radio spectrum limits
        rs_lower_freq = rs.get_lower_frequency()
        rs_upper_freq = rs.get_upper_frequency()
        
        if not float(frequency).is_integer():
            msg = 'Frequency is not a whole number'
            log.error(msg)
            raise ValueError, msg
        elif frequency < rs_lower_freq or frequency > rs_upper_freq:
            msg = ('Frequency must be above {fl} hz '
                   'and below {fu} hz').format(fl=rs_lower_freq, fu=rs_upper_freq)
            log.error(msg)
            raise ValueError, msg
        else:
            self._frequency = int(frequency)
            msg = 'Frequency set to {i}'.format(i=frequency)
            log.debug(msg)

    def set_bandwidth(self, bandwidth):
        """Sets the bandwidth for the listener.
        bandwidth -- the bandwidth in Hz (integer)"""
        if not float(bandwidth).is_integer():
            msg = 'Bandwidth is not a whole number'
            log.error(msg)
            raise ValueError, msg
        elif bandwidth < 1:
            msg = 'Bandwidth must be ate least 1 hz'
            log.error(msg)
            raise ValueError, msg
        else:
            self._bandwidth = int(bandwidth)       
            msg = 'Bandwidth set to {i}'.format(i=bandwidth)
            log.debug(msg)
        
    def set_modulation(self, modulation):
        """Sets the modulation for the listener.
        modulation -- the modulation"""
        
        acceptable_modulations = ['fm','am','usb','lsb']
        
        modulation = modulation.lower()
        
        if modulation in acceptable_modulations:
            self._modulation = modulation
            msg = 'Modulation set to {i}'.format(i=modulation)
            log.debug(msg)
        else:
            msg = ('modulation must be one of {m}').format(
                m=' '.join(acceptable_modulations))
            log.error(msg)
            raise FreqListenerInvalidModulation,msg
                
    def get_id(self):
        """Returns the frequency listener id."""
        return self._id
    
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
            raise TypeError, msg
               
        # obtain the listener id
        id_to_add = listener.get_id()
    
        if id_to_add in current_id_list:
            msg = "Frequency Listener's id is not unique"
            log.error(msg)
            raise FreqListenerListIdNotUniqueError, msg

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

class RadioReceiver(object):
    """Define a radio receiver.
    This usually relates to the radio hardware
    """
    
    # Id of the receiver
    _id = ''
    
    # list of frequency listeners
    _listener_list = FreqListenerList()

    _type = ''
    
    # define the bandwidth capability of the receiver, in hz
    _cap_bw = 0
    
    # define minimum and maximum frequencies that are
    # tunable by the receiver, in hz
    _cap_freq_min = 0
    _cap_freq_max = 0

    # define the currently tuned frequency
    _center_freq = 0
    
    def __init__(self, receiver_id):
        rs = RadioSpectrum()
        self._type = 'base_receiver'
        self._cap_bw = 1000
        self._cap_freq_min = rs.get_lower_frequency()
        self._cap_freq_max = rs.get_upper_frequency()
        # set center frequency halfway between min and max
        self._center_freq = self._cap_freq_max - ((self._cap_freq_max - self._cap_freq_min) / 2)
        self.set_id(receiver_id)
        msg = ('Initialized with type:{t}, cap_bw:{cb}, cap_freq_min:{cfmin},'
               ' cap_freq_max:{cfmax}, center_freq:{cf},'
               ' id:{id}').format(t=self._type, cb=self._cap_bw, 
                                  cfmin=self._cap_freq_min, 
                                  cfmax=self._cap_freq_max, 
                                  cf=self._center_freq, id=receiver_id)
        log.debug(msg)

    def set_id(self, receiver_id):
        """Sets the radio receiver's  id.
        Converts alphabetic characters to lower case.
        receiver_id -- the frequency listener id. 
                        Acceptable characters: ASCII characters, numbers, 
                        underscore, dash."""

        if receiver_id == '':
            msg = 'Receiver id is empty'
            log.error(msg)
            raise RadioReceiverBadIdError, msg
        if all(character in ascii_letters+digits+'_'+'-' 
               for character in receiver_id):
            self._id = receiver_id.lower()
            msg = 'id set to {i}'.format(i=receiver_id.lower())
            log.debug(msg)
        else:
            msg = 'Frequency id contains contains unacceptable characters'
            log.error(msg)
            raise RadioReceiverBadIdError, msg

    def add_frequency_listener(self, listener):
        """Add a FreqListener to this Radio Receiver's listener list.
        listener -- FreqListener"""
 
        if listener.get_upper_frequency() > self._cap_freq_max:
            msg = ("The listener's upper frequency ({lf}) is above the "
                   "receiver's maximum frequency ({mf})").format(
                       lf=listener.get_upper_frequency(),
                       mf=self._cap_freq_max)
            log.error(msg)
            raise RadioReceiverFrequencyOutOfBounds, msg
            
        if listener.get_lower_frequency() < self._cap_freq_min:
            msg = ("The listener's lower frequency ({lf}) is below the "
                  "receiver's minimum frequency ({mf})").format(
                      lf=listener.get_upper_frequency(),
                      mf=self._cap_freq_min)
            log.error(msg)
            raise RadioReceiverFrequencyOutOfBounds, msg
           
        self._listener_list.append(listener)
        msg = 'FreqListener {i} added to list'.format(i=listener)
        log.debug(msg)

    def get_id(self):
        """Returns the receiver's id."""
        return self._id

    def get_upper_frequency(self):
        """Return the upper frequency on this receiver."""
        return self._cap_freq_max
    
    def get_lower_frequency(self):
        """Return the lower frequency on this receiver."""
        return self._cap_freq_min
    
    def get_bandwidth_capability(self):
        """Return the bandwidth capability for this receiver."""
        return self._cap_bw
    
    def get_type(self):
        """Return the type of this receiver."""
        return self._type


class RTL2838R820T2RadioReceiver(RadioReceiver):
    """Defines a radio receiver hardware with  RTL2838 receiver
     and a R820T2 tuner."""
    
    def __init__(self, receiver_id):
        self._type = 'RTL2838_R820T2'
        self._cap_bw = 2400000
        self._cap_freq_min = 25000
        self._cap_freq_max = 1750000000
        self._center_freq = self._cap_freq_max - ((self._cap_freq_max - self._cap_freq_min) / 2)
        self.set_id(receiver_id)
        msg = ('Initialized with type:{t}, cap_bw:{cb}, cap_freq_min:{cfmin},'
               ' cap_freq_max:{cfmax}, center_freq:{cf},'
               ' id:{id}').format(t=self._type, cb=self._cap_bw, 
                                  cfmin=self._cap_freq_min, 
                                  cfmax=self._cap_freq_max, 
                                  cf=self._center_freq, id=receiver_id)
        log.debug(msg)

class RadioReceiverList(list):
    """Define a list of RadioReceiver objects."""

    def append(self, receiver):
        """add a receiver to the list
        receiver - a RadioReceiver to add to the list.
        append will not allow duplicate ids to be added."""
             
        current_id_list = self.get_receiver_id_list()
        
        if not isinstance(receiver, RadioReceiver):
            msg = 'item is not of type RadioReceiver'
            log.error(msg)
            raise TypeError, msg

        # obtain the listener id
        id_to_add = receiver.get_id()
     
        if id_to_add in current_id_list:
            msg = "Radio Receiver's id is not unique"
            log.error(msg)
            raise RadioReceiverListIdNotUniqueError, msg
              
        super(RadioReceiverList, self).append(receiver)
        msg = 'RadioReceiver {i} added to list'.format(i=receiver)
        log.debug(msg)

    def get_receiver_id_list(self):
        """Obtain list of ids for all the members of the list"""
        res = []
 
        for receiver in self:
            fid = receiver.get_id()
            res.append(fid)
         
        return res


class Location:
    """Define a location."""
    
    address = ''
    longitude = ''
    latitude = ''
    
    # define if it is a static or mobile location
    type = ''


class DiatomiteSite:
    """Define a site for diatomite probes.
    Used to give the site a name and to tie a probe to a location.
    A site may have multiple probes, but an object of this type does not need
    to be aware of all diatomite probes."""
    
    # Location for this site
    location = Location()
    
    # Site name
    site_name = ''


class DiatomiteProbe:
    """Define a diatomite probe.
    A diatomite probe pertains to a DiatomiteSite.
    A diatomite probe has one or more radio receivers
    """
     
    _site = DiatomiteSite()
    _receiver_list=RadioReceiverList()
    
    def add_radio_receiver(self, receiver):
        """Add a FreqListener to this Radio Receiver's listener list.
        listener -- FreqListener"""
  
        #TODO: check for duplicate ids when adding
      
        self._receiver_list.append(receiver)
        msg = 'RadioReceiver {i} added to list'.format(i=receiver)
        log.debug(msg)

    

#!/usr/bin/env python2
"""
    Tests for the diatomite monitoring system.
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

import diatomite.diatomite_base_classes as diatomite_base_classes

class testRadioReceiverList(object):
    
    def test_append_with_non_RadioReceiver_fail(self):
        """adding an object not of type RadioReceiver should raise a TypeError."""
        
        non_radio_receiver = 'test'

        radio_receiver_list = diatomite_base_classes.RadioReceiverList()
        try:
            radio_receiver_list.append(non_radio_receiver)
        except TypeError:
            pass

    def test_append_with_RadioReceiver_sucess(self):
        """adding an object of type RadioReceiver is successful."""
        
        radio_receiver = diatomite_base_classes.RadioReceiver('test_append_with_RadioReceiver_sucess')
         
        radio_receiver_list = diatomite_base_classes.RadioReceiverList()
         
        radio_receiver_list.append(radio_receiver)
        
    def test_get_receiover_id_list(self):
        
        # define an empty FreqListenerList
        radio_receiver_list = diatomite_base_classes.RadioReceiverList()
        
        # add a few elements to the freq list and control list
        id_to_set_a = 'test_a'
        id_to_set_b = 'test_b'
        radio_receiver_a = diatomite_base_classes.RadioReceiver(id_to_set_a)
        radio_receiver_b = diatomite_base_classes.RadioReceiver(id_to_set_b)
        radio_receiver_list.append(radio_receiver_a)
        radio_receiver_list.append(radio_receiver_b)
        control_list = []
        control_list.append(id_to_set_a.lower())
        control_list.append(id_to_set_b.lower())

        freq_listener_id_list = radio_receiver_list.get_receiver_id_list()

        if not isinstance(freq_listener_id_list, list):
            msg = ('RadioReceiver.get_listener_id_list did not return a list')
            assert False, msg
            
        if control_list != freq_listener_id_list:
            msg = ('RadioReceiver.get_listener_id_list did not return the expected list contents')
            assert False, msg

    def test_append_repeating_id_fail(self):
        """Adding an already existing id should fail."""
        # define an empty FreqListenerList
        radio_receiver_list = diatomite_base_classes.RadioReceiverList()
       
        # add a few elements to the freq list and control list
        id_to_set_a = 'test_a'
        id_to_set_b = 'test_a'
        radio_receiver_a = diatomite_base_classes.RadioReceiver(id_to_set_a)
        radio_receiver_b = diatomite_base_classes.RadioReceiver(id_to_set_b)
        radio_receiver_list.append(radio_receiver_a)
        control_list = []
        
        control_list.append(id_to_set_a.lower())
        control_list.append(id_to_set_b.lower())
             
        try:
            radio_receiver_list.append(radio_receiver_b)
        except diatomite_base_classes.RadioReceiverListIdNotUniqueError:
            pass
        else:
            msg = 'RadioReceiverList accepted an existing ID'
            assert False, msg

class testRadioSpectrum(object):
    """Test RadioSpectrum."""
    
    _radio_spectrum = diatomite_base_classes.RadioSpectrum()
    
    def test_get_upper_frequency(self):
        """Test retrieving the upper frequency of the RadioSpectrum.
        Also check it is a whole number and larger than zero."""
 
        upper_from_radio_spectrum = self._radio_spectrum.get_upper_frequency()
                
        if not float(upper_from_radio_spectrum).is_integer():
            msg = ('{o} not returning a valid upper frequency (number is not'
                   ' whole).').format(o=type(self._radio_spectrum).__name__)
            assert False, msg
             
        if not upper_from_radio_spectrum >= 1:
            msg  =('{o} not returning a valid upper frequency (number is lower '
                   'than 1).').format(o=type(self._radio_spectrum).__name__)
            assert False, msg 
           
    def test_get_lower_frequency(self):
        """Test retrieving the lower frequency of the RadioSpectrum.
          Also check it is a whole number and larger than zero."""
           

        lower_from_radio_spectrum = self._radio_spectrum.get_lower_frequency()
         
        if not float(lower_from_radio_spectrum).is_integer():
            msg = ('{o} not returning a valid lower frequency (number is not'
                   ' whole).').format(o=type(self._radio_spectrum).__name__)
            assert False, msg
             
        if not lower_from_radio_spectrum >= 1:
            msg = ('{o} not returning a valid lower frequency (number is lower'
                   ' than 1).').format(o=type(self._radio_spectrum).__name__)
            assert False, msg
    

class testFreqListenerList(object):
    """Test FreqListenerList."""
    
    _freq_listener= diatomite_base_classes.FreqListener('testFreqListenerList')
    _freq_listener_list = diatomite_base_classes.FreqListenerList()

    def test_append_with_non_FreqListener_fail(self):
        """adding an object not of type FreqListenerList should raise a TypeError."""
        
        non_freq_listener = 'test'

        try:
            self._freq_listener_list.append(non_freq_listener)
        except TypeError:
            pass

    def test_append_with_FreqListener_sucess(self):
        """adding an object of FreqListener type is successful."""
        
        self._freq_listener_list.append(self._freq_listener)

    def test_append_repeating_id_fail(self):
        """Adding an already existing id should fail."""
        # define an empty FreqListenerList
        freq_listener_list = diatomite_base_classes.FreqListenerList()
        
        # add a few elements to the freq list and control list
        id_to_set_a = 'test_a'
        id_to_set_b = 'test_a'
        freq_listener_a = diatomite_base_classes.FreqListener(id_to_set_a)
        freq_listener_b = diatomite_base_classes.FreqListener(id_to_set_b)
        freq_listener_list.append(freq_listener_a)
        control_list = []
        
        control_list.append(id_to_set_a.lower())
        control_list.append(id_to_set_b.lower())
        
        try:
            freq_listener_list.append(freq_listener_b)
        except diatomite_base_classes.FreqListenerListIdNotUniqueError:
            pass
        else:
            msg = 'FreqListenerList accepted an existing ID'
            assert False, msg

    def test_get_listener_id_list(self):
        
        # define an empty FreqListenerList
        freq_listener_list = diatomite_base_classes.FreqListenerList()
        
        # add a few elements to the freq list and control list
        id_to_set_a = 'test_a'
        id_to_set_b = 'test_b'
        freq_listener_a = diatomite_base_classes.FreqListener(id_to_set_a)
        freq_listener_b = diatomite_base_classes.FreqListener(id_to_set_b)
        freq_listener_list.append(freq_listener_a)
        freq_listener_list.append(freq_listener_b)
        control_list = []
        control_list.append(id_to_set_a.lower())
        control_list.append(id_to_set_b.lower())

        freq_listener_id_list = freq_listener_list.get_listener_id_list()

        if not isinstance(freq_listener_id_list, list):
            msg = ('FreqListenerList.get_listener_id_list did not return a list')
            assert False, msg
            
        if control_list != freq_listener_id_list:
            msg = ('FreqListenerList.get_listener_id_list did not return the expected list contents')
            assert False, msg


class testFreqListener:
    
    def test_set_and_get_id(self):
        """Test setting and retrieving frequency id, Checks that string is 
        stored as lower case."""
        id_to_set = 'test_id123-A'
        freq_listener = diatomite_base_classes.FreqListener(id_to_set)
        freq_listener.set_id(id_to_set)
        
        id_from_fl = freq_listener.get_id()
        
        if not id_to_set.lower() == id_from_fl:
            assert False, 'Id that was set was not returned correctly'

    def test_set_id_with_wrong_characters(self):
        """Test setting a frequency ID containing unacceptable characters."""
        
        # needs to be initialized correctly
        id_to_set = 'initial'
        freq_listener = diatomite_base_classes.FreqListener(id_to_set)
        id_to_set = 'test!@##$$%$%^'
        try:
            freq_listener.set_id(id_to_set)
        except diatomite_base_classes.FreqListenerBadIdError:
            pass
        else:
            assert False, 'FrequencyListener accepted an ID with unacceptable characters'
            
    def test_set_empty_id(self):
        """Test setting a frequency ID containing unacceptable characters."""
        
        id_to_set = 'test_set_empty_id'
        freq_listener = diatomite_base_classes.FreqListener(id_to_set)
        id_to_set = ''
        try:
            freq_listener.set_id(id_to_set)
        except diatomite_base_classes.FreqListenerBadIdError:
            pass
        else:
            assert False, 'FrequencyListener accepted an empty ID'

    def test_set_and_get_frequency(self):
        """Test setting and retrieving frequency."""
        radio_spectrum = diatomite_base_classes.RadioSpectrum()
        radio_spectrum_minimums = radio_spectrum.get_lower_frequency()
        frequency_to_set = radio_spectrum_minimums + 1000
        id_to_set = 'test_set_and_get_frequency'
        freq_listener = diatomite_base_classes.FreqListener(id_to_set)
        freq_listener.set_frequency(frequency_to_set)
        
        frequency_from_fl = freq_listener.get_frequency()
        
        if not frequency_to_set == frequency_from_fl:
            assert False, 'Frequency that was set was not returned correctly'
            
    def test_set_frequency_below_radio_spectrum_minimums(self):
        """Test setting the frequency below the radio spectrum minimums."""
        radio_spectrum = diatomite_base_classes.RadioSpectrum()
        radio_spectrum_minimums = radio_spectrum.get_lower_frequency()
        id_to_set = 'test_set_frequency_below_radio_spectrum_minimums'
        freq_listener = diatomite_base_classes.FreqListener(id_to_set)

        if radio_spectrum_minimums <= 1000:
            frequency_to_set =  radio_spectrum_minimums - 1
        else:
            frequency_to_set = radio_spectrum_minimums - 1000
        
        try:
            freq_listener.set_frequency(frequency_to_set)
        except ValueError:
            pass
        else:
            msg = 'FreqListener accepted frequency below radio spectrum limits'
            assert False, msg

    def test_set_frequency_above_radio_spectrum_maximums(self):
        """Test setting the frequency above the radio spectrum maximums."""
        radio_spectrum = diatomite_base_classes.RadioSpectrum()
        radio_spectrum_maximums = radio_spectrum.get_upper_frequency()
        id_to_set = 'test_set_frequency_above_radio_spectrum_maximums'
        freq_listener = diatomite_base_classes.FreqListener(id_to_set)

        frequency_to_set =  radio_spectrum_maximums + 1000
        
        try:
            freq_listener.set_frequency(frequency_to_set)
        except ValueError:
            pass
        else:
            msg = 'FreqListener accepted frequency above radio spectrum limits'
            assert False, msg 
            
    def test_set_frequency_only_accepts_integer_numbers(self):
        """Test that set_frequency only accepts integer numbers."""
        frequency_to_set = 'blah'
        id_to_set = 'test_set_frequency_only_accepts_integer_numbers_a'
        freq_listener = diatomite_base_classes.FreqListener(id_to_set)
        
        try:
            freq_listener.set_frequency(frequency_to_set)
        except ValueError:
            pass
        else:
            assert False, 'Frequency accepted alphabetic characters.'       

        frequency_to_set = 1.5
        id_to_set = 'test_set_frequency_only_accepts_integer_numbers_b'
        freq_listener = diatomite_base_classes.FreqListener(id_to_set)
        
        try:
            freq_listener.set_frequency(frequency_to_set)
        except ValueError:
            pass
        else:
            assert False, 'Frequency accepted non integer number.'     

    def test_set_and_get_bandwidth(self):
        """Test setting and retrieving bandwidth."""
        bandwidth_to_set = 123
        id_to_set = 'test_set_and_get_bandwidth'
        freq_listener = diatomite_base_classes.FreqListener(id_to_set)
        freq_listener.set_bandwidth(bandwidth_to_set)
        
        bandwidth_from_fl = freq_listener.get_bandwidth()
        
        if not bandwidth_to_set == bandwidth_from_fl:
            assert False, 'Bandwidth that was set was not returned correctly.'

    def test_set_bandwidth_only_accepts_integer_numbers(self):
        """Test that set_bandwidth only accepts integer numbers."""
        bandwidth_to_set = 'blah'
        id_to_set = 'test_set_bandwidth_only_accepts_integer_numbers'
        freq_listener = diatomite_base_classes.FreqListener(id_to_set)
        
        try:
            freq_listener.set_bandwidth(bandwidth_to_set)
        except ValueError:
            pass
        else:
            assert False, 'Bandwidth accepted alphabetic characters.'       

        frequency_to_set = 1.5
        id_to_set = 'test_set_bandwidth_only_accepts_integer_numbers_b'
        freq_listener = diatomite_base_classes.FreqListener(id_to_set)
        
        try:
            freq_listener.set_bandwidth(frequency_to_set)
        except ValueError:
            pass
        else:
            assert False, 'Bandwidth accepted non integer number.'

    def test_set_and_get_modulation(self):
        """Test setting and retrieving modulation."""
        modulation_to_set = 'FM'
        id_to_set = 'test_set_and_get_modulation'
        freq_listener = diatomite_base_classes.FreqListener(id_to_set)
        freq_listener.set_modulation(modulation_to_set)
        
        modulation_from_fl = freq_listener.get_modulation()
        
        if not modulation_to_set.lower() == modulation_from_fl:
            assert False, 'modulation that was set was not returned correctly'   

    def test_set_unacceptable_modulation(self):
        """Test setting an unacceptable modulation."""
        modulation_to_set = 'blaaah'
        id_to_set = 'test_set_unacceptable_modulation'
        freq_listener = diatomite_base_classes.FreqListener(id_to_set)
         
        try:
            freq_listener.set_modulation(modulation_to_set)
        except diatomite_base_classes.FreqListenerInvalidModulation:
            pass
        else:
            assert False, 'FrequencyListener accepted an unacceptable modulation'

    def test_get_upper_frequency(self):
        """Test retrieving the upper frequency of the Listener."""
        
        frequency_to_set = 12000
        bandwidth_to_set = 1000
        upper_freq = frequency_to_set + (bandwidth_to_set/2)
        
        id_to_set = 'test_get_upper_frequency'
        freq_listener = diatomite_base_classes.FreqListener(id_to_set)
        freq_listener.set_frequency(frequency_to_set)
        freq_listener.set_bandwidth(bandwidth_to_set)
        
        upper_from_freq_listener = freq_listener.get_upper_frequency()
        
        if not upper_from_freq_listener == upper_freq:
            assert False, 'Frequency listener not returning correct upper frequency.'

    def test_get_lower_frequency(self):
        """Test retrieving the lower frequency of the Listener."""
        
        frequency_to_set = 12000
        bandwidth_to_set = 1000
        lower_freq = frequency_to_set - (bandwidth_to_set/2)
        
        id_to_set = 'test_get_lower_frequency'
        freq_listener = diatomite_base_classes.FreqListener(id_to_set)
        freq_listener.set_frequency(frequency_to_set)
        freq_listener.set_bandwidth(bandwidth_to_set)
        
        lower_from_freq_listener = freq_listener.get_lower_frequency()
        
        if not lower_from_freq_listener == lower_freq:
            assert False, 'Frequency listener not returning correct lower frequency.'
              

class testRadioReceiver(object):
 
    _radio_receiver = diatomite_base_classes.RadioReceiver('testRadioReceiver')
    _radio_spectrum = diatomite_base_classes.RadioSpectrum()

    def test_init_without_id(self):
        try:
            diatomite_base_classes.RadioReceiver()
        except TypeError:
            pass
        else:
            msg = 'RadioReceiver accepted instanciation without id'
            assert False,msg

    def test_set_empty_id(self):
        """Test setting a frequency ID containing unacceptable characters."""
        
        id_to_set = 'test_set_empty_id'
        radio_receiver = diatomite_base_classes.RadioReceiver(id_to_set)
        id_to_set = ''
        try:
            radio_receiver.set_id(id_to_set)
        except diatomite_base_classes.RadioReceiverBadIdError:
            pass
        else:
            assert False, 'RadioReceiver accepted an empty ID'

    def test_set_and_get_id(self):
        """Test setting and retrieving receiver id, Checks that string is 
        stored as lower case."""
        id_to_set = 'test_id123-A'
        self._radio_receiver.set_id(id_to_set)
        
        id_from_rr = self._radio_receiver.get_id()
        
        if not id_to_set.lower() == id_from_rr:
            assert False, 'Id that was set was not returned correctly'

    def test_set_id_with_wrong_characters(self):
        """Test setting a receiver ID containing unacceptable characters."""
        
        id_to_set = 'test!@##$$%$%^'
        try:
            self._radio_receiver.set_id(id_to_set)
        except diatomite_base_classes.RadioReceiverBadIdError:
            pass
        else:
            assert False, 'RadioReceiver accepted an ID with unacceptable characters'

    def test_get_upper_frequency(self):
        """Test retrieving the upper frequency of the RadioReceiver.
        Also check it is a whole number and larger than zero."""
          
        upper_from_radio_receiver = self._radio_receiver.get_upper_frequency()
        rs_upper_frequency = self._radio_spectrum.get_upper_frequency()
        
        if not float(upper_from_radio_receiver).is_integer():
            msg = ('{o} not returning a valid upper frequency (number is not'
                   ' whole).').format(o=type(self._radio_receiver).__name__)
            assert False, msg
             
        if not upper_from_radio_receiver <= rs_upper_frequency:
            msg = ('{o} not returning a valid upper frequency (number is above'
                   ' radio spectrum {urs}).').format(
                       o=type(self._radio_receiver).__name__,
                       urs=rs_upper_frequency)
            assert False, msg
           
    def test_get_lower_frequency(self):
        """Test retrieving the lower frequency of the RadioReceiver.
          Also check it is a whole number and larger than zero."""
 
        lower_from_radio_receiver = self._radio_receiver.get_lower_frequency()
        rs_lower_frequency = self._radio_spectrum.get_lower_frequency()
         
        if not float(lower_from_radio_receiver).is_integer():
            msg = ('{o} not returning a valid lower frequency (number is not'
                   ' whole).').format(o=type(self._radio_receiver).__name__)
            assert False, msg
             
        if not lower_from_radio_receiver >= rs_lower_frequency:
            msg = ('{o} not returning a valid lower frequency (number is below'
                   ' radio spectrum {lrs}).').format(
                       o=type(self._radio_receiver).__name__,
                       lrs=rs_lower_frequency)
            assert False, msg
 
 
    def test_get_bandwidth_capability(self):
        """Test retrieving the bandwidth capability of the RadioReceiver.
          Also check it is a whole number and larger than zero."""
       
        bandwidth_capability_from_radio_receiver = self._radio_receiver.get_bandwidth_capability()
         
        if not float(bandwidth_capability_from_radio_receiver).is_integer():
            msg = ('{o} not returning a valid bandwidth capability (number is not'
                   ' whole).').format(o=type(self._radio_receiver).__name__)
            assert False, msg
             
        if not bandwidth_capability_from_radio_receiver >= 1:
            msg = ('{o} not returning a valid bandwidth capability (number is lower'
                   ' than 1).').format(o=type(self._radio_receiver).__name__)
            assert False, msg
 

    def test_add_frequency_listener(self):
        """Test adding a frequency listener to a RadioReceiver object."""
#         rr = diatomite_base_classes.RadioReceiver()
        # get the radio's frequency limits
        upper_from_radio_receiver = self._radio_receiver.get_upper_frequency()
        lower_from_radio_receiver = self._radio_receiver.get_lower_frequency()

        # calculate the bandwidth
        bw = upper_from_radio_receiver - lower_from_radio_receiver
         
        # define the center frequency midway from upper and lower
        center_freq = (bw/2) + lower_from_radio_receiver
        frequency_to_set = center_freq

        # ensure the bandwidth fits the radio
        bandwidth_to_set = bw/2

        id_to_set = 'test_add_frequency_listener'
        freq_listener = diatomite_base_classes.FreqListener(id_to_set)
        freq_listener.set_frequency(frequency_to_set)
        freq_listener.set_bandwidth(bandwidth_to_set)

        self._radio_receiver.add_frequency_listener(freq_listener)

 
    def test_add_frequency_listener_with_lower_frequency(self):
        """Test adding a frequency listener to a RadioReceiver object 
        below the RadioReceivers minimum frequency."""
 
        radio_receiver = self._radio_receiver
 
        lower_from_radio_receiver = radio_receiver.get_lower_frequency()
 
        frequency_to_set = lower_from_radio_receiver
        bandwidth_to_set = 1000
        id_to_set = 'test_add_frequency_listener_with_lower_frequency'
        freq_listener = diatomite_base_classes.FreqListener(id_to_set)
        freq_listener.set_frequency(frequency_to_set)
        freq_listener.set_bandwidth(bandwidth_to_set)       
 
        try:
            radio_receiver.add_frequency_listener(freq_listener)
        except diatomite_base_classes.RadioReceiverFrequencyOutOfBounds:
            pass
        else:
            msg = ('{o} accepted a frequency below the minimum'
                   ' frequency').format(o=type(radio_receiver).__name__)
            assert False, msg
 
    def test_add_frequency_listener_with_higher_frequency(self):
        """Test adding a frequency listener to a RadioReceiver object above 
        the RadioReceivers maximum frequency."""
 
        radio_receiver = self._radio_receiver
 
        upper_from_radio_receiver = radio_receiver.get_upper_frequency()
         
        frequency_to_set = upper_from_radio_receiver
        bandwidth_to_set = 1000
        id_to_set = 'test_add_frequency_listener_with_higher_frequency'
        freq_listener = diatomite_base_classes.FreqListener(id_to_set)
        freq_listener.set_frequency(frequency_to_set)
        freq_listener.set_bandwidth(bandwidth_to_set)       
         
        try:
            radio_receiver.add_frequency_listener(freq_listener)
        except diatomite_base_classes.RadioReceiverFrequencyOutOfBounds:
            pass
        else:
            msg = ('{o} accepted a frequency above the maximum'
                   ' frequency').format(o=type(radio_receiver).__name__)
            assert False, msg


class testRTL2838R820T2RadioReceiver(object):
    """Test RTL2838R820T2RadioReceiver class"""
    _radio_receiver = diatomite_base_classes.RTL2838R820T2RadioReceiver()

#     def test_add_frequency_listener2(self):
#         """Test adding a frequency listener to a RadioReceiveraa object."""
#         pass
#         print 'XXXX'
        
class testDiatomiteProbe(object):
    """Test DiatomiteProbe class."""
    
    _diatomite_probe = diatomite_base_classes.DiatomiteProbe() 

    def test_add_radio_receiver(self):
        """Test adding a RadioReceiver to the DiatomiteProbe's RadioReceiverList."""
        
        r_receiver = diatomite_base_classes.RadioReceiver('test_add_radio_receiver')
        
        self._diatomite_probe.add_radio_receiver(r_receiver)
        
    def test_add_radio_receiver_wrong_type_fail(self):
        """Test adding an invalid type to the DiatomiteProbe's RadioReceiverList."""
        
        r_receiver = ''
        
        try:
            self._diatomite_probe.add_radio_receiver(r_receiver)
        except TypeError:
            pass
               
        

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
        
        radio_receiver = diatomite_base_classes.RadioReceiver()
         
        radio_receiver_list = diatomite_base_classes.RadioReceiverList()
         
        radio_receiver_list.append(radio_receiver)
        
        
class testFreqListenerList(object):
    
    def test_append_with_FreqListener_fail(self):
        """adding an object not of type FreqListenerList should raise a TypeError."""
        
        non_freq_listener = 'test'

        freq_receiver_list = diatomite_base_classes.FreqListenerList()
        try:
            freq_receiver_list.append(non_freq_listener)
        except TypeError:
            pass

    def test_append_with_FreqListener_sucess(self):
        """adding an object of FreqListener type is successful."""
        
        freq_listener= diatomite_base_classes.FreqListener()
        radio_receiver_list = diatomite_base_classes.FreqListenerList()
        radio_receiver_list.append(freq_listener)

class testFreqListener:
    
    def test_set_and_get_id(self):
        """Test setting and retrieving frequency id, Checks that string is stored as lower case."""
        id_to_set = 'test_id123-A'
        freq_listener = diatomite_base_classes.FreqListener()
        freq_listener.set_id(id_to_set)
        
        id_from_fl = freq_listener.get_id()
        
        if not id_to_set.lower() == id_from_fl:
            assert False, 'Id that was set was not returned correctly'

    def test_set_id_with_wrong_characters(self):
        """Test setting a frequency ID containing unacceptable characters."""
        
        id_to_set = 'test!@##$$%$%^'
        freq_listener = diatomite_base_classes.FreqListener()
        try:
            freq_listener.set_id(id_to_set)
        except diatomite_base_classes.FreqListenerBadIdError:
            pass
        else:
            assert False, 'FrequencyListener accepted an ID with unacceptable characters'
                     
    def test_set_and_get_frequency(self):
        """Test setting and retrieving frequency."""
        frequency_to_set = 123
        freq_listener = diatomite_base_classes.FreqListener()
        freq_listener.set_frequency(frequency_to_set)
        
        frequency_from_fl = freq_listener.get_frequency()
        
        if not frequency_to_set == frequency_from_fl:
            assert False, 'Frequency that was set was not returned correctly'
            
    def test_set_frequency_only_accepts_integer_numbers(self):
        """Test that set_frequency only accepts integer numbers."""
        frequency_to_set = 'blah'
        freq_listener = diatomite_base_classes.FreqListener()
        
        try:
            freq_listener.set_frequency(frequency_to_set)
        except ValueError:
            pass
        else:
            assert False, 'Frequency accepted alphabetic characters.'       

        frequency_to_set = 1.5
        freq_listener = diatomite_base_classes.FreqListener()
        
        try:
            freq_listener.set_frequency(frequency_to_set)
        except ValueError:
            pass
        else:
            assert False, 'Frequency accepted non integer number.'     

    def test_set_and_get_bandwidth(self):
        """Test setting and retrieving bandwidth."""
        bandwidth_to_set = 123
        freq_listener = diatomite_base_classes.FreqListener()
        freq_listener.set_bandwidth(bandwidth_to_set)
        
        bandwidth_from_fl = freq_listener.get_bandwidth()
        
        if not bandwidth_to_set == bandwidth_from_fl:
            assert False, 'Bandwidth that was set was not returned correctly.'

    def test_set_bandwidth_only_accepts_integer_numbers(self):
        """Test that set_bandwidth only accepts integer numbers."""
        bandwidth_to_set = 'blah'
        freq_listener = diatomite_base_classes.FreqListener()
        
        try:
            freq_listener.set_bandwidth(bandwidth_to_set)
        except ValueError:
            pass
        else:
            assert False, 'Bandwidth accepted alphabetic characters.'       

        frequency_to_set = 1.5
        freq_listener = diatomite_base_classes.FreqListener()
        
        try:
            freq_listener.set_bandwidth(frequency_to_set)
        except ValueError:
            pass
        else:
            assert False, 'Bandwidth accepted non integer number.'

    def test_set_and_get_modulation(self):
        """Test setting and retrieving modulation."""
        modulation_to_set = 'FM'
        freq_listener = diatomite_base_classes.FreqListener()
        freq_listener.set_modulation(modulation_to_set)
        
        modulation_from_fl = freq_listener.get_modulation()
        
        if not modulation_to_set.lower() == modulation_from_fl:
            assert False, 'modulation that was set was not returned correctly'   

    def test_set_unacceptable_modulation(self):
        """Test setting an unacceptable modulation."""
        modulation_to_set = 'blaaah'
        freq_listener = diatomite_base_classes.FreqListener()
         
        try:
            freq_listener.set_modulation(modulation_to_set)
        except diatomite_base_classes.FreqListenerBadModulation:
            pass
        else:
            assert False, 'FrequencyListener accepted an unacceptable modulation'

    def test_get_upper_frequency(self):
        """Test retrieving the upper frequency of the Listener."""
        
        frequency_to_set = 12000
        bandwidth_to_set = 1000
        upper_freq = frequency_to_set + (bandwidth_to_set/2)
        
        freq_listener = diatomite_base_classes.FreqListener()
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
        
        freq_listener = diatomite_base_classes.FreqListener()
        freq_listener.set_frequency(frequency_to_set)
        freq_listener.set_bandwidth(bandwidth_to_set)
        
        lower_from_freq_listener = freq_listener.get_lower_frequency()
        
        if not lower_from_freq_listener == lower_freq:
            assert False, 'Frequency listener not returning correct lower frequency.'
              

class testRadioReceiver(object):
 
    _radio_receiver = diatomite_base_classes.RadioReceiver()
   
    def test_get_upper_frequency(self):
        """Test retrieving the upper frequency of the RadioReceiver.
        Also check it is a whole number and larger than zero."""
         
        radio_receiver = self._radio_receiver
 
        upper_from_radio_receiver = radio_receiver.get_upper_frequency()
         
        if not float(upper_from_radio_receiver).is_integer():
            assert False, '{o} not returning a valid upper frequency (number is not whole).'.format(o=type(radio_receiver).__name__)
             
        if not upper_from_radio_receiver >= 1:
            assert False, '{o} not returning a valid upper frequency (number is lower than 1).'.format(o=type(radio_receiver).__name__)
           
    def test_get_lower_frequency(self):
        """Test retrieving the lower frequency of the RadioReceiver.
          Also check it is a whole number and larger than zero."""
           
        radio_receiver = self._radio_receiver
 
        lower_from_radio_receiver = radio_receiver.get_lower_frequency()
         
        if not float(lower_from_radio_receiver).is_integer():
            assert False, '{o} not returning a valid lower frequency (number is not whole).'.format(o=type(radio_receiver).__name__)
             
        if not lower_from_radio_receiver >= 1:
            assert False, '{o} not returning a valid lower frequency (number is lower than 1).'.format(o=type(radio_receiver).__name__)
 
 
    def test_get_bandwidth_capability(self):
        """Test retrieving the bandwidth capability of the RadioReceiver.
          Also check it is a whole number and larger than zero."""
           
        radio_receiver = self._radio_receiver
       
        bandwidth_capability_from_radio_receiver = radio_receiver.get_bandwidth_capability()
         
        if not float(bandwidth_capability_from_radio_receiver).is_integer():
            assert False, '{o} not returning a valid bandwidth capability (number is not whole).'.format(o=type(radio_receiver).__name__)
             
        if not bandwidth_capability_from_radio_receiver >= 1:
            assert False, '{o} not returning a valid bandwidth capability (number is lower than 1).'.format(o=type(radio_receiver).__name__)
 
    def test_add_frequency_listener(self):
        """Test adding a frequency listener to a {o} object.""".format(o=type(self._radio_receiver).__name__)
         
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

        freq_listener = diatomite_base_classes.FreqListener()
        freq_listener.set_frequency(frequency_to_set)
        freq_listener.set_bandwidth(bandwidth_to_set)       
         
        self._radio_receiver.add_frequency_listener(freq_listener)
 
    def test_add_frequency_listener_with_lower_frequency(self):
        """Test adding a frequency listener to a RadioReceiver object below the RadioReceivers minimum frequency."""
 
        radio_receiver = self._radio_receiver
 
        lower_from_radio_receiver = radio_receiver.get_lower_frequency()
 
        frequency_to_set = lower_from_radio_receiver
        bandwidth_to_set = 1000
        freq_listener = diatomite_base_classes.FreqListener()
        freq_listener.set_frequency(frequency_to_set)
        freq_listener.set_bandwidth(bandwidth_to_set)       
 
        try:
            radio_receiver.add_frequency_listener(freq_listener)
        except diatomite_base_classes.RadioReceiverFrequencyOutOfBounds:
            pass
        else:
            assert False, '{o} accepted a frequency below the minimum frequency'.format(o=type(radio_receiver).__name__)
 
    def test_add_frequency_listener_with_higher_frequency(self):
        """Test adding a frequency listener to a RadioReceiver object above the RadioReceivers maximum frequency."""
 
        radio_receiver = self._radio_receiver
 
        upper_from_radio_receiver = radio_receiver.get_upper_frequency()
         
        frequency_to_set = upper_from_radio_receiver
        bandwidth_to_set = 1000
        freq_listener = diatomite_base_classes.FreqListener()
        freq_listener.set_frequency(frequency_to_set)
        freq_listener.set_bandwidth(bandwidth_to_set)       
         
        try:
            radio_receiver.add_frequency_listener(freq_listener)
        except diatomite_base_classes.RadioReceiverFrequencyOutOfBounds:
            pass
        else:
            assert False, '{o} accepted a frequency above the maximum frequency'.format(o=type(radio_receiver).__name__)


class testRTL2838R820T2RadioReceiver(testRadioReceiver):
 
    _radio_receiver = diatomite_base_classes.RTL2838R820T2RadioReceiver()


#     def test_append_check_FreqListener_below_min_freq_fail(self):
#         """check that when a frequency listener (and the lower half of bw) is below the
#         receivers minimum frequency, it fails adding the listener to a receiver's 
#         listener list."""
#         
#         assert False, 'This test is not finished'
# 
#     def test_append_check_FreqListener_above_max_freq_fail(self):
#         """check that when a frequency listener (and the upper half of bw) is above the
#         receivers maximum frequency, it fails adding the listener to a receiver's
#         listener list."""
#         
#         assert False, 'This test is not finished'
# 
#     def test_append_check_FreqListener_whitin_limits_pass(self):
#         """check that a frequency listener (and the whole bw) is within the 
#         receiver's limits it can be added to a receiver's listener list."""
#         
#         assert False, 'This test is not finished'
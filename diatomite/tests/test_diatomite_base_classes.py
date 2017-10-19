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
import osmosdr
from gnuradio import gr
import time

class TestDataTap(object):
    """Test the DataTap class"""
    
    id_to_set = 'test_data_tap'
    _test_data_tap = diatomite_base_classes.DataTap(id_to_set)
    
    def test_init_and_stop(self):
        id_to_set = 'test_init_and_stop'
        
        try:
            dt = diatomite_base_classes.DataTap(id_to_set)
        except Exception, excpt:
            msg = ('Unable to initialize  DataTap,'
                   ' with {e}').format(e=excpt)
            assert False, msg
            
        try:
            dt.stop()
        except Exception, excpt:
            msg = ('DataTap stop failed,'
                   ' with {e}').format(e=excpt)
            assert False, msg
            
    def test_set_and_get_id(self):
        """Test setting and retrieving data tap id, Checks that string is
        stored as lower case."""
        id_to_set = 'test_id123-A'
        data_tap = diatomite_base_classes.DataTap(id_to_set)
        data_tap._set_id(id_to_set)

        id_from_dt = data_tap._get_id()

        if not id_to_set.lower() == id_from_dt:
            assert False, 'Id that was set was not returned correctly'
            
        data_tap.stop()

    def test_set_id_with_wrong_characters(self):
        """Test setting a datatap ID containing unacceptable characters."""

        # needs to be initialized correctly
        id_to_set = 'initial'
        data_tap = diatomite_base_classes.DataTap(id_to_set)
        id_to_set = 'test!@##$$%$%^'
        try:
            data_tap._set_id(id_to_set)
        except diatomite_base_classes.BadIdError:
            pass
        else:
            data_tap.stop()
            msg = ('datatap accepted an ID with unacceptable '
                   'characters')
            assert False, msg

    def get_file(self):
        """"Test getting the file name."""
        self._test_data_tap._get_file()

    def test_get_value(self):
        """Test retrieving the value"""
      
        val_to_set = 'test_get_value'
        self._test_data_tap.update_value(val_to_set)
       
        val_from_gv = self._test_data_tap._get_value()
        
        if val_from_gv != val_to_set:
            msg = ('_get_value returned a different value than it was set to.'
                   'expected:{vts}, returned:{vfg}').format(vts=val_to_set, 
                                                            vfg=val_from_gv)
            assert False, msg

    def test_output(self):
        """Test output of tap"""
        
        # use a different DataTap to ensure the file isn't overwritten by other thread
        id_to_set = 'test_output'
        test_data_tap = diatomite_base_classes.DataTap(id_to_set)
        
        file_path = test_data_tap._get_file()
  
        val_to_set2 = 'test_output'
        test_data_tap.update_value(val_to_set2)
             
        # wait for the file to be ready
        time.sleep(2)
        tap_file = open(file_path,'r')
        file_contents = tap_file.readline().rstrip()
          
        if file_contents != val_to_set2:
            msg = ('value in file differs from what is expected.'
                   'expected:{vts}, on file:{vff}').format(vts=val_to_set2, 
                                                            vff=file_contents)
            assert False, msg           

        test_data_tap.stop() 

    def test_stop(self):
        """Test the stop method."""
        # must be last to clean up the object set at the start of this test set
         
        self._test_data_tap.stop()
        


class TestRadioSourceList(object):
    """Test the RadioSourceList class"""

    def test_append_with_non_RadioSource_fail(self):
        """adding an object not of type RadioSource should raise a
        TypeError."""

        non_radio_source = 'test'

        radio_source_list = diatomite_base_classes.RadioSourceList()
        try:
            radio_source_list.append(non_radio_source)
        except TypeError:
            pass

    def test_append_with_RadioSource_sucess(self):
        """adding an object of type RadioSource is successful."""

        rs_id = 'test_append_with_RadioSource_sucess'
        radio_source = diatomite_base_classes.RadioSource(rs_id)

        radio_source_list = diatomite_base_classes.RadioSourceList()

        radio_source_list.append(radio_source)

    def test_get_receiver_id_list(self):
        """Test retrieving the list of radio source ids"""
        # define an empty FreqListenerList
        radio_source_list = diatomite_base_classes.RadioSourceList()

        # add a few elements to the freq list and control list
        id_to_set_a = 'test_a'
        id_to_set_b = 'test_b'
        radio_source_a = diatomite_base_classes.RadioSource(id_to_set_a)
        radio_source_b = diatomite_base_classes.RadioSource(id_to_set_b)
        radio_source_list.append(radio_source_a)
        radio_source_list.append(radio_source_b)
        control_list = []
        control_list.append(id_to_set_a.lower())
        control_list.append(id_to_set_b.lower())

        freq_listener_id_list = radio_source_list.get_radio_source_id_list()

        if not isinstance(freq_listener_id_list, list):
            msg = ('RadioSource.get_listener_id_list did not return a list')
            assert False, msg

        if control_list != freq_listener_id_list:
            msg = ('RadioSource.get_listener_id_list did not return the'
                   ' expected list contents')
            assert False, msg

    def test_append_repeating_id_fail(self):
        """Adding an already existing id should fail."""
        # define an empty FreqListenerList
        radio_source_list = diatomite_base_classes.RadioSourceList()

        # add a few elements to the freq list and control list
        id_to_set_a = 'test_a'
        id_to_set_b = 'test_a'
        radio_source_a = diatomite_base_classes.RadioSource(id_to_set_a)
        radio_source_b = diatomite_base_classes.RadioSource(id_to_set_b)
        radio_source_list.append(radio_source_a)
        control_list = []

        control_list.append(id_to_set_a.lower())
        control_list.append(id_to_set_b.lower())

        try:
            radio_source_list.append(radio_source_b)
        except diatomite_base_classes.RadioSourceListIdNotUniqueError:
            pass
        else:
            msg = 'RadioSourceList accepted an existing ID'
            assert False, msg


class TestRadioSpectrum(object):
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
            msg = ('{o} not returning a valid upper frequency (number is lower'
                   ' than 1).').format(o=type(self._radio_spectrum).__name__)
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


class TestFreqListenerList(object):
    """Test FreqListenerList."""

    fl_id = 'testFreqListenerList'
    _freq_listener = diatomite_base_classes.FreqListener(fl_id)
    _freq_listener_list = diatomite_base_classes.FreqListenerList()

    def test_append_with_non_FreqListener_fail(self):
        """adding an object not of type FreqListenerList should raise a
        TypeError."""

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
        """Test retrieving list of listener ids."""

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
            msg = ('FreqListenerList.get_listener_id_list did not return a'
                   ' list')
            assert False, msg

        if control_list != freq_listener_id_list:
            msg = ('FreqListenerList.get_listener_id_list did not return the'
                   ' expected list contents')
            assert False, msg


class TestFreqListener(object):
    """Test the FreqListener class"""

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
        except diatomite_base_classes.BadIdError:
            pass
        else:
            msg = ('FrequencyListener accepted an ID with unacceptable '
                   'characters')
            assert False, msg

    def test_set_empty_id(self):
        """Test setting a frequency ID containing unacceptable characters."""

        id_to_set = 'test_set_empty_id'
        freq_listener = diatomite_base_classes.FreqListener(id_to_set)
        id_to_set = ''
        try:
            freq_listener.set_id(id_to_set)
        except diatomite_base_classes.BadIdError:
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

    def test_set_and_get_radio_source_bw(self):
        """Test setting and getting the radio source bandwidth for this
        listener"""

        id_to_set = 'test_set_and_get_radio_source_bw'
        freq_listener = diatomite_base_classes.FreqListener(id_to_set)

        radio_source_bw_to_set = 1000

        freq_listener.set_radio_source_bw(radio_source_bw_to_set)

        if radio_source_bw_to_set != freq_listener.get_radio_source_bw():
            msg = ('Radio source bandwidth that was set was not'
                   ' returned correctly')
            assert False, msg

    def test_set_frequency_below_radio_spectrum_minimums(self):
        """Test setting the frequency below the radio spectrum minimums."""
        radio_spectrum = diatomite_base_classes.RadioSpectrum()
        radio_spectrum_minimums = radio_spectrum.get_lower_frequency()
        id_to_set = 'test_set_frequency_below_radio_spectrum_minimums'
        freq_listener = diatomite_base_classes.FreqListener(id_to_set)

        if radio_spectrum_minimums <= 1000:
            frequency_to_set = radio_spectrum_minimums - 1
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

        frequency_to_set = radio_spectrum_maximums + 1000

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

    def test_frequency_offset(self):
        """Test setting the frequency offset."""

        id_to_set = 'test_frequency_offset'
        freq_listener = diatomite_base_classes.FreqListener(id_to_set)

        listener_freq = 200000
        radio_source_freq = 600000

        # set the listener frequency
        freq_listener.set_frequency(listener_freq)

        # set the offset
        freq_listener.set_frequency_offset(radio_source_freq)

        # calculate offset
        if listener_freq < radio_source_freq:
            offset = (radio_source_freq - listener_freq) * -1
        elif listener_freq > radio_source_freq:
            offset = radio_source_freq - listener_freq
        else:
            offset = 0

        returned_offset = freq_listener.get_frequency_offset()

        if returned_offset == offset:
            pass
        else:
            msg = ('Frequency offset not correct . Should be {o}, but got'
                   ' {ro}').format(o=offset, ro=returned_offset)
            assert False, msg

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

    def test_set_gr_radio_source(self):
        """Test setting the gnu radio radio source."""
        
        id_to_set = 'test_set_gr_radio_source'
        # use one of the derived Classes from RadioSource for which you have 
        # hardware connected
        radio_source = diatomite_base_classes.RTL2838R820T2RadioSource(id_to_set)
        freq_listener = diatomite_base_classes.FreqListener(id_to_set)
        
        radio_source._radio_init()
        radio_source_block = radio_source.get_source_block()
        
        try:
            freq_listener.set_source_block(radio_source_block)
        except Exception, exc:
            msg = ('Failed radio init with {m} for'
                   ' Class {c}').format(m=str(exc), c=type(radio_source))
            assert False, msg


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
            msg = 'FrequencyListener accepted an unacceptable modulation'
            assert False, msg
            
    def test_set_gr_top_block(self):
        """Test setting the gnuradio top block."""

        # setup a RadioSource
        radio_source = diatomite_base_classes.RTL2838R820T2RadioSource('test_set_gr_top_block')
        radio_source._radio_init()

        frequency_to_set = 12000
        bandwidth_to_set = 1000

        id_to_set = 'test_set_gr_top_block'
        freq_listener = diatomite_base_classes.FreqListener(id_to_set)
        freq_listener.set_frequency(frequency_to_set)
        freq_listener.set_bandwidth(bandwidth_to_set)
        
        gr_top_block = radio_source.get_gr_top_block()

        freq_listener.set_gr_top_block(gr_top_block)

    def test_set_gr_top_block_wrong_type(self):
        """Test setting the gnuradio top block with a wrong type."""

        frequency_to_set = 12000
        bandwidth_to_set = 1000

        id_to_set = 'test_set_gr_top_block'
        freq_listener = diatomite_base_classes.FreqListener(id_to_set)
        freq_listener.set_frequency(frequency_to_set)
        freq_listener.set_bandwidth(bandwidth_to_set)
        
        try:
            freq_listener.set_gr_top_block('ola')
        except TypeError:
            pass
        else:
            msg = 'set_gr_top_block accepted an object of wrong type.'
            assert False, msg
          
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
            msg = 'Frequency listener not returning correct upper frequency.'
            assert False, msg

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
            msg = 'Frequency listener not returning correct lower frequency.'
            assert False, msg

    def test_connect_frequency_translator_to_source(self):
        """Test connecting the frequency translation filter to a gnu radio 
        source."""
        
        # setup a RadioSource
        radio_source = diatomite_base_classes.RTL2838R820T2RadioSource('testRadioSource')
        radio_source._radio_init()
        
        # setup a FrequencyListener
        id_to_set = 'test_connect_frequency_translator_to_source'
        freq_listener = diatomite_base_classes.FreqListener(id_to_set)
        
        # determine radio frequency to use on listener
        # use the radio source center frequency as datum
        frequency_to_set = radio_source.get_center_frequency() - 1000
        freq_listener.set_frequency(frequency_to_set)
        
        # get the gnu radio source
        source_block = radio_source.get_source_block()
        freq_listener.set_source_block(source_block)
        
        # get the gnu radio top block
        gr_top_block = radio_source.get_gr_top_block()
        freq_listener.set_gr_top_block(gr_top_block)
        
        # configure the frequency translator
        try:
            freq_listener._config_frequency_translation()
        except Exception, exc:
            msg =('Failed to configure frequency translator for'
                  ' Class {c}, with {m}').format(m=str(exc), 
                                                 c=type(radio_source))
            assert False, msg
                 
        # connect the frequency translator to the source
        try:
            freq_listener._connect_frequency_translator_to_source()
        except Exception, exc:
            msg =('Failed to connect frequency translator for'
                  ' Class {c}, with {m}').format(m=str(exc), 
                                                 c=type(radio_source))
            assert False, msg

    def test_setup_rf_fft(self):
        """Test setting up an fft"""
        
        # setup a RadioSource
        radio_source = diatomite_base_classes.RTL2838R820T2RadioSource('testRadioSource')
        radio_source._radio_init()
        
        # setup a FrequencyListener
        id_to_set = 'test_setup_rf_fft'
        freq_listener = diatomite_base_classes.FreqListener(id_to_set)
        
        # determine radio frequency to use on listener
        # use the radio source center frequency as datum
        frequency_to_set = radio_source.get_center_frequency() - 1000
        freq_listener.set_frequency(frequency_to_set)
        
        # get the gnu radio source
        source_block = radio_source.get_source_block()
        freq_listener.set_source_block(source_block)
        
        # get the gnu radio top block
        gr_top_block = radio_source.get_gr_top_block()
        freq_listener.set_gr_top_block(gr_top_block)
        
        # configure the frequency translator
        try:
        
            freq_listener._config_frequency_translation()
        except Exception, exc:
            msg =('Failed to configure frequency translator for'
                  ' Class {c}, with {m}').format(m=str(exc), 
                                                 c=type(radio_source))
            assert False, msg
                 
        # connect the frequency translator to the source
        try:
            freq_listener._connect_frequency_translator_to_source()
        except Exception, exc:
            msg =('Failed to connect frequency translator for'
                  ' Class {c}, with {m}').format(m=str(exc), 
                                                 c=type(radio_source))
            assert False, msg      
        
        try:
            freq_listener._setup_rf_fft()
        except Exception, exc:
            msg =('Failed to setup fft for'
                  ' Class {c}, with {m}').format(m=str(exc), 
                                                 c=type(radio_source))
            assert False, msg   

    def test_setup_stop_signal_probe(self):
        """Test setting up and stopping the signal probe"""
 
        # setup a RadioSource
        radio_source = diatomite_base_classes.RTL2838R820T2RadioSource('testRadioSource')
        radio_source._radio_init()
        
        # setup a FrequencyListener
        id_to_set = 'test_setup_signal_probe'
        freq_listener = diatomite_base_classes.FreqListener(id_to_set)
        
        # determine radio frequency to use on listener
        # use the radio source center frequency as datum
        frequency_to_set = radio_source.get_center_frequency() - 1000
        freq_listener.set_frequency(frequency_to_set)
        
        # get the gnu radio source
        source_block = radio_source.get_source_block()
        freq_listener.set_source_block(source_block)
        
        # get the gnu radio top block
        gr_top_block = radio_source.get_gr_top_block()
        freq_listener.set_gr_top_block(gr_top_block)
        
        # configure the frequency translator
        try:
        
            freq_listener._config_frequency_translation()
        except Exception, exc:
            msg =('Failed to configure frequency translator for'
                  ' Class {c}, with {m}').format(m=str(exc), 
                                                 c=type(radio_source))
            assert False, msg

        # connect the frequency translator to the source
        try:
            freq_listener._connect_frequency_translator_to_source()
        except Exception, exc:
            msg =('Failed to connect frequency translator for'
                  ' Class {c}, with {m}').format(m=str(exc), 
                                                 c=type(radio_source))
            assert False, msg      
        
        try:
            freq_listener._setup_rf_fft()
        except Exception, exc:
            msg =('Failed to setup fft for'
                  ' Class {c}, with {m}').format(m=str(exc), 
                                                 c=type(radio_source))
            assert False, msg   
        
        try:
            freq_listener._setup_signal_probe()
        except Exception, exc:
            msg =('Failed to setup fft for'
                  ' Class {c}, with {m}').format(m=str(exc), 
                                                 c=type(radio_source))
            assert False, msg   
            
        try:
            freq_listener._stop_signal_probe()
        except Exception, exc:
            msg =('Failed to stop fft signal probe'
                  ' Class {c}, with {m}').format(m=str(exc), 
                                                 c=type(radio_source))
            assert False, msg   

    def test_start_stop(self):
        """Test starting and stopping the frequency listener"""
 
        # setup a RadioSource
        radio_source = diatomite_base_classes.RTL2838R820T2RadioSource('testRadioSource')
        radio_source._radio_init()
        
        # setup a FrequencyListener
        id_to_set = 'test_connect_frequency_translator_to_source'
        freq_listener = diatomite_base_classes.FreqListener(id_to_set)
        
        # determine radio frequency to use on listener
        # use the radio source center frequency as datum
        frequency_to_set = radio_source.get_center_frequency() - 1000
        freq_listener.set_frequency(frequency_to_set)
        
        # get the gnu radio source
        source_block = radio_source.get_source_block()
        freq_listener.set_source_block(source_block)
        
        # get the gnu radio top block
        gr_top_block = radio_source.get_gr_top_block()
        freq_listener.set_gr_top_block(gr_top_block)
        
        # start the listener
        try:
        
            freq_listener.start()
        except Exception, exc:
            msg =('Failed to start the listener'
                  ' Class {c}, with {m}').format(m=str(exc), 
                                                 c=type(radio_source))
            assert False, msg
            
        time.sleep(5)    
        
        try:
            freq_listener.stop()
        except Exception, exc:
            msg =('Failed to stop the listener'
                  ' Class {c}, with {m}').format(m=str(exc), 
                                                 c=type(radio_source))
            assert False, msg          


    def test_set_and_get_create_fft_tap(self):
        """Test set_create_fft_tap and get_create_fft_tap"""
        create_fft_tap = True
        id_to_set = 'test_set_and_get_create_fft_tap'
        freq_listener = diatomite_base_classes.FreqListener(id_to_set)
        
        try:
            freq_listener.set_create_fft_tap(create_fft_tap)
        except Exception, exc:
            msg =('Failed to set_create_fft_tap'
                  ' with {m}').format(m=str(exc))
            assert False, msg

        try:
            create_fft_tap_from_fl = freq_listener.get_create_fft_tap()
        except Exception, exc:
            msg =('Failed to get_create_fft_tap'
                  ' with {m}').format(m=str(exc))
            assert False, msg

        if not create_fft_tap == create_fft_tap_from_fl:
            assert False, 'Value set on set_create_fft_tap no returned correctly.'

    def test_set_create_fft_tap_with_bad_value(self):
        """Test set_create_fft_tap with a non boolean"""
        create_fft_tap = 25
        id_to_set = 'test_set_create_fft_tap_with_bad_value'
        freq_listener = diatomite_base_classes.FreqListener(id_to_set)
        
        try:
            freq_listener.set_create_fft_tap(create_fft_tap)
        except TypeError:
            pass
        else:
            msg = 'set_create_fft_tap accepted non boolean value!'
            assert False, msg

class TestRadioSource(object):
    """Test the RadioSource class"""

    _radio_source = diatomite_base_classes.RadioSource('testRadioSource')
    _radio_spectrum = diatomite_base_classes.RadioSpectrum()

    def test_init_without_id(self):
        """Test the initialization without passing an id"""
        try:
            diatomite_base_classes.RadioSource()
        except TypeError:
            pass
        else:
            msg = 'RadioSource accepted instanciation without id'
            assert False, msg

    def test_set_empty_id(self):
        """Test setting a frequency ID containing unacceptable characters."""

        id_to_set = 'test_set_empty_id'
        radio_source = diatomite_base_classes.RadioSource(id_to_set)
        id_to_set = ''
        try:
            radio_source.set_id(id_to_set)
        except diatomite_base_classes.BadIdError:
            pass
        else:
            assert False, 'RadioSource accepted an empty ID'

    def test_set_and_get_id(self):
        """Test setting and retrieving receiver id, Checks that string is
        stored as lower case."""
        id_to_set = 'test_id123-A'
        self._radio_source.set_id(id_to_set)

        id_from_rr = self._radio_source.get_id()

        if not id_to_set.lower() == id_from_rr:
            assert False, 'Id that was set was not returned correctly'

    def test_set_id_with_wrong_characters(self):
        """Test setting a receiver ID containing unacceptable characters."""

        id_to_set = 'test!@##$$%$%^'
        try:
            self._radio_source.set_id(id_to_set)
        except diatomite_base_classes.BadIdError:
            pass
        else:
            msg = 'RadioSource accepted an ID with unacceptable characters'
            assert False, msg

    def test_set_frequency_below_source_minimums(self):
        """Test setting the frequency below the radio spectrum minimums."""
        
        radio_source_minimuns = self._radio_source.get_lower_frequency()

        if radio_source_minimuns <= 1000:
            frequency_to_set = radio_source_minimuns - 1
        else:
            frequency_to_set = radio_source_minimuns - 1000

        try:
            self._radio_source.set_frequency(frequency_to_set)
        except ValueError:
            pass
        else:
            msg = 'FreqListener accepted frequency below radio source limits'
            assert False, msg

    def test_set_frequency_above_radio_source_maximums(self):
        """Test setting the frequency above the radio source maximums."""

        radio_source_maximums = self._radio_source.get_upper_frequency()

        frequency_to_set = radio_source_maximums + 1000

        try:
            self._radio_source.set_frequency(frequency_to_set)
        except ValueError:
            pass
        else:
            msg = 'FreqListener accepted frequency above radio spectrum limits'
            assert False, msg

    def test_set_frequency_only_accepts_integer_numbers(self):
        """Test that set_frequency only accepts integer numbers."""
        frequency_to_set = 'blah'

        try:
            self._radio_source.set_frequency(frequency_to_set)
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

    def test_get_upper_frequency(self):
        """Test retrieving the upper frequency of the RadioSource.
        Also check it is a whole number and larger than zero."""

        upper_from_radio_source = self._radio_source.get_upper_frequency()
        rs_upper_frequency = self._radio_spectrum.get_upper_frequency()

        if not float(upper_from_radio_source).is_integer():
            msg = ('{o} not returning a valid upper frequency (number is not'
                   ' whole).').format(o=type(self._radio_source).__name__)
            assert False, msg

        if not upper_from_radio_source <= rs_upper_frequency:
            msg = ('{o} not returning a valid upper frequency (number is above'
                   ' radio spectrum {urs}).').format(
                       o=type(self._radio_source).__name__,
                       urs=rs_upper_frequency)
            assert False, msg

    def test_get_lower_frequency(self):
        """Test retrieving the lower frequency of the RadioSource.
          Also check it is a whole number and larger than zero."""

        lower_from_radio_source = self._radio_source.get_lower_frequency()
        rs_lower_frequency = self._radio_spectrum.get_lower_frequency()

        if not float(lower_from_radio_source).is_integer():
            msg = ('{o} not returning a valid lower frequency (number is not'
                   ' whole).').format(o=type(self._radio_source).__name__)
            assert False, msg

        if not lower_from_radio_source >= rs_lower_frequency:
            msg = ('{o} not returning a valid lower frequency (number is below'
                   ' radio spectrum {lrs}).').format(
                       o=type(self._radio_source).__name__,
                       lrs=rs_lower_frequency)
            assert False, msg

    def test_get_bandwidth_capability(self):
        """Test retrieving the bandwidth capability of the RadioSource.
          Also check it is a whole number and larger than zero."""

        bw_cap_from_rsource = self._radio_source.get_bandwidth_capability()

        if not float(bw_cap_from_rsource).is_integer():
            msg = ('{o} not returning a valid bandwidth capability (number'
                   ' is not'
                   ' whole).').format(o=type(self._radio_source).__name__)
            assert False, msg

        if not bw_cap_from_rsource >= 1:
            msg = ('{o} not returning a valid bandwidth capability'
                   ' (number is lower'
                   ' than 1).').format(o=type(self._radio_source).__name__)
            assert False, msg

    def test_get_center_frequency(self):
        """Test retrieving the center frequency."""

        # get lower and upper frequencies
        lower_from_radio_source = self._radio_source.get_lower_frequency()
        upper_from_radio_source = self._radio_source.get_upper_frequency()

        # get the center frequency:
        center_frequency = self._radio_source.get_center_frequency()

        if (lower_from_radio_source <= center_frequency
                <= upper_from_radio_source):
            pass
        else:
            msg = ('Radio Source returned a center frequency outside of'
                   ' capabilities. Center frequency:{cf}, mini freq {lf}'
                   ' max freq:{uf}').format(cf=center_frequency,
                                            lf=lower_from_radio_source,
                                            uf=upper_from_radio_source)
            assert False, msg

    def test_radio_init(self):
        """Test the radio initialization"""

        try:
            self._radio_source._radio_init()
        except diatomite_base_classes.RadioSourceRadioFailureError, exc:
            msg = ('Failed radio init with {m} for'
                   ' Class {c}').format(m=str(exc), c=type(self._radio_source))
            assert False, msg
# 
#     def test_get_source_block(self):
#         """Test retrieving the gnu radio source."""
# 
#         self._radio_source._radio_init()
#         try:
#             source_block = self._radio_source.get_source_block()
#         except Exception, excpt:
#             msg = ('Failed getting radios source for Class {c},'
#                    ' with {e}').format(c=type(self._radio_source), e=excpt)
#             assert False, msg
#         else:
#             print 'type or rsource:{trs}'.format(trs=type(rsource))

#     def test_add_frequency_listener(self):
#         """Test adding a frequency listener to a RadioSource object."""
#         # get the radio's frequency limits
#         upper_from_radio_source = self._radio_source.get_upper_frequency()
#         lower_from_radio_source = self._radio_source.get_lower_frequency()
# 
#         # calculate the bandwidth
#         bwidth = upper_from_radio_source - lower_from_radio_source
# 
#         # define the center frequency midway from upper and lower
#         center_freq = (bwidth/2) + lower_from_radio_source
#         frequency_to_set = center_freq
# 
#         # ensure the bandwidth fits the radio
#         bandwidth_to_set = bwidth/2
# 
#         id_to_set = 'test_add_frequency_listener'
#         freq_listener = diatomite_base_classes.FreqListener(id_to_set)
#         freq_listener.set_frequency(frequency_to_set)
#         freq_listener.set_bandwidth(bandwidth_to_set)
#         
#         self._radio_source._radio_init()
# 
#         print '////////////////t:{t}'.format(t=type(self._radio_source))
#         self._radio_source.add_frequency_listener(freq_listener)

    def test_add_frequency_listener_with_lower_frequency(self):
        """Test adding a frequency listener to a RadioSource object
        below the RadioSources minimum frequency."""

        radio_source = self._radio_source

        lower_from_radio_source = radio_source.get_lower_frequency()

        frequency_to_set = lower_from_radio_source
        bandwidth_to_set = 1000
        id_to_set = 'test_add_frequency_listener_with_lower_frequency'
        freq_listener = diatomite_base_classes.FreqListener(id_to_set)
        freq_listener.set_frequency(frequency_to_set)
        freq_listener.set_bandwidth(bandwidth_to_set)

        try:
            radio_source.add_frequency_listener(freq_listener)
        except diatomite_base_classes.RadioSourceFrequencyOutOfBounds:
            pass
        else:
            msg = ('{o} accepted a frequency below the minimum'
                   ' frequency').format(o=type(radio_source).__name__)
            assert False, msg

    def test_add_frequency_listener_with_higher_frequency(self):
        """Test adding a frequency listener to a RadioSource object above
        the RadioSources maximum frequency."""

        upper_from_radio_source = self._radio_source.get_upper_frequency()

        frequency_to_set = upper_from_radio_source
        bandwidth_to_set = 1000
        id_to_set = 'test_add_frequency_listener_with_higher_frequency'
        freq_listener = diatomite_base_classes.FreqListener(id_to_set)
        freq_listener.set_frequency(frequency_to_set)
        freq_listener.set_bandwidth(bandwidth_to_set)

        try:
            self._radio_source.add_frequency_listener(freq_listener)
        except diatomite_base_classes.RadioSourceFrequencyOutOfBounds:
            pass
        else:
            msg = ('{o} accepted a frequency above the maximum'
                   ' frequency').format(o=type(self._radio_source).__name__)
            assert False, msg


class TestRTL2838R820T2RadioSource(object):
    """Test RTL2838R820T2RadioSource class"""
    rs_id = 'testRTL2838R820T2RadioSource'
    _radio_source = diatomite_base_classes.RTL2838R820T2RadioSource(rs_id)

    def test_radio_init(self):
        """Test the radio initialization"""

        try:
            self._radio_source._radio_init()
        except diatomite_base_classes.RadioSourceRadioFailureError, excpt:
            msg = ('Failed radio init with {m} for Class'
                   ' {c}').format(m=str(excpt), c=type(self._radio_source))
            assert False, msg

    def test_get_source_block(self):
        """Test retrieving the gnu radio source."""

        self._radio_source._radio_init()
        try:
            source_block = self._radio_source.get_source_block()
        except Exception, excpt:
            msg = ('Failed getting radios source for Class {c},'
                   ' with {e}').format(c=type(self._radio_source), e=excpt)
            assert False, msg

        if not type(source_block) == osmosdr.osmosdr_swig.source_sptr:
            msg = ('get_radio_source returned wrong type. Class being'
                   ' tested:{c}').format(c=type(self._radio_source))
            assert False, msg

    def test_add_frequency_listener(self):
        """Test adding a frequency listener to a RadioSource object."""
        # get the radio's frequency limits
        upper_from_radio_source = self._radio_source.get_upper_frequency()
        lower_from_radio_source = self._radio_source.get_lower_frequency()

        # calculate the bandwidth
        bwidth = upper_from_radio_source - lower_from_radio_source

        # define the center frequency midway from upper and lower
        center_freq = (bwidth/2) + lower_from_radio_source
        frequency_to_set = center_freq

        # ensure the bandwidth fits the radio
        bandwidth_to_set = bwidth/2

        id_to_set = 'test_add_frequency_listener'
        freq_listener = diatomite_base_classes.FreqListener(id_to_set)
        freq_listener.set_frequency(frequency_to_set)
        freq_listener.set_bandwidth(bandwidth_to_set)
        
        self._radio_source._radio_init()

        self._radio_source.add_frequency_listener(freq_listener)

    def test_get_gr_top_block(self):
        """Test getting the gnuradio top block."""
        
        self._radio_source._radio_init()
        
        gr_top_block = self._radio_source.get_gr_top_block()
                        
        if not type(gr_top_block) == gr.top_block:
            msg = 'get_gr_top_block returned a wrong type'
            assert False, msg


    def test_start_and_stop_frequency_listeners(self):
        """Test starting and stopping the frequency listeners"""

        # add a new frequency listener
        # get the radio's frequency limits
        upper_from_radio_source = self._radio_source.get_upper_frequency()
        lower_from_radio_source = self._radio_source.get_lower_frequency()

        # calculate the bandwidth
        bwidth = upper_from_radio_source - lower_from_radio_source

        # define the center frequency midway from upper and lower
        center_freq = (bwidth/2) + lower_from_radio_source
        frequency_to_set = center_freq

        # ensure the bandwidth fits the radio
        bandwidth_to_set = bwidth/2

        id_to_set = 'test_start_frequency_listeners'
        freq_listener = diatomite_base_classes.FreqListener(id_to_set)
        freq_listener.set_frequency(frequency_to_set)
        freq_listener.set_bandwidth(bandwidth_to_set)
        
        freq_listener.set_create_fft_tap(True)
        
        self._radio_source._radio_init()

        self._radio_source.add_frequency_listener(freq_listener)
        

        try:
            self._radio_source.start_frequency_listeners()
        except Exception, excpt:
            msg = ('Failed starting frequency listeners for Class {c},'
                   ' with {e}').format(c=type(self._radio_source), e=excpt)
            assert False, msg


        time.sleep(5)

        try:
            self._radio_source.stop_frequency_listeners()
        except Exception, excpt:
            msg = ('Failed stopping frequency listeners for Class {c},'
                   ' with {e}').format(c=type(self._radio_source), e=excpt)
            assert False, msg

    def test_get_listener_id_list(self):
        """Test retrieving list of listener ids."""

        # need a clean radio source
        rs_id = 'rs2'
        radio_source = diatomite_base_classes.RTL2838R820T2RadioSource(rs_id)

        upper_from_radio_source = radio_source.get_upper_frequency()
        lower_from_radio_source = radio_source.get_lower_frequency()

        # calculate the bandwidth
        bwidth = upper_from_radio_source - lower_from_radio_source

        # define the center frequency midway from upper and lower
        center_freq = (bwidth/2) + lower_from_radio_source
        frequency_to_set = center_freq

        # add a few elements to the freq list and control list
        id_to_set_a = 'test_a'
        id_to_set_b = 'test_b'
        freq_listener_a = diatomite_base_classes.FreqListener(id_to_set_a)
        freq_listener_a.set_frequency(frequency_to_set)
        freq_listener_b = diatomite_base_classes.FreqListener(id_to_set_b)
        freq_listener_b.set_frequency(frequency_to_set)
        
        radio_source._radio_init()

        radio_source.add_frequency_listener(freq_listener_a)
        radio_source.add_frequency_listener(freq_listener_b)

        control_list = []
        control_list.append(id_to_set_a.lower())
        control_list.append(id_to_set_b.lower())

        freq_listener_id_list = radio_source.get_listener_id_list()
        if not isinstance(freq_listener_id_list, list):
            msg = ('FreqListenerList.get_listener_id_list did not return a'
                   ' list')
            assert False, msg

        if control_list != freq_listener_id_list:
            msg = ('FreqListenerList.get_listener_id_list did not return the'
                   ' expected list contents')
            assert False, msg
        
        
    def test_start(self):
        """Test the start method"."""
        
        self._radio_source.start()
        
    def test_stop(self):
        """Test the stop method"."""
        
        self._radio_source.start()

class TestDiatomiteProbe(object):
    """Test DiatomiteProbe class."""

    _diatomite_probe = diatomite_base_classes.DiatomiteProbe()

    def test_add_radio_source(self):
        """Test adding a RadioSource to the DiatomiteProbe's
        RadioSourceList."""

        rs_id = 'test_add_radio_source'
        r_receiver = diatomite_base_classes.RadioSource(rs_id)

        self._diatomite_probe.add_radio_source(r_receiver)

    def test_add_radio_source_wrong_type_fail(self):
        """Test adding an invalid type to the DiatomiteProbe's
        RadioSourceList."""

        r_receiver = ''

        try:
            self._diatomite_probe.add_radio_source(r_receiver)
        except TypeError:
            pass
        
        
class TestAFrequencies(object):
    """Test with a specific frequency"""

    rs_id = 'testRTL2838R820T2RadioSource'
    _radio_source = diatomite_base_classes.RTL2838R820T2RadioSource(rs_id)
    
    listener_freq_a = 97.8e6
    receiver_freq = 97e6
    
    def test_listener_freq_a(self):
        """Test listener_freq_a"""

        # set the bandwidth
        bwidth = 200e3

        # define the center frequency midway from upper and lower
        
        self._radio_source.set_frequency(self.receiver_freq)

        # ensure the bandwidth fits the radio
        bandwidth_to_set = bwidth/2

        # add a new frequency listener
        id_to_set = 'listener_freq_a'
        freq_listener = diatomite_base_classes.FreqListener(id_to_set)
        freq_listener.set_frequency(self.listener_freq_a)
        freq_listener.set_bandwidth(bandwidth_to_set)
        
        self._radio_source._radio_init()

        self._radio_source.add_frequency_listener(freq_listener)
        

        try:
            self._radio_source.start_frequency_listeners()
        except Exception, excpt:
            msg = ('Failed starting frequency listeners for Class {c},'
                   ' with {e}').format(c=type(self._radio_source), e=excpt)
            assert False, msg
                
    

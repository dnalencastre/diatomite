#!/usr/bin/env python2
"""
    Simple monitoring of a preset frequency, to test diatomite_base_classes.
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

import sys
import os
sys.path.append(os.path.abspath('../'))
import diatomite.diatomite_base_classes as diatomite_base_classes
import logging
logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.DEBUG)

class TestFrequencies(object):
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
        freq_listener.set_create_fft_tap(True)
        
        self._radio_source._radio_init()

        self._radio_source.add_frequency_listener(freq_listener)
        

        print 'Listeners:{l}'.format(l=self._radio_source.get_listener_id_list())

        try:
            self._radio_source.start_frequency_listeners()
        except Exception, excpt:
            msg = ('Failed starting frequency listeners for Class {c},'
                   ' with {e}').format(c=type(self._radio_source), e=excpt)


test = TestFrequencies()

test.test_listener_freq_a()
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
import time
sys.path.append(os.path.abspath('../'))
import diatomite.radiosource as radiosource
import diatomite.freqlistener as freqlistener
import logging
logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.DEBUG)

class TestFrequencies(object):
    """Test with a specific frequency"""

    rs_id = 'testRTL2838R820T2RadioSource'
    _radio_source = radiosource.RTL2838R820T2RadioSource(rs_id)
    
#     listener_freq_a = 97.8e6
#     receiver_freq = 97e6
    listener_freq_a = 89.5e6
#     listener_freq_a = 90.8e6
#     listener_freq_a = 90.77e6

#     listener_freq_a = 89.539e6
#     listener_freq_a = 89.615e6
#     receiver_freq = 89.3e6
#     receiver_freq = 89e6
    receiver_freq = 90e6
#     receiver_freq = 89.6e6
#     receiver_freq = 89.5e6
#     receiver_freq = 89.4e6

#     receiver_freq = listener_freq_a

       
#     _radio_source._radio_init()

    def prep_source(self):

        # enable the audio output
        audio_enable = True
        self._radio_source.set_audio_sink_enable(audio_enable)
        
        # enable the spectrum analyzer for the source
        spec_analyzer = True
#         spec_analyzer = False
        self._radio_source.set_spectrum_analyzer_tap_enable(spec_analyzer)

        # define the center frequency midway from upper and lower
        
        self._radio_source.set_frequency(self.receiver_freq) 
    def start_source(self):

        try:
            self._radio_source.start()
        except Exception, excpt:
            msg = ('Failed starting source{c},'
                   ' with {e}').format(c=type(self._radio_source), e=excpt)
            logging.error(msg)
            raise
        
    def do_center_freq_snd_output(self):
        self._radio_source.do_snd_output()
        
        
    def do_listner_snd_output(self):
        self._freq_listener.do_snd_output()
        
    def test_listener_freq_a(self):
        """Test listener_freq_a"""

        # set the bandwidth
#         bwidth = 200e3
        bwidth = 200000



        # ensure the bandwidth fits the radio
        bandwidth_to_set = bwidth/2

        # add a new frequency listener
        id_to_set = 'listener_freq_a'
        self._freq_listener = freqlistener.FreqListener(id_to_set)
        self._freq_listener.set_frequency(self.listener_freq_a)
        self._freq_listener.set_bandwidth(bandwidth_to_set)
#         self._freq_listener.set_bandwidth(bwidth)

#         signal_threshold = -2
        signal_threshold = -65

        self._freq_listener.set_signal_pwr_threshold(signal_threshold)

        self._freq_listener.set_spectrum_analyzer_tap_enable(True)
        
        
        audio_enable = True
        self._freq_listener.set_audio_enable(audio_enable)
        
        tap_path = '.'
        self._radio_source.set_tap_directory(tap_path)
        self._radio_source.add_frequency_listener(self._freq_listener)
        

        print 'Listeners:{l}'.format(l=self._radio_source.get_listener_id_list())

        print 'B---->create fft tap:{v}'.format(v=self._radio_source.get_spectrum_analyzer_tap_enable())



    def stop_source(self):
        try:
            self._radio_source.stop()
        except Exception, excpt:
            msg = ('Failed stopping source {c},'
                   ' with {e}').format(c=type(self._radio_source), e=excpt)
            logging.error(msg)
            raise

    def get_data(self):
        
        rcf = float(self._radio_source.get_center_frequency())/1000/1000
        
        rlf = float(self._radio_source.get_lower_frequency())/1000/1000
        rhf = float(self._radio_source.get_upper_frequency())/1000/1000
        
        lcf = float(self._freq_listener.get_frequency())/1000/1000
        llf = float(self._freq_listener.get_lower_frequency())/1000/1000
        lhf = float(self._freq_listener.get_upper_frequency())/1000/1000
        
        print '-----------------------------------------------'
        print ('Receiver--> center freq: {rcf}, lower freq:{rlf}, '
               'upper freq:{rhf}').format(rcf=rcf, rlf=rlf, rhf=rhf)
        
        print ('Listener--> center freq: {lcf}, lower freq:{llf}, '
               'upper freq:{lhf}').format(lcf=lcf, llf=llf, lhf=lhf)
        print '-----------------------------------------------'
        

if __name__ == "__main__":
    test = TestFrequencies()
    


    test.prep_source()
    
    
    print "Receiver freq:{rf}".format(rf=test.receiver_freq)
    print "Listener freq:{rf}".format(rf=test.listener_freq_a)
    print "Frequency offste:{fo}".format(fo=test.receiver_freq - test.listener_freq_a)
    
    test.test_listener_freq_a()
    test.start_source()

#     test.test_listener_freq_a()

#     test.do_center_freq_snd_output()

    test.get_data()
    
#     test.do_center_freq_snd_output()

    
    time.sleep(15)

#     test.stop_source()

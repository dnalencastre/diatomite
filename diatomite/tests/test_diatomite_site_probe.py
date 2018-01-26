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

import nose
import os
import yaml
import tempfile
from diatomite.diatomite_site_probe import DiaConfParser
from gnuradio.fec.LDPC.Generate_LDPC_matrix_functions import write_alist_file


class TestDiaConfParser:
    """test diatomite_site_probe.DiaConfParser class"""
    
    tconf_file = None
    
    def setUp(self):
        _, self.tconf_file = tempfile.mkstemp(prefix='dia_test_tmp', dir='.')
        
    def tearDown(self):
        os.remove(self.tconf_file)

    def write_yaml_file(self, data, filen):
        """Write a yaml file from a know data set
        data -- dictionary with data to write
        filen -- name for output file"""
        
        # NOTE: files will be written on CWD
        
        with open(filen, 'w') as outfile:
            yaml.dump(data, outfile, default_flow_style=False)

    def test_read_yaml_conf_file(self):
        
        data = {
            'key1': 'val1',
            'key2': 1234,
            'key3': {
                    'k3_1': 'val3_1',
                } 
            }

        self.write_yaml_file(data, self.tconf_file)
        
        dia_conf = DiaConfParser()

        tfileh = open(self.tconf_file, 'r')
        dia_conf.read_yaml_conf_file(tfileh)
        
        print 'Test reading and loading yaml file to python dict'
        assert dia_conf._initial_conf == data
        
        
        
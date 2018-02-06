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
import diatomite.diatomite_site_probe as dia_sp

class TestDiaConfParser:
    """test diatomite_site_probe.DiaConfParser class"""
    
    def __init__(self):
        self.tconf_file = None

        # a known good configuration
        self.good_conf_01 = {
            'sites': {
                'test_site_1': {
                    'location': 'location',
                    'probes': {
                        'test_probe_1': {
                            'RadioSources': {
                                'rs1': {
                                    'frequency': '89e6', 
                                    'type': 'RTL2832U', 
                                    'listeners': {
                                        'ln11': {
                                            'bandwidth': '200000',
                                            'frequency': '89.5e6',
                                            'level_threshold': '-70'
                                            }
                                        }
                                    }
                                },
                            }
                        }
                    }
                }
            }
    
        self.bad_conf_missing_probes_section = {
            'sites': {
                'test_site_1': {
                    'location': 'location',
                    }
                }
            }
        
        self.bad_conf_missing_probes = {
            'sites': {
                'test_site_1': {
                    'probes': {},
                    'location': 'location',
                    }
                }
            }
    
        self.bad_conf_missing_site_conf = {
            'sites': {
                }
            }
    
        self.bad_conf_missing_sites_section = {
            }
    
        self.bad_conf_missing_site_location = {
            'sites': {
                'test_site_1': {
                    'probes': {
                        'test_probe_1': {
                            'RadioSources': {
                                'rs1': {
                                    'freq_analyzer_tap': 'True',
                                    'audio_output': 'True', 
                                    'frequency': '89e6', 
                                    'type': 'RTL2832U', 
                                    'listeners': {
                                        'ln11': {
                                            'freq_analyzer_tap': 'True',
                                            'bandwidth': '200000',
                                            'frequency': '89.5e6',
                                            'modulation': 'FM',
                                            'audio_output': 'True',
                                            'level_threshold': '-70'
                                            }
                                        }
                                    }
                                },
                            'tap_dir_path': 'taps',
                            'logging': {
                                'log_level': 'INFO',
                                'dir_path': 'log'
                                }
                            }
                        }
                    }
                }
            }

        self.bad_conf_missing_radiosource_mandatorys = {
            'sites': {
                'test_site_1': {
                    'location': 'location',
                    'probes': {
                        'test_probe_1': {
                            'RadioSources': {
                                'rs1': {
                                    'freq_analyzer_tap': 'True',
                                    'audio_output': 'True', 
                                    'listeners': {
                                        'ln11': {
                                            'freq_analyzer_tap': 'True',
                                            'bandwidth': '200000',
                                            'frequency': '89.5e6',
                                            'modulation': 'FM',
                                            'audio_output': 'True',
                                            'level_threshold': '-70'
                                            }
                                        }
                                    }
                                },
                            }
                        }
                    }
                }
            }

        # a configuration missing the RadioSources
        self.bad_conf_missing_RadioSources_section = {
            'sites': {
                'test_site_1': {
                    'location': 'location',
                    'probes': {
                        'test_probe_1': {
                            }
                        }
                    }
                }
            }

        self.bad_conf_missing_radiosource = {
            'sites': {
                'test_site_1': {
                    'probes': {
                        'test_probe_1': {
                            'RadioSources': {

                                },
                            }
                        }
                    }
                }
            }

        
        self.radio_source_bad_audio_output_val = {
            'sites': {
                'test_site_1': {
                    'location': 'location',
                    'probes': {
                        'test_probe_1': {
                            'RadioSources': {
                                'rs1': {
                                    'frequency': '89e6', 
                                    'type': 'RTL2832U',
                                    'audio_output': 'BLAGH',
                                    'listeners': {
                                        'ln11': {
                                            'freq_analyzer_tap': 'True',
                                            'bandwidth': '200000',
                                            'frequency': '89.5e6',
                                            'modulation': 'FM',
                                            'audio_output': 'True',
                                            'level_threshold': '-70'
                                            }
                                        }
                                    }
                                },
                            }
                        }
                    }
                }
            }
        
        self.radio_source_bad_freq_analyzer_tap_val = {
            'sites': {
                'test_site_1': {
                    'location': 'location',
                    'probes': {
                        'test_probe_1': {
                            'RadioSources': {
                                'rs1': {
#                                     'frequency': '89e6', 
                                    'type': 'RTL2832U',
                                    'freq_analyzer_tap': 'BLAGH',
                                    'listeners': {
                                        'ln11': {
                                            'freq_analyzer_tap': 'True',
                                            'bandwidth': '200000',
                                            'frequency': '89.5e6',
                                            'modulation': 'FM',
                                            'audio_output': 'True',
                                            'level_threshold': '-70'
                                            }
                                        }
                                    }
                                },
                            }
                        }
                    }
                }
            }
        
        self.bad_conf_missing_listeners_section = {
            'sites': {
                'test_site_1': {
                    'location': 'location',
                    'probes': {
                        'test_probe_1': {
                            'RadioSources': {
                                'rs1': {
                                    'frequency': '89e6', 
                                    'type': 'RTL2832U', 
                                    }
                                },
                            }
                        }
                    }
                }
            }
        
        self.bad_conf_missing_listeners = {
            'sites': {
                'test_site_1': {
                    'location': 'location',
                    'probes': {
                        'test_probe_1': {
                            'RadioSources': {
                                'rs1': {
                                    'frequency': '89e6', 
                                    'type': 'RTL2832U', 
                                    'listeners': {
                                        }
                                    }
                                },
                            }
                        }
                    }
                }
            }
        
        
        self.bad_conf_missing_listener_mandatorys = {
            'sites': {
                'test_site_1': {
                    'location': 'location',
                    'probes': {
                        'test_probe_1': {
                            'RadioSources': {
                                'rs1': {
                                    'frequency': '89e6', 
                                    'type': 'RTL2832U', 
                                    'listeners': {
                                        'ln11': {
                                            }
                                        }
                                    }
                                },
                            }
                        }
                    }
                }
            }
        
        self.listener_bad_audio_output_val = {
            'sites': {
                'test_site_1': {
                    'location': 'location',
                    'probes': {
                        'test_probe_1': {
                            'RadioSources': {
                                'rs1': {
                                    'frequency': '89e6', 
                                    'type': 'RTL2832U', 
                                    'listeners': {
                                        'ln11': {
                                            'bandwidth': '200000',
                                            'frequency': '89.5e6',
                                            'level_threshold': '-70',
                                            'audio_output': 'blaaa'
                                            }
                                        }
                                    }
                                },
                            }
                        }
                    }
                }
            }

        self.listener_bad_freq_analyzer_tap_val = {
            'sites': {
                'test_site_1': {
                    'location': 'location',
                    'probes': {
                        'test_probe_1': {
                            'RadioSources': {
                                'rs1': {
                                    'frequency': '89e6', 
                                    'type': 'RTL2832U', 
                                    'listeners': {
                                        'ln11': {
                                            'bandwidth': '200000',
                                            'frequency': '89.5e6',
                                            'level_threshold': '-70',
                                            'freq_analyzer_tap': 'blaaa'
                                            }
                                        }
                                    }
                                },
                            }
                        }
                    }
                }
            }

        self.listener_bad_modulation_val = {
            'sites': {
                'test_site_1': {
                    'location': 'location',
                    'probes': {
                        'test_probe_1': {
                            'RadioSources': {
                                'rs1': {
                                    'frequency': '89e6', 
                                    'type': 'RTL2832U', 
                                    'listeners': {
                                        'ln11': {
                                            'bandwidth': '200000',
                                            'frequency': '89.5e6',
                                            'level_threshold': '-70',
                                            'modulation': 'blaaa'
                                            }
                                        }
                                    }
                                },
                            }
                        }
                    }
                }
            }

        self.listener_bad_level_threshold_val = {
            'sites': {
                'test_site_1': {
                    'location': 'location',
                    'probes': {
                        'test_probe_1': {
                            'RadioSources': {
                                'rs1': {
                                    'frequency': '89e6', 
                                    'type': 'RTL2832U', 
                                    'listeners': {
                                        'ln11': {
                                            'bandwidth': '200000',
                                            'frequency': '89.5e6',
                                            'level_threshold': 'blaah',
                                            }
                                        }
                                    }
                                },
                            }
                        }
                    }
                }
            }
        
        self.listener_bad_bandwidth_val = {
            'sites': {
                'test_site_1': {
                    'location': 'location',
                    'probes': {
                        'test_probe_1': {
                            'RadioSources': {
                                'rs1': {
                                    'frequency': '89e6', 
                                    'type': 'RTL2832U', 
                                    'listeners': {
                                        'ln11': {
                                            'bandwidth': 'blaah',
                                            'frequency': '89.5e6',
                                            'level_threshold': '-70',
                                            }
                                        }
                                    }
                                },
                            }
                        }
                    }
                }
            }
        
        self.listener_bad_frequency_val = {
            'sites': {
                'test_site_1': {
                    'location': 'location',
                    'probes': {
                        'test_probe_1': {
                            'RadioSources': {
                                'rs1': {
                                    'frequency': '89e6', 
                                    'type': 'RTL2832U', 
                                    'listeners': {
                                        'ln11': {
                                            'bandwidth': '200000',
                                            'frequency': 'blaaah',
                                            'level_threshold': '-70',
                                            }
                                        }
                                    }
                                },
                            }
                        }
                    }
                }
            }
        
    def setUp(self):
        _, self.tconf_file = tempfile.mkstemp(prefix='dia_test_tmp', dir='.')
        
    def tearDown(self):
        os.remove(self.tconf_file)

    def write_yaml_file(self, data, filen):
        """Write a yaml file from a dict
        data -- dictionary with data to write
        filen -- name for output file"""
        
        # NOTE: files will be written on CWD
        
        with open(filen, 'w') as outfile:
            yaml.dump(data, outfile, default_flow_style=False)

    def test_read_yaml_conf_file(self):
        """Test reading a yaml config file generated from a know data set
        and check it again against the data set.
        Should pass if the read data matches the written data."""
        
        data = {
            'key1': 'val1',
            'key2': 1234,
            'key3': {
                    'k3_1': 'val3_1',
                } 
            }

        self.write_yaml_file(data, self.tconf_file)
        
        dia_conf = dia_sp.DiaConfParser()

        tfileh = open(self.tconf_file, 'r')
        dia_conf.read_yaml_conf_file(tfileh)
        
        print 'Test reading and loading yaml file to python dict'
        assert dia_conf._initial_conf == data
    
    def test_parse_good_conf(self):
        """Test to parse a known good configuration"""
        
        dia_conf = dia_sp.DiaConfParser()
        dia_conf._process_config(self.good_conf_01)
        
    def test_parse_good_conf_adding_site_optionals(self):
        """Test to parse a known good configuration is being added optional site fields"""

        dia_conf = dia_sp.DiaConfParser() 
        dia_conf._good_conf = dia_conf._process_config(self.good_conf_01)

        sites = dia_conf.get_config()['sites']
                 
        for s_key in sites:
            this_site = sites[s_key]
            # add the listener id to the data
            this_site['id'] = s_key
             
            if 'address' not in this_site:
                assert False
            if 'type' not in this_site:
                assert False
            if 'longitude' not in this_site:
                assert False
            if 'latitude' not in this_site:
                assert False
            if 'coord_type' not in this_site:
                assert False
    
    def test_current_conf_sample(self):
        """Test the current configuration sample against the current code. If all other tests pass, this must also pass, otherwise sample is wrong !"""
        dia_conf = dia_sp.DiaConfParser()
        dia_conf.read_conf_file('../../dia_conf.yaml')
    
    @nose.tools.raises(dia_sp.DiaConfParserError)
    def test_parse_missing_site_conf(self):
        """Test to parse a configuration missing a site definition.
        An exception should be raised"""
        
        dia_conf = dia_sp.DiaConfParser()
        dia_conf._process_config(self.bad_conf_missing_site_conf)

    @nose.tools.raises(dia_sp.DiaConfParserError)
    def test_parse_missing_sites_section(self):
        """Test to parse a configuration missing sites section.
        An exception should be raised"""
        
        dia_conf = dia_sp.DiaConfParser()
        dia_conf._process_config(self.bad_conf_missing_sites_section)

    @nose.tools.raises(dia_sp.DiaConfParserError)
    def test_parse_missing_site_location_conf(self):
        """Test to parse a configuration missing site location.
        An exception should be raised"""
        
        dia_conf = dia_sp.DiaConfParser()
        dia_conf._process_config(self.bad_conf_missing_site_location)      

    @nose.tools.raises(dia_sp.DiaConfParserError)
    def test_parse_missing_probes_section(self):
        """Test to parse a configuration missing probes section.
        An exception should be raised"""
        
        dia_conf = dia_sp.DiaConfParser()
        dia_conf._process_config(self.bad_conf_missing_probes_section)

    @nose.tools.raises(dia_sp.DiaConfParserError)
    def test_parse_missing_probes(self):
        """Test to parse a configuration missing probes configuration (But with a "probes" section).
        An exception should be raised"""
        
        dia_conf = dia_sp.DiaConfParser()
        dia_conf._process_config(self.bad_conf_missing_probes)

    def test_parse_good_conf_adding_probe_optionals(self):
        """Test to parse a known good configuration is being added optional probe fields"""
        
        dia_conf = dia_sp.DiaConfParser() 
        dia_conf._good_conf = dia_conf._process_config(self.good_conf_01)

        probes_conf = dia_conf.get_config()['sites']['test_site_1']['probes']
                 
        for p_key in probes_conf:
            this_probe = probes_conf[p_key]
            # add the listener id to the data
             
            if 'tap_dir_path' not in this_probe:
                assert False
            if 'logging' not in this_probe:
                assert False
                
            logging_conf = this_probe['logging']
            
            if 'log_level' not in logging_conf:
                assert False
            if 'dir_path' not in logging_conf:
                assert False
                
    @nose.tools.raises(dia_sp.DiaConfParserError)
    def test_parse_missing_RadioSources_section(self):
        """Test to parse a configuration missing RadioSources section.
        An exception should be raised"""
        
        dia_conf = dia_sp.DiaConfParser()
        dia_conf._process_config(self.bad_conf_missing_RadioSources_section)

    @nose.tools.raises(dia_sp.DiaConfParserError)
    def test_parse_missing_radio_sources(self):
        """Test to parse a configuration missing radio sources configuration (But with a "RadioSources" section).
        An exception should be raised"""
        
        dia_conf = dia_sp.DiaConfParser()
        dia_conf._process_config(self.bad_conf_missing_radiosource)

    @nose.tools.raises(dia_sp.DiaConfParserError)
    def test_parse_missing_radio_source_missing_radio_source_mandatorys(self):
        """Test to parse a configuration missing radio sources mandatory fields.
        An exception should be raised"""
        
        dia_conf = dia_sp.DiaConfParser()
        dia_conf._process_config(self.bad_conf_missing_radiosource_mandatorys)

    def test_parse_good_conf_adding_radio_source_optionals(self):
        """Test to parse a known good configuration is being added optional radio source fields"""
        
        dia_conf = dia_sp.DiaConfParser() 
        dia_conf._good_conf = dia_conf._process_config(self.good_conf_01)

        radiosources_conf = dia_conf.get_config()['sites']['test_site_1']['probes']['test_probe_1']['RadioSources']
                 
        for rs_key in radiosources_conf:
            this_rs = radiosources_conf[rs_key]
            # add the listener id to the data
             
            if 'audio_output' not in this_rs:
                assert False
            if 'freq_analyzer_tap' not in this_rs:
                assert False

    def test_radio_source_valid_values(self):
        """Test if radio source values are sane.
        Tested with bad value for radio source audio output and freq_analyzer_tap"""
        
        dia_conf = dia_sp.DiaConfParser()
        
        for conf in [self.radio_source_bad_audio_output_val,
                     self.radio_source_bad_freq_analyzer_tap_val]:
            
            try:
                dia_conf._good_conf = dia_conf._process_config(conf)
            except dia_sp.DiaConfParserError:                
                assert True
            else:
                assert False

    @nose.tools.raises(dia_sp.DiaConfParserError)
    def test_parse_missing_listeners_section(self):
        """Test to parse a configuration missing listeners section.
        An exception should be raised"""
        
        dia_conf = dia_sp.DiaConfParser()
        dia_conf._process_config(self.bad_conf_missing_listeners_section)

    @nose.tools.raises(dia_sp.DiaConfParserError)
    def test_parse_missing_listeners(self):
        """Test to parse a configuration missing listener configuration (But with a "listeners" section).
        An exception should be raised"""
        
        dia_conf = dia_sp.DiaConfParser()
        dia_conf._process_config(self.bad_conf_missing_listeners)
        
    def test_parse_good_conf_adding_listener_optionals(self):
        """Test to parse a known good configuration is being added optional listener fields"""
        
        dia_conf = dia_sp.DiaConfParser() 
        dia_conf._good_conf = dia_conf._process_config(self.good_conf_01)

        listeners_conf = dia_conf.get_config()['sites']['test_site_1']['probes']['test_probe_1']['RadioSources']['rs1']['listeners']
                 
        for l_key in listeners_conf:
            this_l = listeners_conf[l_key]
            # add the listener id to the data
             
            if 'modulation' not in this_l:
                assert False
            if 'audio_output' not in this_l:
                assert False
            if 'freq_analyzer_tap' not in this_l:
                assert False           

    @nose.tools.raises(dia_sp.DiaConfParserError)
    def test_parse_missing_listener_missing_radio_source_mandatorys(self):
        """Test to parse a configuration missing listener mandatory fields.
        An exception should be raised"""
         
        dia_conf = dia_sp.DiaConfParser()
        dia_conf._process_config(self.bad_conf_missing_listener_mandatorys)
        
    def test_listener_valid_values(self):
        """Test if listener values are sane.
        Tested with bad values for:
            - audio_output
            - freq_analyzer_tap
            - modulation
            - level_threshold
            - bandwidth
            - frequency"""

        dia_conf = dia_sp.DiaConfParser()
        for conf in [        
            self.listener_bad_audio_output_val,
            self.listener_bad_freq_analyzer_tap_val,
            self.listener_bad_modulation_val,
            self.listener_bad_level_threshold_val,
            self.listener_bad_bandwidth_val,
            self.listener_bad_frequency_val
            ]:
            
            try:
                dia_conf._good_conf = dia_conf._process_config(conf)
            except dia_sp.DiaConfParserError as e:
                assert True
            else:
                assert False


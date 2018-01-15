#!/usr/bin/env python2
"""
    diatomite - Api service classes
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

import logging
from multiprocessing import Process, Queue
from multiprocessing import managers as mp_managers
import json
import bottle


class DiaApiSvcError(Exception):
    """Raised when the api service encounters an error."""
    pass


class ApiSvc(object):
    """Provide RESTFULL API services."""

    _subprocess_in = Queue()
    _subprocess_out = None
    _api_srv_subprocess = None

    _data = {}

    # Id of this component
    _id = 'API_SRV'

    def __init__(self, probe_conf, site_conf, in_queue, out_queue):
        """Initialize the api service object.
        probe_conf -- a dictionary with a valid configuration for
                this probe
        site_conf -- a dictionary with the site configuration
        in_queue -- queue to be used as input for this radio source
        out_queue -- queue to be used as output for radio sources"""

        if (probe_conf is not None and site_conf is not None
                and in_queue is not None and out_queue is not None):
            self.configure(probe_conf, site_conf, in_queue, out_queue)
        else:
            msg = ('Incomplete initialization. probe conf:{pc}, site_conf:{sc}'
                   ' output queue:{q}').format(pc=probe_conf, sc=site_conf,
                                               q=out_queue)
            raise DiaApiSvcError(msg)

    def configure(self, probe_conf, site_conf, in_queue, out_queue):
        """Configure the api service object.
        probe_conf -- a dictionary with a valid configuration for
                this probe
        site_conf -- a dictionary with the full configuration received
                by diatomite
        in_queue -- queue to be used as input for this radio source
        out_queue -- queue to be used as output for radio sources"""

        # TODO: do the configuration !!
        self._data = site_conf

    def set_ouptut_queue(self, queue):
        """Set the PAI service output queue
        queue -- the output queue (multiprocessing.Queue)"""

        type_queue = type(queue)

        # check if we were given an object of the right type
        if not isinstance(queue, mp_managers.BaseProxy):

            msg = ('Queue must be a queue of multiprocessing.managers.BaseProxy,'
                   ' was {tgtb}').format(tgtb=type_queue)
            raise TypeError(msg)

        self._subprocess_out = queue
        msg = 'Top block set.'
        logging.debug(msg)

    def get_output_pipe(self):
        """Return the output pipe for the listener."""

        return self._subprocess_out

    def get_id(self):
        """Returns the radio source's id."""
        return self._id

    def send_data(self, data):
        """Sends data output to the output pipe.
        data -- data to send"""

        # prepend with the source id
        out_data = self.get_id() + ':' + data
        self._subprocess_out.put(out_data)
        msg = 'sending data to parent:{d}'.format(d=out_data)
        logging.debug(msg)

    def start(self):
        """Start the api server.
        Returns the handle to the subprocess."""

        # setup and start the subprocess for this source

        self._api_srv_subprocess = Process(target=self._run_api_srv_subprocess,
                                           args=(self._subprocess_out,
                                                 self._subprocess_in))
        try:
            self._api_srv_subprocess.start()
        except Exception, exc:
            msg = ('Failed starting the source subprocesses with:'
                   ' {m}').format(m=str(exc))
            logging.debug(msg)
            raise

    def _run_api_srv_subprocess(self, input_conn, output_conn):
        """start the subprocess the api server.
        input_conn - input pipe
        output_conn - output pipe"""

        # TODO: Add working code
        me = self

        # start flask
        api = DiaApi('DiatomiteAPI', self._data)
        api.run(host='localhost', port=8000)

        msg = 'API server exiting.'.format(id=self.get_id())
        logging.debug(msg)
        output_conn.send(msg)

    def get_site(self):
        """Get site data"""
        return self._data


class DiaApi(bottle.Bottle):
    """Class to provide an API server for Diatomite"""

    def __init__(self, name, data):

        super(DiaApi, self).__init__()
        self.name = name
        self._set_routes()
        self._data = data

    def _set_routes(self):
        """Set routes for the api"""
        self.route('/', callback=self.get_index, method='GET')

    def get_index(self):
        """Get index page"""
        bottle.response.headers['Content-Type'] = 'application/json'
        return json.dumps(self._data)

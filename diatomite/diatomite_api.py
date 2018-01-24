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
from multiprocessing import queues as mp_queues
import threading
import json
import bottle
import diatomite_aux as dia_aux


class DiaApiSvcError(Exception):
    """Raised when the api service encounters an error."""
    pass


class ApiSvc(object):
    """Provide RESTFULL API services."""

    def __init__(self, probe_conf, site_conf, in_queue, out_queue):
        """Initialize the api service object.
        probe_conf -- a dictionary with a valid configuration for
                this probe
        site_conf -- a dictionary with the site configuration
        in_queue -- queue to be used as input for this radio source
        out_queue -- queue to be used as output for radio sources"""

        self._subprocess_in = Queue()
        self._subprocess_out = None
        self._api_srv_subprocess = None
        self._probe_stop = threading.Event()
        self._monitor_input_queue_thread = None

        self._data = {}

        # Id of this component
        self._id = 'API_SRV'

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

        self._data = site_conf

        self.set_ouptut_queue(out_queue)
        self.set_input_queue(in_queue)

    def set_ouptut_queue(self, queue):
        """Set the API service output queue
        queue -- the output queue (multiprocessing.Queue)"""

        type_queue = type(queue)

        # check if we were given an object of the right type
        if not isinstance(queue, mp_queues.Queue):

            msg = ('Queue must be a queue of multiprocessing.queues.Queue,'
                   ' was {tgtb}').format(tgtb=type_queue)
            raise TypeError(msg)

        self._subprocess_out = queue
        msg = 'Top block set.'
        logging.debug(msg)

    def set_input_queue(self, queue):
        """Set the API service input queue
        queue -- the input queue (multiprocessing.Queue)"""

        type_queue = type(queue)

        # check if we were given an object of the right type
        if not isinstance(queue, mp_queues.Queue):

            msg = ('Queue must be a queue of multiprocessing.queues.Queue,'
                   ' was {tgtb}').format(tgtb=type_queue)
            raise TypeError(msg)

        self._subprocess_in = queue
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

    def _monitor_input_queue(self, stop_event):
        """Monitor input queue"""
        stop = False
        while not stop_event.is_set():
            in_data = self._subprocess_in.get()

            # extract commands from in_data
            msg_type = in_data.get_msg_type()
            if msg_type in (dia_aux.DiaMsgType.LNR_SIG_STATE,
                            dia_aux.DiaMsgType.LNR_SIG_STATUS_CHANGE):
                self._process_sig_state_update(in_data)
            elif msg_type == dia_aux.DiaMsgType.RCV_SYS_STATE_CHANGE:
                self._process_rcv_state_update(in_data)
            elif msg_type == dia_aux.DiaMsgType.LNR_SYS_STATE_CHANGE:
                self._process_lnr_state_update(in_data)

            # TODO: manage stop messages
#             input_cmd = ''
#             if input_cmd == 'STOP':
#                 stop = True

            msg = 'in_data {d}, type {t}'.format(d=in_data, t=type(in_data))
            logging.debug(msg)

            stop_event.wait(0.1)

    def _process_sig_state_update(self, in_data):
        """process signal state update messages
        in_data -- a DiaSiteMsg object"""

        # check if we were given an object of the right type
        if not isinstance(in_data, dia_aux.DiaSiteMsg):
            msg = ('in_data must be a DiaSiteMsg,'
                   ' was {t}').format(t=type(in_data))
            raise TypeError(msg)

        # extract the payload
        payload = in_data.get_payload()
        site_id = in_data.get_id()

        # re-pack payload into a probe message
        dia_probe_msg = dia_aux.DiaProbeMsg()
        dia_probe_msg.set_json(payload)

        dia_probe_msg_payload = dia_probe_msg.get_payload()
        probe_id = dia_probe_msg.get_id()

        # re-pack payload into a receiver message
        dia_receiver_msg = dia_aux.DiaRadioReceiverMsg()
        dia_receiver_msg.set_json(dia_probe_msg_payload)

        dia_receiver_msg_payload = dia_receiver_msg.get_payload()
        rcvr_id = dia_receiver_msg.get_id()

        # re-pack payload into a listener message
        dia_lnr_msg = dia_aux.DiaListenerMsg()
        dia_lnr_msg.set_json(dia_receiver_msg_payload)

        dia_lnr_msg_payload = dia_lnr_msg.get_payload()
        lnr_id = dia_lnr_msg.get_id()

        self._update_sig_state(site_id, probe_id, rcvr_id, lnr_id,
                               dia_lnr_msg_payload)

    def _process_rcv_state_update(self, in_data):
        """process receivar sys state update messages
        in_data -- a DiaSiteMsg object"""

        # check if we were given an object of the right type
        if not isinstance(in_data, dia_aux.DiaSiteMsg):
            msg = ('in_data must be a DiaSiteMsg,'
                   ' was {t}').format(t=type(in_data))
            raise TypeError(msg)
        # TODO: finish receiver state update

    def _process_lnr_state_update(self, in_data):
        """process listener sys state update messages
        in_data -- a DiaSiteMsg object"""

        # check if we were given an object of the right type
        if not isinstance(in_data, dia_aux.DiaSiteMsg):
            msg = ('in_data must be a DiaSiteMsg,'
                   ' was {t}').format(t=type(in_data))
            raise TypeError(msg)
        # TODO: finish listener state update

    def _update_sig_state(self, site_id, probe_id, rsrc_id, lnr_id, data):
        """Update signal state info from a DiaSiteMsg
        site_id -- site id for the listener that will be updated
        probe_id -- probe id for the listener that will be updated
        rsrc_id -- receiver id for the listener that will be updated
        lnr_id -- id for the listener that will be updated
        data -- the signal data, either a json or DiaSigState"""

        # transform payload from json to

        # check if data is already a DiaSigState
        if not isinstance(data, dia_aux.DiaSigState):
            # transform the json to a a DiaSigState
            sig_state = dia_aux.DiaSigState()
            sig_state.set_json(data)
        else:
            sig_state = data

        site_data = self._data[site_id]

        probe_data = site_data['probes'][probe_id]

        radio_source = probe_data['RadioSources'][rsrc_id]

        listener = radio_source['listeners'][lnr_id]

        listener['signal_state'] = sig_state


    def _run_api_srv_subprocess(self, input_conn, output_conn):
        """start the subprocess the api server.
        input_conn - input pipe
        output_conn - output pipe"""

        # launch thread to monitor and act on queue messages
        self._monitor_input_queue_thread = threading.Thread(target=self._monitor_input_queue,
                                                            name=self.get_id(),
                                                            args=(self._probe_stop,))
        self._monitor_input_queue_thread.daemon = True
        self._monitor_input_queue_thread.start()

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
        self.route('/sites', callback=self.get_sites, method='GET')
        self.route('/sites/<site>', callback=self.get_site, method='GET')
        self.route('/sites/<site>/probes', callback=self.get_probes,
                   method='GET')
        self.route('/sites/<site>/probes/<probe>', callback=self.get_probe,
                   method='GET')
        self.route('/sites/<site>/probes/<probe>/RadioSources',
                   callback=self.get_sources, method='GET')
        self.route('/sites/<site>/probes/<probe>/radiosources',
                   callback=self.get_sources, method='GET')
        self.route('/sites/<site>/probes/<probe>/RadioSources/<source>',
                   callback=self.get_source, method='GET')
        self.route('/sites/<site>/probes/<probe>/radiosources/<source>',
                   callback=self.get_source, method='GET')
        self.route('/sites/<site>/probes/<probe>/RadioSources/<source>/listeners',
                   callback=self.get_listeners, method='GET')
        self.route('/sites/<site>/probes/<probe>/radiosources/<source>/listeners',
                   callback=self.get_listeners, method='GET')
        self.route('/sites/<site>/probes/<probe>/RadioSources/<source>/listeners/<listener>',
                   callback=self.get_listener, method='GET')
        self.route('/sites/<site>/probes/<probe>/radiosources/<source>/listeners/<listener>',
                   callback=self.get_listener, method='GET')
        self.route('/sites/<site>/probes/<probe>/RadioSources/<source>/listeners/<listener>/current_signal_state',
                   callback=self.get_listener_current_signal_state, method='GET')
        self.route('/sites/<site>/probes/<probe>/radiosources/<source>/listeners/<listener>/current_signal_state',
                   callback=self.get_listener_current_signal_state, method='GET')


    def get_sites(self):
        """Get all sites know to this probe"""
        bottle.response.headers['Content-Type'] = 'application/json'
        return json.dumps(self._data, cls=dia_aux.DataDumpEnconder)

    def get_site(self, site):
        """Get a site,
        site -- site id"""
        bottle.response.headers['Content-Type'] = 'application/json'

        if site not in self._data:
            bottle.response.status = 400
            return

        return json.dumps(self._data[site], cls=dia_aux.DataDumpEnconder)


    def get_probes(self, site):
        """GEt all probes from a site
        site -- site id"""
        bottle.response.headers['Content-Type'] = 'application/json'

        if site not in self._data:
            bottle.response.status = 400
            return

        return json.dumps(self._data[site]['probes'],
                          cls=dia_aux.DataDumpEnconder)

    def get_probe(self, site, probe):
        """GEt a probe from a site
        site -- site id
        probe -- probe id"""
        bottle.response.headers['Content-Type'] = 'application/json'

        if site not in self._data:
            bottle.response.status = 400
            return

        if probe not in self._data[site]['probes']:
            bottle.response.status = 400
            return

        return json.dumps(self._data[site]['probes'][probe],
                          cls=dia_aux.DataDumpEnconder)

    def get_sources(self, site, probe):
        """Get all sources from a probe
        site -- site id
        probe -- probe id"""
        bottle.response.headers['Content-Type'] = 'application/json'

        if site not in self._data:
            bottle.response.status = 400
            return

        if probe not in self._data[site]['probes']:
            bottle.response.status = 400
            return

        this_probe = self._data[site]['probes'][probe]

        return json.dumps(this_probe['RadioSources'],
                          cls=dia_aux.DataDumpEnconder)

    def get_source(self, site, probe, source):
        """Get a source from a probe
        site -- site id
        probe -- probe id
        source -- source id"""
        bottle.response.headers['Content-Type'] = 'application/json'

        if site not in self._data:
            bottle.response.status = 400
            return

        if probe not in self._data[site]['probes']:
            bottle.response.status = 400
            return

        this_probe = self._data[site]['probes'][probe]

        return json.dumps(this_probe['RadioSources'][source],
                          cls=dia_aux.DataDumpEnconder)

    def get_listeners(self, site, probe, source):
        """Get all listeners from a source
        site -- site id
        probe -- probe id
        source -- source id"""
        bottle.response.headers['Content-Type'] = 'application/json'

        if site not in self._data:
            bottle.response.status = 400
            return

        if probe not in self._data[site]['probes']:
            bottle.response.status = 400
            return

        this_probe = self._data[site]['probes'][probe]
        this_source = this_probe['RadioSources'][source]

        return json.dumps(this_source['listeners'],
                          cls=dia_aux.DataDumpEnconder)

    def get_listener(self, site, probe, source, listener):
        """Get a listener from a source
        site -- site id
        probe -- probe id
        source -- source id
        listener -- listener id"""
        bottle.response.headers['Content-Type'] = 'application/json'

        if site not in self._data:
            bottle.response.status = 400
            return

        if probe not in self._data[site]['probes']:
            bottle.response.status = 400
            return

        this_probe = self._data[site]['probes'][probe]
        this_source = this_probe['RadioSources'][source]

        return json.dumps(this_source['listeners'][listener],
                          cls=dia_aux.DataDumpEnconder)

    def get_listener_current_signal_state(self, site, probe, source, listener):
        """Get a listener's current state
        site -- site id
        probe -- probe id
        source -- source id
        listener -- listener id"""
        bottle.response.headers['Content-Type'] = 'application/json'

        if site not in self._data:
            bottle.response.status = 400
            return

        if probe not in self._data[site]['probes']:
            bottle.response.status = 400
            return

        this_probe = self._data[site]['probes'][probe]
        this_source = this_probe['RadioSources'][source]

        return json.dumps(this_source['listeners'][listener]['signal_state']['current'],
                          cls=dia_aux.DataDumpEnconder)

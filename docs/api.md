# Diatomite API

The current api is read-only.

The current operations are GETs for:

- http://localhost:8000/diatomite/sites - all sites configured on the probe (on the probe there should only be one site)
- http://localhost:8000/diatomite/sites/<site_id> - a specific site
- http://localhost:8000/diatomite/sites/<site_id>/probes - the list of probes configured
- http://localhost:8000/diatomite/sites/<site_id>/probes/<probe_id> - a specific probe
- http://localhost:8000/diatomite/sites/<site_id>/probes/<probe_id>/RadioSources - the list of radio sources for a site
- http://localhost:8000/diatomite/sites/<site_id>/probes/<probe_id>/RadioSources/<source_id> - a specific radio source
- http://localhost:8000/diatomite/sites/<site_id>/probes/<probe_id>/RadioSources/<source_id>/listeners - the list of listeners for a radio source
- http://localhost:8000/diatomite/sites/<site_id>/probes/<probe_id>/RadioSources/<source_id>/listeners/<listener_id> - a specific listener id
- http://localhost:8000/diatomite/sites/<site_id>/probes/<probe_id>/RadioSources/<source_id>/listeners/<listener_id>current_signal_state - the latest signal state information for a listener.

At this point results for invalid requests are closed connections without any results.

For typical results of http://localhost:8000/diatomite/sites, see the sample file docs/output_sample_01.json

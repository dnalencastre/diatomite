# Architecture for the Diatomite system
## A (brief) description of the Diatomite System

The Diatomite system is composed of several main components:
1. a diatomite site - where the user may describe the location where it is installed.
2. a diatomite probe - which represents an instance of the software.
3. a radio source - which represents one instance of radio hardware. Each probe may have several of these.
4. a listener - which represents a frequency to be monitored. Each radio source may have several of these.
5. API server - which is responsible for presenting the state of the system to the world.

Diatomite makes heavy use of GNU radio, specifically on the 'listener' and 'radio source' components.

Regarding the 'Diatomite site', it is an abstraction, of a physical entity. A user may want more than one probe on a given location and this is a clean way of identifying one of those locations. A given 'Diatomite probe' will not be aware of any other probes on the same 'Diatomite site'.

The 'Diatomite probe' handles software configuration and initialization of the 'radio sources' and the API server.
It also passes reports obtained from the 'listeners' and 'Radio Sources' to the API server.

The 'Radio source' is the interface into the SDR hardware, and handles it's configuration, and also the configuration of it's dependent listeners.
The 'Radio Source' is also responsible of passing reports from 'listeners' to the 'Diatomite Site'
A 'Radio source' may be configured to allow sound output and and RF analyser output to aid in configuration. In this case the sound output is to allow 'listeners' to output sound for their signal.;

The 'listener', tunes into a frequency, does the necessary filtering and evaluates the conditions of the signal,
and reports it to the 'Radio Source'.
It may also be configured to allow sound output and and RF analyser output to aid in configuration.

The 'API server' keeps a representation of the state of the system internally, receives updates from the 'Diatomite probe' and allows access to that data via the API it exposes on it's API server.

All of this is done by spawning several processes.

1. An initial a Site/Probe process, where initial configurations are done, and which spawns the other processes.
2. one subprocess per 'Radio Source'
3. one API server.

This is done in order to minimize contention due to the GIL, as each 'Radio Source' and 'Listener' will have several threads running in parallel.

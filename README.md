# Diatomite
## Software to monitor radio frequency activity

This is software to enable a user to monitor frequency activity.
The use case is where a broadcaster wants to check if a given broadcast is being received on a certain location, so that actions can be taken if the broadcast is not being received, all of this using readily available components (General purpose computers, operating systems, inexpensive radio receivers).

This was done from a 'IT Infrastructure Admin' perspective and not from a Radio frequency engineer perspective.

Diatomite makes heavy use of GNU radio!!! https://www.gnuradio.org/

The software monitors one or more frequencies, using one or more SDR radio receivers, and reports signal statuses through a RESTfull api.
The signals status is determined against a pre-determind level for each frequency set in the configuration file. There is no auto sensing.

Currently only RealTek 2838 SDR dongles are supported, but this should be easy to extend.

Also provided is a tool (tools/tap_graph.py) to monitor radio frequency analyser outputs of Diatomite on a character console. This was deliberately made as a text console utility to enable the use on remote equipment via ssh.

The software should be considered early ALPHA, and is working end-to-end, reading configurations, monitoring frequencies and reporting on the RESTfull API server.

Signal detection is done the following way:
1. a frequency is monitored
2. a fast Fourrier transform is taken every 10th of a second.
3. 10% of the central portion of the fast Fourrier transform is taken and averaged.
4. The last average is added to a list of averages with the last 10 measurements.
5. An average of these last 10 measurements is taken and check against a pre-configured level threshold. If it is above the threshold, the signal is deemed 'Present', otherwise it is deemed 'Absent'

CAVEAT EMPTOR.
Use at own risk.

Major known issues.
API server relies on Bottles' internal web server, which is not meant for production, and may not allow more than one concurrent connection.
Message passing serialization is a bit awkward.

Next steps:
1. Create test scripts, with as close to full code coverage as possible.
2. Reporting of component status through the API
3. Improve shutdown process
4. Improve rf analyser tap naming
5. add replay capability to tap_grap.py
6. ..... many other stuff

Hope this will be of use.
Duarte Alencastre

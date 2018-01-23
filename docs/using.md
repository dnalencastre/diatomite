# Using Diatomite

## configuring
Configuration is done via a yaml file.
See the provided dia_conf.yaml and also docs/config_files.txt.

## configuring listeners
Do an initial configuration, ensuring that:
1. the probe "tap_dir_path" is configured with a valid and writeable path.
2. the radio source "freq_analyzer_tap" is set to "TRUE"
3. the listener "freq_analyzer_tap" is set to "TRUE"
4. Optionally, set both the radio source and listener "audio_output" to "TRUE", so that you are able to check if the correct broadcast is being tuned.
5. start diatomite.
7. monitor the listener tap with the tap_graph.py tool, determine a level that is high enough from the noise floor that it be reached by the noise floor.
8. add this level to the listener's 'level_threshold' (keep in mind it must be a negative number)
9. set radio source "freq_analyzer_tap"to "FALSE"
10. set listener "freq_analyzer_tap"to "FALSE"
11. ensure both the radio source and listener "audio_output" are set to "FALSE"
12. restart diatomite
13. check the API

## Starting diatomite
Diatomite can be started with
python diatomite_srv.py -f <path_to_config_file>

## Radio Frequency analyser taps
Radio Frequency analyser taps can be accessed on the tap directory stated on the configuration, via the tools/tap_graph.py utility.
tools/tap_graph.py -f taps/<listener_or_source_name>.tap

Radio frequency taps should be only used for set up as they will use computing resources.

## Sound output
Listeners can be configured to output sound, provided:
1. the Listener's source is also configured to output sound.
2. sound output hardware exists and is compatible with GNU radio

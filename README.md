# Parse Earthworm PZ files into obspy Inventory object

* Because of the way PZ files are, there is only one response stage

## Assumptions:
* Network codes and stations codes are unique
* Poles and Zeros frequencies are in radian (easy to fix)
* Input units are M/S

## To be added:
* Argument parsing
* Get missing values from command line
* Option to throw exception or not
* PZtoStationXML

## To be fixed:
* Normalizing frequencies are assumed to be 1 Hz.
* Maybe try to use the instrument info to gather decimation stage info :/


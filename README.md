# Parse Earthworm PZ files into obspy Inventory object
ver 0.2:
* Reads all '*PZ' files in the directory into an obspy inventory object
* Produces stationXML compatible with dataless SEED

## Assumptions
* Network codes and stations codes are unique
* Poles and Zeros frequencies are in radian (easy to fix)
* Input units are M/S

## To be added
* Argument parsing
* Get missing values from command line
* Option to throw exception or not
* PZtoStationXML

## To be fixed
* Normalizing frequencies are assumed to be 1 Hz.
* Maybe try to use the instrument info to gather decimation stage info :/


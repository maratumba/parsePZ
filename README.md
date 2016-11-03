# Parse Earthworm PZ files into obspy Inventory object

* Because of the way PZ files are, there is only one response stage

## Assumptions:
* network codes and stations codes are unique

## To be fixed:
* Normalizing frequencies are assumed to be 1 Hz.
* Maybe try to use the instrument info to gather decimation stage info :/


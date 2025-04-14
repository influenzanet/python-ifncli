# Participants commands

## participants:flags:stats

Build statistics of participants' flags

Parameters:
 - `--study`: Study key to fetch participants flags from

Optional parameters:
 - `--page-size`: Number of participants to download on each iteration (default:100)
 - `--no-print`: Disable print of results
 - `--output`: Path of a json file to export the results
 - `--stats`: string definition of stats to build (see stats)
 - `--stats-file`: yaml definition of stats file (see stats)

Statistics:
Several kind of statistics can be built on participant flags:

General (no parameter):
- `counts`: Build a frequency of participants flags keys (count occurence of each flag name)

Fields based (need to specify the field name)
- `summary` : Build a quantitative summary of flag values, 
- `category`: Build a qualitative stats as frequency count for each flag value occurence 

`--stats` parameter accept string format as a list of statistics to build, separated by a comma.
Field based stats must be specified using the syntax : <statistic>:<field>

Examples:
 - "counts": Just build the flags naeme frequency (default if nothing specified)
 - "category:minor" : Build categorical statistic on values of the flag 'minor'
 - "counts,category:minor" : Build flags frequency and the categorical on value of the flag 'minor'
 - "summary:counter": Build a qualitative summary of values of the flag named 'counter'

`--stats-file` accepts a yaml file to define statistics request, it must contains a list of statistic specification.
Each entry can be either the string definition (e.g. "summary:counter") or an object {"type":, "field":}

Example:
```yaml
# Flag name frequency
- "counts"
- "summary:counter"
# Using the object based definition. An optional "name" field can be used to provide results name in case of collision
# By default name is {type}_{field} and "counts" for flags frequency
- 
  type: "category"
  field: "minor"
```

Output:

- Flags counts returns a named list (dict) with flag name and count of occurence of this name in flags as value
- category returns a named list, with flag value as key, and count of this value occurences in flags as value
- summary retuns a named list with metrics : 'n' (count with values), 'mean', 'variance', 'min', 'max', invalid (value not parseable as float), nan: 

## participants:flags:sync

This command allow to synchronize flags of participants with a file describing the target values for each participants.

Arguments:

  -  `--study` : the study key
  -  `--file` : path to the json file with flags values for each participants

Optional arguments:

  - `--dry-run` : Will only show what should be updated but do not update flags
  - `--page-size` : Count of participants to load in each step, default=500

The json file should be contains an object (dictionary in python) with participant id as key,
the value must be another object with flag key and value to sync.

```json
{
  "my-participant-id": {
    "flag1":"0"
  }
}
```

The example will synchronize, the flag named 'flag1' set to value '0' for the participant 'my-participant-id'.
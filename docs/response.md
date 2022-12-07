# Response commands

Response commands manage the response data

## response:download

Base command to download survey response. This command download response for a single survey on a defined period



## response:schema

Download schema of the response (survey definition as a flat list for each survey version)

## response:export-bulk

response export-bulk is a more advanced export command, to extract response for a survey in an automatic way.
It will export response data incrementaly using a file per week. 
It produces a catalog file, registering the name and the time range for each exported file.

If you run several times the command during the current week, the data will be updated.

The download parameters are defined in a 'profile' yaml file 

Parameters:
    - --profile path to the yaml file with the profile to export
    - --output path of the folder to put the export into (data will be in subdirectory with survey_key as name)
    - --study name of the study to use

The export profile is here :

```yaml
survey_key: 'intake'
survey_info: # If survey_info is provided then survey structure will be exported too (like response:schema)
  lang: fr # Language for labels to be exported
  format: json # Export format for the survey infos data
start_time: '2022-11-28T00:00:00' # Start download on this time
format: wide
short_keys: false
key_separator: '|' # How to separated item key and response key.
meta: # Complement information to extract, if not present each will be inferred to false
  position: true
  init_times: true
  display_tile: true
  response_time: true
```
The data are downloaded as file by week in a a folder with the name of the survey key.

The from the provided output folder (in --output) the files will be in a subfolder with the name of the survey key
The same output folder can be used for several survey, each one will have a directory with its key

In the output folder will be:
    - csv file (one for each weekly batch) : response data
    - catalog.json containing list of csv file with time range
    - survey_infos.json : data about the survey versions

## response:export-plan

Response plan is an upper level of response:export-bulk, it's the same a calling export-bulk for each survey in one command.
This list of survey to export is defined in a yaml file (the "plan"). For each survey the path for the yaml file containing the export parameters is expected
(so you can reuse export profiles already defined). It's just a way to regroup exports in one command.

2 parameters:

- plan : path to a yaml file describing all the surveys to export
- output : the folder where to put the files (each survey export will be in a separated subfolder named by the survey keys)
  
plan file:

```yaml
study: grippenet # Name of the study where the survey lives
profiles: # Name of the profile files of each survey to export (relative path to the yaml plan file, simplest : in the same directory)
  - intake.yaml
  - weekly.yaml
  - vaccination.yaml
```

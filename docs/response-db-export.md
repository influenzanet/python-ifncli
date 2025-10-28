# Export Response to a database

This new export method allows to download raw response data from the platform and save it in a sqlite database (single file database without the need of installing a server).

Advantages:

- Single file database can contains many tables, a single file can be used to download data for all the surveys
- The exporter uses pagination to download data, limiting the number of response loaded at each step, reducing the risk of memory problem on the server side.
- The database also contains survey info (json description of the survey in a simpler form)


## Export Commands

The exports provides 2 commands

- `response:db:export`
- `response:db:export-plan`

Both commands needs a "profile" yaml file to describe the configuration of the export. Both command can export several surveys from one profile (contrary to the file based command like `response:export-plan`). `response:db:export-plan` is using a profile file for each survey so can be used if each surveys need separated parameters. If only survey key change, then you can simply use a single profile file for all.


### Profile file

The profile file, is a yaml file describing parameters. The format is the same as previous export commands (i.e. `response:export-*`) with some deprecated (ignored) parameters and extensions.

```yaml
# survey_key and surveys are ways to define survey key to use. They are mutually exclusive, only one has to be provided
# survey_key is for a single survey profile, surveys allow several surveys to share the same profile parameters
study_key: 'study' # Optional study_key
survey_key: 'survey'
surveys:
 - survey1
 - survey2
start_time: '2022-11-28T00:00:00' # Start download on this time, mandatory
max_time: now # When to end the download (can be necessary if you want to use separated db by year/season for example)
key_separator: '|' # How to separated item key and response key. Can be omitted, default is pipe '|'
survey_info: # If survey_info is provided then survey structure will be exported too 
  lang: fr # Language for labels to be exported
  # format: json # Export format will be stored as json, format is ignored
# format: wide -> not used
# short_keys: false -> short keys are always use, providing 'False' will be ignored

compressor: 'zstd' # How to compress json raw data in the database 'zstd','zlib','zlib-1','none'
                   # By default use the best available (zstd if present or zlib-1)
                   # Once created it cannot be changed as the data are already compressed. 
                   # All data in the same data must have the same compression policy (even if defined in separated profile, compressor choice is stored in db)
```

> Warning: `key_separator` must be the same for all surveys in the target database, it's advised to use always the same response key separator character (default is pipe character `|`). Never use dot '.' or any character used in survey keys ('-', '_' are not advised)

> Warning: If you plan to use export with db build-flat (reimport data in a database `response:db:build-flat`), you must provide `survey_info` entry

### response:db:export

Export one survey (or several if profile use `surveys` entry) from a profile into a target sqlite database

Main Parameters:

- `--profile`: Path to yaml export profile (described in upper paragraph)
- `--db-path`: Database file path where to store the response (if not exists will create the database using this file path)

Optional parameters:

- `--study`: The study key (can be defined in profile)
- `--survey`: Optional survey key to run a profile only for one survey, only works for multiple survey profile
- `--page-size`: Number of response to download at once, default is 1000. You can increase but increase memory load of the server and can cause error
- `--start-from`: Force the start time to this time (iso string format e.g. '2024-11-25T00:00:00')
- `--restart`: Force restart from `start_time` in the profile

### response:db:export-plan

Export several profiles in one command

This command requires a little yaml file, exactly the same as `response:export-plan` command

```yaml
study: grippenet # Name of the study where the survey lives
profiles: # Name of the profile files of each survey to export (relative path to the yaml plan file, simplest : in the same directory)
  - intake.yaml
  - weekly.yaml
  - vaccination.yaml
```

Parameters:

- `--db-path`: Database file path
- `--plan`:  yaml files with export plan (as described above)

Optional parameters:
- `--page-size`: Number of response to download at once
- `--restart`: force restart from `start_time` in each profile 
        
## Export Database Schema

Export database is an SQLite database stored in a single file.

Several tables are created in the database

### Table `survey_info`

Stores the survey info description in json:

- survey: survey key
- version: survey version 
- data: survey info as json

### Table `import_log``

Stores log about import 

- time: timestamp of the import
- survey_key: survey key 
- start: start_time of the import 
- end: end_time of the import

### Table `export_meta``

Stores parameters of the export. Ensure consistency of exports. This table is a single row table (using id constraint)

- id: always '1', force single row
- key_separator: key separator used to build the column name, must be the same across all responses data in this db
- use_jsonb: flag to use (or not) jsonb format. 

### Response data table

Table name will be `responses_{survey}`.
If survey is 'weekly', table name will be `responses_weekly`

Each row contains a single response stored in json (or jsonb)

Columns:
- id: response id (as provided in response data)
- submitted: submitted time
- version: survey version of this response
- data: raw response data (json or jsonb depending on `use_jsonb`in export_meta table) 
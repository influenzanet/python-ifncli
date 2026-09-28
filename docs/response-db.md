# Response db 

The 'response:db:*' commands offer a new way to export data from the Influenzanet platform.

They provides 2 main features:

- Downloading the raw data to a single file database, which allows to sync the data (no more merging multiple csv files)
- Build an analysis database (single file too) from this local database with one table for each survey.

## Setup

First, ensure that the 'response:db' commands are available (if you can only see `response:db:unavailable`, it's because some Python packages are missing).
Install the missing packages with pip or uv (see readme.md file for installation instructions).

Use the command `response:db:setup` to create the necessary configuration files (it will ask for some questions and create YAML files for the 2 steps).

You will need to define where to place 2 files:
- The download database (for example 'data/download.db')
- The analysis database (for example 'data/analysis.duckdb') - It's a DuckDb database so by convention we use '.duckdb' extension here but '.db' could be fine too.

## Download

```bash
./ifn response:db:export --profile=./path/to/export-db.yml --db-path=/path/to/download.db 
```

The `export-db.yml` file contains parameters to describe what to export (called "profile")
Details are provided in [./response-db-export.md](Response db Export Page)

For example:
```yaml
study_key: grippenet
surveys:
- intake
- weekly
- vaccination
start_time: '2022-11-28T00:00:00'
max_time: now
survey_info:
  lang: fr
```

Once the script has been run, it will download all the data from 2021-11-01 to the current time.
If the script is run again, it will start where it left off (after the last response time downloaded).

You can use '--restart' option to reset the time and download the data from the start again.

The data are indexed by response `id`, so data will not be duplicated.

## Build an analysis database

This step will create (or update) another database file, but with data organized in a much more usable way for analysis. The responses for each survey will be in a specific table. For example 'intake' survey will be in a table
named 'pollster_results_intake', this weirdo name is to be ensure compatibility with old platform table name.

The script will use survey descriptions to infer the best data type (for example, responses of multiple-choice question will be in boolean column,and response of a date question, provided as timestamp will be in 'date' typed column).

For more details, see [Response db Build commands](response-db-build.md)

```bash
./ifn response:db:build --profile=./path/to/build-plan.yml --data-path=/path/to/data/files
```

Here `profile` is another configuration file and `data-path` where to find the databases files (it's strongly set here that both database files - raw data and analysis - are in the same directory, if not it's possible to define each by absolute path)

A simple profile to build database:

```yaml
source_db: '{data_path}/download.db'
target_db: '{data_path}/analysis.duckdb'
surveys:
  intake: ~
  weekly: ~
  vaccination: ~
```

It specifies the location of the databases (relatively to `data-path` argument), and the surveys to be exported. The '~' value here stands for 'null' wich will use default parameters for this survey.

Profiles for each survey can be highly customised, to remap the names provided in raw data to column names.

Especially it's possible to add processors that can apply transformations to raw data, such as renaming the response key to have more friendly name or avoiding collision in question name (see the Builder principles section in [Response Db build Command](response-db-build.md) document).

For example, the survey weekly in version '21-11-1' and '22-12-1', some question names (Qxx) are duplicated in different question groups. Question Q10, for example, exists once in the main question group and once in the 'EX' question group. The response key generated will be 'weekly.main.Q10' and 'weekly.EX.Q10', but the builder only considers the last segment of the name (question name) is used, which creates a collision for the question name 'Q10'.

In the following example we rename the question named 'EX.Qxx' to 'EX_Qxx' which avoids a collision on question name (Qxx).

```yaml
source_db: '{data_path}/download.db'
target_db: '{data_path}/analysis.duckdb'
surveys:
  intake: ~
  weekly: 
    processors:
        - version: '21-11-1,22-12-1'
          name: 'rename'
          rules:
            - regex: 
                '^EX\.Q': 'EX_Q'
  vaccination: ~
```
# Import Data into analysis database

Requirements:
- Some python packages need to be installed to make the commands available, if not 'response:db:unavailable' command is only available
- Data must be exported in an sqlite database using the response:db:export* command
- The export profile must have `survey_info` entry to ensure survey schema is available

The 'import' commands are dedicated to reimport raw data into another database and transform the raw response data (in json) into flat table

The general schema of the export is:

response:db:export -> raw sqlite database (json response) -> response:db:import -> duckddb (flat table columns=question responses)

To **import** data you will need a source database used to export raw data, and a target database 

Two different databases are used because they are not dedicated to the same usage. The database containing raw data is dedicated to synchronise the export from the platform which are intented to be transformed in a a more convenient format for the data analysis. It contains data in a raw format (json) which is really heavy.

Raw data could be transformed to a more convenient format like table, csv. And is indepdendent of the download process (no need to merge and reconciliate multiple csv files).

The import database uses duckdb format and flat tables, much more compact than csv, with data type preservation (boolean columns, date could be date column, ...) and a single file

## Import principles

The raw data are provided as a json, each question will produces one or several data element each with a unique key and a value.
A single survey response is a list of key, value pairs represented in json a json object with mostly a single string value but sometime it can be a json object (if the server data exporter cannot infer the question type).

The import into flat table will need to define the *schema* of the data, associating each data element of the response with a name and a data type. 

Name of the data could be the ones provided in the raw data, but those names are not convienient to use in data analysis programs (using some characters not useable as regular variable name) or for Influenzanet not following the names already in use in the previous platform making harder the use with legacy data. So it's usually a better approach to rename data elements to simpler and classic column names (only with letters/numbers and '_')

Data types are not well represented in the raw data, many values are provided as string but are natively more simpler types (boolean are provided as text 'TRUE' and 'FALSE', datetime are provided as integer timestamp). In case of using custom question or complex question (with different response types in the same question) data will be provided as a json entry

### The import process

The import will provide 2 transformations :
- Name of each data element (using transformation rules)
- Data type of each column

The import process is :

- Load a batch of `batch_size` responses from the raw responses database
- Group the responses in the loaded batch by survey version
- From the survey version group
    - Transform to Pandas DataFrame
    - Define the list of Processors to apply to the data for the survey version of the group
    - Apply transformation processors to the data in order
    - Import the transformed data into the target database
        - Create table if not exists (default table is `pollster_results_{survey_key}` as in the legacy platform)
        - If table exists, create non existent columns
        - Insert the data
        - Update the participant index table

### Data Processors 

Processors are operation dedicated to transform the data into a desired format
Two types of processors are provided:

- Renaming processor : transform the name of columns into another name (for example using regular expression)
- Data casting processor: Transform the type of the columns

By default, 2 processors are applied to the data:
- Default renaming processor : applied rules to transform data names into columns names following legacy Influenzanet names
- Default casting processor: will apply data type casting from the infered data type schema (see below)

Be aware that the default casting processor knows the columns names in the raw data.

### The Inferred schema

The data schema is by default inferred from the survey info (they must be activated in the raw data export profile) determining from question type what is the most probable data type. But it's not perfect.

Some problems can occur (in the same survey) if you have defined the same question key but the question type has changed, the response element could have a different data type. In this case you have to override the schema or define you own schema completely (see import profile)

> Warning: In general case a question key must be applied only once to a given question, if the type of the response (i.e. single response, multiple, ...) it's not the same question then another question key should be used. 
> If the question response are extended (like adding possible response in single or multiple choice for example) it's not considered as a change of question (but it's up to you to change the question key), it will not break the schema in this case.

The import engine allows to provide a manual schema, by defining for each data entry what type to apply (it's only applied by default casting processor, if you dont use it you will need to define you own processo to be applied).

Beware that the default casting processor is using the schema from the raw data, names of the data are the ones in the raw data. If you add renaming process before it some columns will not be identified and not transformed. It can be handled in the import profile.

## Import profile

The import profile is a yaml file configuring how to handle the import. In a simple case it will be very simple. Some options are provided to enable customization and handling problems in the infered schema.

Many elements of the profile can also been provided as argument in the command line of command `response:db:import`
You can mix both (some defined in profile if they dont change, others in command line), command line parameter will override the one in the profile.

```yaml
survey: survey_key
# Databases path 
source_db: /path/to/the/raw/export/db
source_table: 'responses_{survey}' # Optional table containing response data of the survey (default is exporter convention)
target_db: /path/to/the/target/duckdb
target_table: 'pollster_results_{survey}' # Optional target table name, default is Influenzanet's legacy table name 

# Import criteria (what to import from the )
from_time: '' # Optional, starting time of the import (default no time, import all )
to_time: '' # Optional, ending time of the import (default no time)
versions: # Version selector of the survey to load (default is all), see version selector below
batch_size: 1000 # Number of response to load at once (will load until no more data is available)
starting_offset: 0 # Starting offset of the query in source db (only to be used for debugging)

# Debug options (see debug)
debugger: '' # List of debug flags

# Schema : give the data type to use for each data name
# Schema is used only by default casting processor (if you dont use it it's not necessary)
infer_schema: true # Infer schema from the survey_info, usually it's possible to use it, if you set it to
                   # false you will need to define manually all data types you want to change
schema: # Override the schema
    data_name: type
    ....

# Processors definition (see processor definition)
processors:
  - <processor_definition>
  ....
```

### Survey schema

Survey schema inform the Default Casting processor how to transform data type of some columns.

Currently only handles types:
- 'date': transform timestamp integer to date time column
- 'bool': transform column to boolean values
- 'json': explode json contents to flat columns 

The schema is provided as a simple key value dictionary, where key is the data element name (key in the raw).
Beware that the names depends on when the casting processor is applied, if you define renaming before

### Processors

Processors can help to handles problems in raw data blocking the transformation process.

Each entry in `processors` can be:
- a string to refer to builtin operators: 'default_casting', 'default_renaming'
- a custom processor definition (yaml object)

```yaml
name: # Name of the processor ('rename', 'to_bool', 'to_date')
position: # optional can define the processor position relative to default one 'before_casting', 'after_casting', 'end'
version: # Version selector (string or more complex list)
# For data transformation only 'to_bool', 'to_date'
columns: # Column selector
    - <column_rule>
# For 'rename' processor
rules: 
    - <rename_rule>
```

#### <rename_rule> Remanimg rules 

Renaming rules can use 2 methods: regex using regular expression or fixed rules

You provide each rule as an object with key as the method to use, like in the following example

```yaml
  - name: 'rename'
    rules:
        - regex:
            'pattern':'replace'
        - fixed:
            'old_name':'new_name'
```

Rules are applied in order of the list, it's advised to use separated rules if you want to have renaming sequence (i.e. the same name renamed successively by several renaming expressions)

Regex rules uses python regex regular expression, you can use '\1'..'\9' in replace expression to use capturing group results.
In regex you can use '<$>' (wihout any escaping), it will be replaced by the key_separator used in the data names.

#### Default Renaming Processor

This renaming processor apply several rules:
- remove any prefix from question key (i.e. remove anything before a dot '.' in the question key)
- matrix row mat.row{x}.col{y} -> multi_row{x}_col{y} (legacy platform name)
- likert_{x} -> lk_{x}
- Any key separator is then replaced by a '_' : 'Q1|0' -> 'Q1_0', 'Q1|0|open' -> 'Q1_0_open'
- Some predefined columns are renamed to legacy platform names
    - participantID -> global_id 
    - ID -> id
    - submitted -> timestamp

#### Default casting processor

The default casting processor uses the schema to change column types to common known types: date, bool, json
 
Beware that the casting processor must be used before the renaming rules because the schema is inferred from the raw data names

#### Processors positions

The processor sequence of processors position is :
- 'before_casting', 
- 'default_casting' <-- default processor for data type casting
- 'after_casting', <-- custom processors are run here by default
- 'default_renaming' <-- default processor for data renaming
- 'end'

By default custom processors are inserted in 'after_casting' position (after `default_casting` processor but before `default_renaming`),
Renaming must occurs after the default casting because the casting relies on the raw data names (see schema).

If you want your custom processor to run after all the default processor, use 'end' position.

The order of processors with the same position is preserved.

### Survey Version Selector

Survey version is defined as a 3 number sequence separated by a '-', ex '25-1-2'
2 first numbers are respectively year and month when the survey is published, the last number is the order of the version in the given year/month.

It's strongly infered that the numbers have an order semantic, where a-b-c, evaluation consider in priority a > b > c

To define a processor to be applied only for a given version, you can use version selection expression.

Version selection expression is a boolean expression (will resolve to true/false, true if the proposed version matches the version expression )

It can be represented as a string of rules separated by a comma (',') or a list (in a yaml file) to more readability
A rule preceded by a '!' will use the following rule as an exclusing rule (version matching the rule will be excluded)

Rules: 

- A literal with a single version number will match the exact version number, e.g. '25-2-2'
- A range of version can be defined using ':', e.g: '25-0-0:25-12-99'
- '!22-1-2' : Exclude version 22-1-2 from the selection

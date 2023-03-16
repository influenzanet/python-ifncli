# Default Resources path layout

By default the commands expects resources files to follow a standard organization described in [readme file](../readme.md). Some options can use this default layout to find the files at the expected place, instead of typing the full path.

# Study commands

## `study:show` Study Show

Show global information about a study
By default output a textual human readable of the json
Arguments:

- `--study_key` key of the study to show
- `--json` output json study definition instead of the textual form
- `--lang` Only output text for this language if provided (default: all)

## `study:list` List studies

Show list of available studies

## `study:list-survey` List surveys in a study

Show list of available survey in a study

Arguments:
- **study_key** : key of the study 
- **--lang** : if provided only show the text for this language (use language code like 'fr', 'en')
- **--json** : Output the full json instead of the textual representation

## `study:show-survey` Show a survey definition

Show a survey definition
By default output a textual human readable of the json

Arguments:

- `--study_key STUDY` key of the study to show
- `--survey SURVEY` key of the survey to show
- `--json` output json study definition instead of the textual form
- `--lang LANG` Only output text for this language if provided (default: all)
- `--format NAME` Output format (see below)
- `--output FILE` Save the generated output in the given file
- `--from-file FILE` Use the survey definition provided in the file, this option doesnt fetch data from the databasae

Output formats:

- human: human readable textual format, it's a yaml-like format but only for reading purpose
- dict-yaml: yaml format (parsable) of the simplified human readable format
- dict-json: json dictionary of the simplified human readable format (use --json to get the full json from API) 
- html: static HTML document of the survey definition

## `study:create` Create a new study

Arguments:

- **--study-def-path**: relative or absolute path the to study definitions folder where config files are placed.
- **--secret-from**: File where secretKey is stored (as plain text, full content of file)

Study definition folder

It has to contain two files:

  1. `props.yaml` with the study properties including study key and secret key, 
  2. `study_rules.json` containing the study rules in a json array.

**Caution** provide the secretKey in props.yaml will raise an error. Since study props is intended to be versioned, this is strongly deprecated and the secret should be provided using an external file. 

### Example study props yaml file:
```yaml
studyKey: inf-study-20
status: active
props:
  systemDefaultStudy: true
  startDate: 1590969600
  name:
    en: Influenzanet 20
    de: Influenzanet 20
  description:
    en: <optional description>
    de: <optional description>
  tags:
    - en: covid-19
      de: covid-19
    - en: flu
      de: flu
```


## `study:manage-members` Manage Study Members

Adding or removing non-admin (RESEARCHER) users for studies:

Arguments:

- **--study_key** : Key of an existing study to which the user should be added to or removed from.

- **--user_id** : ID of the user in the userDB.

- **--user_name** :  Email address of the user or human readable alias.
- **--action** : what action to perform for the given study/user pair. By default ADD, optionally override with REMOVE, to remove a user defined by user_id.

## `study:update-rules` Upload new study rules to an existing study

Upload of new study rules to an existing study

This command will update the study rules with the ones provided by the json file for the study specified by the `survey key`.
The user needs permission to modify the study (study member with OWNER, or MAINTAINER role).

Arguments:

- **--study_key** : Key of an existing study to which the survey should be added or updated in.

One of the following arguments:

- **--rules_json_path** : relative or absolute path to a study rule definition file.
- **--default** : this flag will use the default layout path in resources path (./study/[study_key]/studyRules.json)

## `study:custom-rules` Apply custom rules

Arguments:

- **--rules** : JSON File containing the rule to apply
- **--study** or **--study_key** Key of the study to which apply the rule
- **--output**" : path of file to output results (optional, if not provided results will be printed to console)

And One of the following to define the participant list to apply the rule to:

- --all : Apply to all participants
- --pid : participantID (or coma separated list if several)
- --pid-file : file path containing the list of participantID, can be provided as a text file (one line by pid) or JSON file (extension .json)

If pid-file is a json file containing a dictionary, one of the 2 options **must** be provided :
--pid-json-keys : the participant ID is in the key of the provided dictionary
--pid-json-values : the participant ID is in the value of the provided dictionary

If a participant list is provided (so except for **--all** source), optional parameters can be provided:

- --done-file : name of file to store the list of successfully applied participant ID (will create a text file, one pid by line)
- --exclude-done : if provided will read the file given in **--done-file** and exclude participant already in done file of the given list 
 
This can be used if list is very long, to be able to replay the action without applying twice the rule to participants.

## study:import-survey Update a new survey definition for study

This command will create (if not existing) or update a previous survey definition identified by the `survey key`. If a survey currently exists with the key, by default this will be "unpublished" and the new version published.
The user needs permission to modify the study (study member with OWNER, or MAINTAINER role).

Arguments:

- **--study_key**: Key of an existing study to which the survey should be added or updated in. Now optional, tt can be provided in from_name

- **--survey_json**: relative or absolute path to a survey definition file, e.g., as exported by the study manager app.

- **--from-name** : name of the survey, will use the default resources layout path (study/[study_key]/surveys/[name].json). It can be prefixed by the study_key with a '/' (as [study_key]/[survey_key])

Example:

```bash
./ifn-cli study:import-survey --from-name grippenet/weekly

# OR

./ifn-cli study:import-survey --study_key grippenet --from-name weekly

# OR

./ifn-cli study:import-survey --study_key grippenet --survey_json path/to/the/weekly.json

```

### `study:replace-survey` Replace survey object (incl. history)

Before executing the upload, a prompt will ask for confirmation (type "yes" if you want to proceed).

This command will create (if not existing) or update a previous survey definition identified by the `survey key`. 
The user needs permission to modify the study (study member with OWNER, or MAINTAINER role).

Arguments:

- **--study_key** : Key of an existing study to which the survey should be added or updated in.

- **--survey_json** : relative or absolute path to a survey definition file, e.g., as exported by the study manager app.


# Survey command

## `survey:repo:import` Upload survey definition to Influenzanet Survey Repository

This command allow to send the survey definitions of published surveys to the Influenzanet Survey Repository.
The Survey Repository aims at collecting survey definition for common influenzanet survey to document the data collection processing at the european level, and to facilitate common data analysis.

To use this command you will need to configure the repository account in your yaml configuration (entry `survey_repository`). If you dont have an account, contact the Influenzanet team to create one and obtain your credentials.

Arguments:

- `--study` : Study key to use
- `--survey` : The survey keys (can provide several separated by comma. e.g.: 'intake,weekly')
- `--all-versions` : Scan and send all published versions of the surveys
- `--published-after` : Only surveys published after this time (use ISO date/time string e.g. '2025-03-31')

## `survey:repo:list` Show list of surveys in the 

## `survey:standard` Validate a survey definition against standard

Arguments

- profile = path to a profile yaml fil
- survey = path to the json definition file of the survey to validate

Profile:

```yaml
profile:
 standard: # How to define standard 
  # pass file name directly
  file: path/to/file
  # OR
  name: # name of standard
  revision: # Name of branch, tag or commit, default is latest on main 
  repo: # name of the repo, default is 'influenzanet/surveys-standards'
  # OR
  url: full URL of the file to fetch
 prefix: 'intake.'

```

`standard` entry define the way to get the standard (from a file or download from github)
`prefix` is used to put the 'prefix' used in the key of the SurveyDefinition model to remove to have the standard name (usually 'survey_name.')

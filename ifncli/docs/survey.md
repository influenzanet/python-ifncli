# Survey command

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

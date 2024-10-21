


# Changelog

## v1.4

### General
- Fix dependency for python 3.12
- Fix api manager when switching context

### Messages
- handle headerOverrides in email templates

### Response downloading
- Harmonize output argument handling

## v1.3

### General:

- Revert back to cliff behavior (interactive mode) when no command provided. Can change this behaviour by using env variable `IFNCLI_DEFAULT_COMMAND`
- studies path and auto_messages path can be configured in plaform config if directory layout is not used
- Force renew token before execution of a command to Admin API

### Messages
- Email layout ca be disabled
- Improve email layout template processing (detect unknown variable and circular dependency)
- Can import custom message type for studies
- email:import-auto : handle next time expression for email template
- email:import-auto : can separate translations in a file named 'translations.yaml' instead of providing it in settings (to be able to switch settings)
### Study
- study:create : at least one study key or study def path are required (study key will use default directory layout)
- study:create :  Fix study property description import (name was used)
- study:import-survey : Support for uploading  old survey (<=v1.1) into system handling v1.2 surveys
- study:custom-rules : accepts several format for participants id list (), handle done-file and exclude-done file to be able to resume the action

### Response downloading
- response:export-plan : fix plan path detection 
- response export: fix download loop

## v1.2

### General:
- Accepts "plugins" module to define local extra commands (not versioned in this repo)

### Messages
- automessages settings accepts untilTime and condition
- email:import-auto accepts alternate yaml file name (to send the same automessage with different settings)

### Study
- standardize args for study:* commands, accepts `--study-key` or `--study`
- **study:custom-rules** accepts participants ids as argument (coma separated) or from a file

### Other
- add **stats:user** command to fetch data from user-stats-service (https://github.com/grippenet/user-stats-service)

## v1.1

### Messages:

- Automessages import reworked (uses Message classes, can use layout to wrap the message before it's updated like for the email template)
- Can force force nextTime of automessage using the `--at` parameter
- `template_layout` can be used in platform config yaml file  ([resources]/platform.yaml) to defined common layout by default for emails auto and system emails

### Survey & Responses:

- show surveys info once updated (id, versionID)
- Add response downloader commands: schema, response, export-bulk (incremental export) and export-plan (list of surveys)

### Config & Environnement:

- Add context feature, env variable `IFNCLI_CONTEXT` can point to a context file describing the available environnement files and which to use
- Show connection information once (on stderr)

### Migration:

- User migration script adapted

## v1.0

- use influenzanet.api 1.0 (new survey-service endpoint v1.3.0)
- Adapt new survey model for upload
- commands accepting a survey json (study:show-survey, survey:check, survey:validate) handle old and new survey model (survey engine 1.2 and <1.1.7)

## < v1.0

History from a legacy repo (with other projects), with no version
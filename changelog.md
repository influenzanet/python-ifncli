


# Changelog

# v1.2

- add 'stats:user' command to fetch data from user-stats-service (https://github.com/grippenet/user-stats-service)
- standardize args for study:* commands, accepts '--study-key' or '--study'
- 'study:custom-rules' accepts participants ids as argument (coma separated) or from a file
- Accepts "plugins" module to define local extra commands (not versioned in this repo)

## v1.1

Messages:

- Automessages import reworked (uses Message classes, can use layout to wrap the message before it's updated like for the email template)
- Can force force nextTime of automessage using the `--at` parameter
- `template_layout` can be used in platform config yaml file  ([resources]/platform.yaml) to defined common layout by default for emails auto and system emails

Survey & Responses:

- show surveys info once updated (id, versionID)
- Add response downloader commands: schema, response, export-bulk (incremental export) and export-plan (list of surveys)

Config & Environnement:

- Add context feature, env variable `IFNCLI_CONTEXT` can point to a context file describing the available environnement files and which to use
- Show connection information once (on stderr)

Migration:

- User migration script adapted

## v1.0

- use influenzanet.api 1.0 (new survey-service endpoint v1.3.0)
- Adapt new survey model for upload
- commands accepting a survey json (study:show-survey, survey:check, survey:validate) handle old and new survey model (survey engine 1.2 and <1.1.7)

## < v1.0

History from a legacy repo (with other projects), with no version
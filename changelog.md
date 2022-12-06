


# [Unreleased]

- Automessages import reworked (uses Message classes, can use layout)
- Can force force nextTime of automessage using the `--at` parameter
- `template_layout` can be used in platform config yaml file  ([resources]/platform.yaml) to defined common layout by default for emails auto and system emails
- User migration script adapted
- Show connection information once (on stderr)
- show surveys info once updated (id, versionID)
- Add response downloader commands: schema, response and bulk (list of surveys)

# v1.0

- use influenzanet.api 1.0 (new survey-service endpoint v1.3.0)
- Adapt new survey model for upload
- commands accepting a survey json (study:show-survey, survey:check, survey:validate) handle old and new survey model (survey engine 1.2 and <1.1.7)

# < v1.0

History from a legacy repo (with other projects), with no version
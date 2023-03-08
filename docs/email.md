# Email Commands

## `email:import-templates`  Update Email templates

Arguments

- **--email_template_folder**: Optional path to the email template folder (if not given uses default from platform config)
- **--dry-run** : will prepare and preprocess templates but do not send update to the database (so you can check the results).

The default email templates folder is a folder named 'email_templates' in the resource directory (see [])

## Preparations:

The script will assume the following folder structure to be present (`[email_templates]` is the root of the template path)

```
[email_templates]/
|- header-overrides.yaml  (optional)
|- layout.html   (optional)
|-<lang-code-1>/
|    |- account-deleted.html
|    |- account-id-changed.html
|    |- password-changed.html
|    |- password-reset.html
|    |- registration.html
|    |- invitation.html
|    |- study-reminder.html
|    |- subjects.yaml
|    |- verification-code.html
|    |- verify-email.html
|-<lang-code-2>/
|    |- account-deleted.html
|    |- account-id-changed.html
|    |- password-changed.html
    ...
```

### Email Header configuration
The file `header-overrides.yaml` is optional. Content is structured like:

``` 
account-deleted:
  from: "example@org.com"
  sender: "example@org.com"
  replyTo:
    - "example@org.com"
account-id-changed:
  sender: "example@org.com"
invitation: null
password-changed:
  from: "example@org.com"
password-reset: null
registration: null
verification-code: null
verify-email: null
```
Where each message type category could include the following fields:

- `from`: From field for the email header
- `sender`: Sender field for the email header 
- `replyTo`:  List of email addresses to replyTo array will consist. 
- `noReplyTo`: boolean, if true the default noReplyTo config will be overwritten with an empty array.

Note the `subjects.yaml` file - this should contain the translated subject line for each email type in key value pairs:

```
account-deleted: "Account Deletion Successful"
account-id-changed: "Email changed"
password-changed: "Your password was changed"
password-reset: "Reset your password"
registration: "Registered"
invitation: "You have been invited"
verification-code: "Code to login"
verify-email: "Please confirm your email address"
```

### Common HTML layout 

The layout.html is an optional common layout for all the messages. If present it will be used and each message will be wrapped by this layout.
An example layout file is given in the example/ folder of this docs.
It has to be placed at the root of the email templates folder (along with header-overrides.yaml file)

In this file, the placeholder `{=main_content=}` will be replaced by the content of each email template, to create the final email contents (in other words, each email template will be wrapped by this layout to create the final email message to be submitted as the message template for the platform). Once generated a file with the `.built` extension is created alongside each html file with the full email content (to allow to check the content)

It's also possible to define `template_layout` with the relative path of the layout file in platform.yaml (at the root of resources directory). It will be used for all email templates

### Preprocessing of templates

Email template can have preprocessing variable replaced *before* to be updated into the database by fixed values.
These values can be used in a template using the *{=**name**=}* where name will be the lookup keys.

Values are to be defined in the cli config file under the 'vars' entry (see the [readme docs](readme.md)) or in the common platform.yaml file in at the root of the resources directory.

If necessary you can define custom variables (either in config file or in platform.yaml file and use them in your templates).

An Example of the variables in a platform.yaml:
```yaml
vars:
  # ....
  web_app_url: 'https//mywebsite'
  default_language: 'en'
  # Variable can also make reference to other variables and value will be resolved during template processing
  my_login_url: "{=web_app_url=}/login"
```

You can then use *{=web_app_url=}* into the email templates, it will be replaced by the value of the `web_app_url` variable each time the templates are updated.

During the process, for each template an file with the '.built' extension will content the real content to be sent to the server (before the base64 encoding).

## email:send-custom Send a Custom email to participant

Settings.yaml example

````yaml 
messageType: # ?
defaultLanguage: 'en' # Code of the default language 
translations: 
   # One entry by language with the translated template
   -
    lang:
    subject:
    templateFile: '' # relative path to template file, (relative in settings.yaml folder)
````

## email:import-auto Create an automatic email sending rule

email:import-auto [--force] [--dry-run] name

Arguments:

name: name of the auto message to load. Settings will be search in a subdirectory with this name of email_auto in resources dir

--force: If set to true, existing auto message will be ignored and a new one will be created. By default (false), existing auto message with same type, study key and message type will be replaced.

--dry-run: Prepare the automessage and print it but do not update 

name of the automessage, give the name of the subdirectory of auto_messages where the files have to be placed in the resources dir
For example:

email:import-auto weekly

Will search in [resource_path]/auto_messages/weekly/settings.yaml

## Files layout

From the resources directory root, expected path is:

[root]
|
|- auto_messages
  |- [name]  # Name of your automessage (arbitrary name, it your the name you use to tell the cli tool which message to handle)
    |- settings.yaml
    |- template.html

### settings.yaml:

Example content of the ´settings.yaml` file:
```yaml
sendTo: "all-users"  # Type of Automessage
studyKey: ""  # Study keys to use if the type is study-participants
messageType: "weekly" # Type of template to use
nextTime: "2020-09-11-12:25:00" # See below
untilTime:
 - relative: true
   weekday: "sunday"
 - hour: 14
   min: 0
period: 86400
defaultLanguage: "en" # If not provided the platform default can be used
label: "message label" # Optional message label
translations:
  - lang: "en"
    subject: "Weekly study reminder"
    templateFile: "en.html"
```

'nextTime' and untilTime can be either a string with next time or a dictionary object with hour parameter or a list of dictionary
A list will apply each rule, this enable to combine several time modifiers.
Dictionary describes rule to apply on each time part, either fixed or relative to set the time

Relative rule have the entry `relative: true`, if not or false, the rule fix the value

```yaml
nextTime:
  relative: true # Use relative to current time
  hour: 1 # Number of hours to add or fixed hour if relative = false
  min: 1 # Number of minutes to add or fixed minutes if relative = false
```

The following example show the combination of relative and fixed rule

```yaml
untilTime:
 - relative: true
   weekday: "sunday"
 - hour: 14
   min: 0
```

The untilTime will be, the next sunday (first rule, relative), and next fix time to 14:00 to the result of the first rule,
the combination, will give "next sunday at 14:00"

Available time/date part:

relative time rules (with `relative:true`):
- `hour` (number of hour to shift)
- `min` (number of minutes to shift)
- `day` (number of days)
- `weekday` (days of the week)

Fixed rules (with `relative:false` or omitted in the rule):
- `hour`
- `min`
# Email Commands

## `email:import-templates`  Update Email templates

Arguments

- **--default_language**: Which language should be used by default if not defined otherwise
- **--email_template_folder**: Path to the email template folder (folder's content should be as defined above)
- **--dry-run** : will prepare and preprocess templates but do not send update to the database.

### Preparations:
The script will assume the following folder structure to be present at the given location (by default `./resources`):
```
email_templates/
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
### Preprocessing of templates
Email template can have preprocessing variable replaced *before* to be updated into the database by fixed values.
These values can be used in a template using the *{=**name**=}* where name will be the lookup keys.
Values are to be defined in the cli config file under the 'email_vars' entry

Example:
```yaml
email_vars:
  web_url: 'https//mywebsite'
```

You can then use *{=web_url=}* into the email templates, it will be replaced by the value of the `web_url` variable each time the templates are updated.

If a file named 'layout.html' is placed in the root of the email templates folder. 
In this file, the tag `{=main_content=}` will be replaced by each template content, to create the full
template.

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

Arguments:

--email_folder: Path to the folder containing the email's config and content files. By default it is expected to be in `./resources/auto_reminder_email`. The folder should contain the file `settings.yaml` and all html templates referenced from this file.

--ignore_existing: If set to true, existing auto message will be ignored and a new one will be created. By default (false), existing auto message with same type, study key and message type will be replaced.

### Example setting:

Example content of the ´settings.yaml` file:
```yaml
sendTo: "all-users"
studyKey: ""
messageType: "weekly"
nextTime: "2020-09-11-12:25:00"
period: 86400
defaultLanguage: "en"
translations:
  - lang: "en"
    subject: "Weekly study reminder"
    templateFile: "en.html"
```


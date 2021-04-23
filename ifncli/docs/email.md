# Email Commands



## Update Email templates

### Arguments

```
--dry-run : will prepare and preprocess templates but do not send update to the database.
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

## SendCustom

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

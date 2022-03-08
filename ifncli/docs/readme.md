# Influenzanet Command Line tool

## Usage

To run the CLI, run `ifn-cli` command

```bash
./ifn-cli -h
```

On Windows you may need to run

```batch
python ifn-cli
```

## Configuration

The configuration (API url, credentials,...) are expected to be provided in a yaml file.
The default file will be looked up at file is at `./resources/config.yaml`.
This configuration file has to be seen as a kubeconfig file for the platform, it will contains the context to manage a platform.

Content should be:
```yaml
management_api_url: "<http url with port>"
participant_api_url: "<http url with port>" 
user_credentials:
  email: "<user-account@email.com>"
  password: "<strong-password>"
  instanceId: "<default-instanceID>"
resources_path: path/to/resources/dir # Path pointing to directory with resources
vars:  # Variables to be used for this config. They overrides the ones in the platform config file (see Resource Directory)
  web_url: value
  default_language: en
```

To use another location either:

- use the '--config' argument
- Define the environment variable `IFN_CONFIG` with the path of the yaml file to use.

To manage several platforms you can have one config for each, and switch from one another by changing the 

## Resource Directory

The resource directory contains the needed resources to configure a given platform. It can be versioned (using git for example) to enable collaboration & tracking of the history. 

### Platform config.

The resource directory can contains a yaml file named "platform.yaml" containing the default values for the platforms. The values contained in this file will be overriden by the ones provided 'vars' section in the tool configuration file.

The platform config has the following structure:

```yaml
vars:
  # Default values for common platform variables
  # These values can be overridden in the config file (in the "vars" section)
  web_url: https//my.platform.com  # URL of the Participant website URL
  default_language: en # Default language to be used in the email template

```

### Other resources
Some files/directory are expected as default (it would work better if you follow this layout).

- email_templates: email templates (organized by language), the organization of the files is described in the [emails and templates management](email.md)
- auto_reminder_email

It can contains other resources (study files, etc)

## Commands 

Commands are grouped by namespaces

- email: [emails and templates management](email.md)
- study: [study management commands](study.md)
- response: [fetch responses data](response.md)
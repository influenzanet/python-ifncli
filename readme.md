# Influenzanet Command Line tool

Influenzanet CLI tools provides some command line tools to manage Influenzanet instances.

## Disclaimer:

- These tools are *not* official tools but WIP tools (several implementations of such tools exist) from standalone python scripts
- It's not as complete as the other ones (we complete them as soon as we need the tool)
  
It proposes:
- An organization layout for resources files layout (things work easier when files are placed following it)
- A way to handle configuration of instances with common variables (useable in email templates) by instance and by deployment environment
- A common HTML layout useable for email templates (the templates files will be wrapped in the layout before submission)
- Tools to check survey consistency (including expressions) 
- Transformation ofs survey json to (more) human readable html or yaml document

ifncli is based on :

- [cliff](https://docs.openstack.org/cliff/latest) command line framework
- [influenzanet.api](https://github.com/influenzanet/python-influenzanet-api) package to interact with management API
- [influenzanet.surveys](https://github.com/influenzanet/python-influenzanet-surveys) package to work with surveys 
## Overview

In the following we consider two different things :

- An instance : as a configured influenzanet system for a given project (for example for a country). 
- A deployment : the instance is installed and online in a given IT environment (in a production server, in a local dev cluster, ...)

An given instance can be deployed in several environments with some differences. The following organisation aims at separate the common parts (what will be the same in all environments) and what will be specific for one environment to facilitate the reproducibility.

To run, the tool will expect 2 things :

- A configuration file (in yaml) containing the information about the influenzanet instance to manage in an environment (this file is specific on one deployment)
- A resources directory containing all the files needed to configure the instance (email templates, study/surveys, ...); all the data you will inject into the deployed instance to configure/run it. This resources directory is specific of the instance (for one country for example) but not of the deployment (the same resource directory can be used for development/testing). 

You can use several config file, each one will contains information about how to manage one influenzanet instance in a given environment (on production server, on local cluster for dev, etc.). It will contain some configuration values specific to the deployed environment (for example the URL of the website will not be the same in prod/dev environments).

## Installation

- Clone this repo
  
- Install the requirements

```python
pip install -r requirements.txt
```

- create the .local directory to put your environment config .yaml files (recommended)

- create a environment yaml config (see Environment Configuration file for content) with credentials

- If the location of the resources files is not in the yaml, you can create (or symlink) a 'resources' dir in it (it's ignored by git) it's default location.

Try to login:

```bash
./ifn login
```

## Usage

To run the CLI, run `ifn-cli` command

```bash
./ifn -h
```

On Windows you may need to run

```batch
python ifn
```

or create a batch file ifn.bat like 

```batch
python ifn %*
```

## Environment Configuration file

The configuration (API url, credentials,...) are expected to be provided in a yaml file. A default file will be looked up at file is at `./resources/config.yaml`.

This configuration file is specific for one influenzanet instance and a given deployment environment (like a kubeconfig or a .env.local file)

Content should be:
```yaml
management_api_url: "<http url with port>"
participant_api_url: "<http url with port>" 
user_credentials:
  email: "<user-account@email.com>"
  password: "<strong-password>"
  instanceId: "<default-instanceID>"
resources_path: path/to/resources/dir # Path pointing to directory with resources
vars:  # Variables of the platform to be used in the email templates. They overrides the ones in the platform config file (see Resource Directory)
  web_app_url: value
  default_language: en
```

`web_app_url` is an example (you have to use it in your email templates using the syntax described in [the doc](docs/email.md), as it's user defined you can define the variables you want and use them in templates.

To use a configuration file you can either:

- use the '--config' argument and pass the file location
- Define the environment variable `IFN_CONFIG` with the path of the yaml file to use (caution it's not 'INF_CONFIG').

To manage several platforms you can have one config for each, and switch from one another by changing the environment variable value to point to another configuration variable.

The following resources directory is probably to be tracked by a VCS (like git) so it's recommended to put those configuration files outside it.

For example on my local copy, the config files are in a .local directory and files (survey, templates) in the resources/ (symlink from another location)
## Resources Directory

The resources directory contains the needed resources to configure a given instance of the Influenzanet system. It can be versioned (using git for example) to enable collaboration & tracking of the history. Of course it should not contains any secret values (neither the config yaml describes in the previous section because it contains credentials)

The standard layout (following paths are relative to the resources directory root), names in [brackets] indicate a *variable name* (user-defined), it's up to you to decide the value.

```
platform.yaml  #  Platform configuration file
email_templates # Email templates
  +-
    layout.html # Common HTML layout template (optional)
    [language]
      +- 
        invitation.html  # Template for "invitation" email
        password-changed.html # Template for password-changed email 
        ... # And so on
study
  [study_key]
    +-
      props.yaml
      studyRules.json
      surveys
        +-
          [survey_name].json
        
```

For example, a survey named "weekly" of the study "influenzanet" (study_key=influenzanet) will have its definition file expected at :  ./study/influenzanet/surveys/weekly.json

### Platform config.

The resources directory can contain a yaml file named `platform.yaml` containing the default values for the instance (regardless the deployment). The values contained in this file will be overridden by the ones provided 'vars' section in the environment configuration file.

You can put in this file the values that are not supposed to be changed regardless the environment (like ".env" file or the default values.yaml of an helm chart)

If you need to use different values for one deployment/environment, you have to override this values in the 'vars' section of the config file for this environment.  

The platform config has the following structure:

```yaml
vars:
  # Default values for common platform variables
  # These values can be overridden in the config file (in the "vars" section)
  web_app_url: https//my.platform.com  # URL of the Participant website URL
  default_language: en # Default language to be used in the email template

```

### Other resources
Some files/directory are expected as default (it would work better if you follow this layout).

- email_templates: email templates (organized by language), the organization of the files is described in the [emails and templates management](docs/email.md)
- auto_reminder_email

It can contain other resources (study files, etc)

## Commands 

Commands are grouped by namespaces

- email: [emails and templates management](docs/email.md)
- study: [study management commands](docs/study.md)

Some commands can help to manage the configuration :

```bash
./ifn config:show 
```

Will show the current configuration and the platform variables (after overrides). This command will also show from where each variable takes its value (from platform file or config file) to be able follow the overriding process.

```bash
./ifn login
```

This command will try to log in to the management API using the current configuration 
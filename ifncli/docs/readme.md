# Influenzanet Command Line tool

Influenzanet CLI tools provides management tool for an influenzanet instance. 

## Overview

In the following we consider two differents things :

- An instance : as a configured influenzanet system for a given project (for example for a country). 
- A deployment : the instance is installed and online in a given IT environment (in a production server, in a local dev cluster, ...)

An given instance can be deployed in several environments with some differences. The following organisation aims at separate the common parts (what will be the same in all environments) and what will be specific for one environment to facilitate the reproductibility.

To run, the tool will expect 2 things :

- A configuration file (in yaml) containing the information about the influenzanet instance to manage in an environment (this file is specific on one deployment)
- A resources directory containing all the files needed to configure the instance (email templates, study/surveys, ...); all the data you will inject into the deployed instance to configure/run it. This resources directory is specific of the instance (for one country for example) but not of the deployment (the same resource directory can be used for developpement/testing). 

You can use several config file, each one will contains information about how to manage one influenzanet instance in a given environment (on production server, on local cluster for dev, etc.). It will contain some configuration values specific to the deployed environment (for example the URL of the website will not be the same in prod/dev environments).

## Usage

To run the CLI, run `ifn-cli` command

```bash
./ifn-cli -h
```

On Windows you may need to run

```batch
python ifn-cli
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

To use another location either:

- use the '--config' argument
- Define the environment variable `IFN_CONFIG` with the path of the yaml file to use.

To manage several platforms you can have one config for each, and switch from one another by changing the environment variable.

## Resources Directory

The resources directory contains the needed resources to configure a given instance of the Influenzanet system. It can be versioned (using git for example) to enable collaboration & tracking of the history. Of course it should not contains any secret values.

### Platform config.

The resources directory can contain a yaml file named "platform.yaml" containing the default values for the instance. The values contained in this file will be overriden by the ones provided 'vars' section in the tool configuration file.
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

- email_templates: email templates (organized by language), the organization of the files is described in the [emails and templates management](email.md)
- auto_reminder_email

It can contain other resources (study files, etc)

## Commands 

Commands are grouped by namespaces

- email: [emails and templates management](email.md)
- study: [study management commands](study.md)
- response: [fetch responses data](response.md)

Some commands can help to manage the configuration :

```bash
./ifn-cli config:show 
```

Will show the current configuration (config.yaml) and the platform variables (after overrides). This command will also show from where each variable takes its value (from platform file or config file) to be able follow the overriding process.

```bash
./ifn-cli login
```

This command will try to log in to the management API using the current configuration 
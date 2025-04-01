# Influenzanet Command Line tool

Influenzanet CLI tools provides some command line tools to manage Influenzanet instances.
  
It proposes:
- An organization layout for resources files layout (things work easier when files are placed following this layout)
- A way to handle configuration of instances with common variables (useable in email templates) by instance and by deployment environment
- A common HTML layout useable for email templates (the templates files will be wrapped in the layout before submission)
- Tools to check survey consistency (including expressions) 
- Transformation of survey json to (more) human readable html or yaml document

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

# If you plan to use survey repository
# user, password and platform code have to be provided by the Influenzanet admin team.
survey_repository:
 user: your-user
 password: your-password
 platform_code: your-platform-code
 # Optional list of studies with for each study a list of survey to send
 studies: 
  my-study: # Name to the study holding the surveys to send to the repository
    - intake
    - weekly
    - vaccination
    # Influenzanet standard names are : intake, weekly, vaccination
    # If the survey key used by the platform is not the standard name
    # You can rename the survey with a common name as common_name=survey_key
    # In the following, the survey key 'intake_vac' (survey name in your study) will be sent with the common survey name 'vaccination'
    # In this case the line value must be between quote ''   
    - vaccination=intake_vac
```

`web_app_url` is an example (you have to use it in your email templates using the syntax described in [the doc](docs/email.md), as it's user defined you can define the variables you want and use them in templates.

To use a configuration file you have 3 ways:

If you have one fixed target environment (you only manages one platform deployed on one location):

You can either:
- Define the environment variable `IFN_CONFIG` with the path of the yaml file to use (caution it's not 'INF_CONFIG').
- or use the '--config' argument and pass the file location

To manage several platforms you can have one config for each and use the **context** feature described below.

**Tips:** : To know what is the current config, you can use starship (see [Starship](#use-with-starship))

The following resources directory is probably to be tracked by a VCS (like git) so it's recommended to put those configuration files outside it.

For example on my local copy, the config files are in a .local directory and files (survey, templates) in the resources/ (symlink from another location)

### Context

If you have several environment it's painful to redefine each time the location of the configuration. To manage this, we use the 'context'

A config file (yes another one) contains the list of known environment config file with for each a nick name

The context file is :
```yaml
# current entry define the name of the current context to use
current: prod
configs:
# Each config entry associate a nickname (name for this target env) and a path to the config file with environment config
  prod: path/to/my/prod/conf.yaml
  dev: path/to/my/dev/conf.yaml
```

You just have to create this file (suggestion: the same place as the other environment files, like '.local' folder) and put the path to this file into the environment variable named `IFNCLI_CONTEXT`

For example, if your context file is at .local/contexts.yaml
```yaml
export IFNCLI_CONTEXT=.local/contexts.yaml
```

Several commands are available to manage environments :

- `config:contexts` : read the context file and show list of known environnements
- `config:switch` : to switch to another environnement (e.g `./ifn config:switch prod` will switch to config named 'prod' for all next commands)
- `config:show`: show the current configuration (it merges the platform variable and the env ones, so you can see the actual config in use)
- `login` : test to log in with the current config

## Resources Directory

The resources directory contains the needed resources to configure a given instance of the Influenzanet system. It can be versioned (using git for example) to enable collaboration & tracking of the history. Of course it should not contains any secret values (neither the config yaml describes in the previous section because it contains credentials)

The standard layout (following paths are relative to the resources directory root), names in [brackets] indicate a *variable name* (user-defined), it's up to you to decide the value.

Here the expected files organization from the root of the resources directory:

```
platform.yaml  #  Platform configuration file
auto_messages
  |--[name]  # Name of a 
    |-- settings.yaml
email_templates # Email templates
    |--layout.html # Common HTML layout template (optional)
    |-- [language]
      |--  invitation.html  # Template for "invitation" email
      |--  password-changed.html # Template for password-changed email 
      |--  ... # And so on
study
  |--[study_key]
    |--  props.yaml
    |--  studyRules.json
    |--  surveys
        |--[survey_name].json
        
```

An example with real names:
```
platform.yaml  #  Platform configuration file
auto_messages
  |-- weekly  # For the weekly reminder automessage (directory name here is user-defined)
    |-- settings.yaml
    |-- template_fr.html
email_templates # Email templates
    |--layout.html # Common HTML layout template (optional)
    |-- en
      |--  invitation.html  # Template for "invitation" email
      |--  password-changed.html # Template for password-changed email 
      |--  ... # And so on
    |-- fr
      |--  invitation.html  # Template for "invitation" email
      |--  password-changed.html # Template for password-changed email 
      |--  ... # And so on
study
  |-- grippenet
    |--  props.yaml
    |--  studyRules.json
    |--  surveys
        |-- weekly.json
        |-- intake.json
        |-- vaccination.json
        
```

For example, a survey named "weekly" of the study "influenzanet" (study_key=influenzanet) will have its definition file expected at :  ./study/influenzanet/surveys/weekly.json

### Platform config.

The resources directory can contain a yaml file named `platform.yaml` containing the default values for the instance (regardless the deployment). The values contained in this file will be overridden by the ones provided 'vars' section in the environment configuration file.

You can put in this file the values that are not supposed to be changed regardless the environment (like ".env" file or the default values.yaml of an helm chart)

If you need to use different values for one deployment/environment, you have to override this values in the 'vars' section of the config file for this environment.  

The platform config has the following structure:

```yaml
template_layout: /path/to/template/layout.html # Optional template layout to wrap with the email templates
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

## Add Custom commands

It's possible to extend ifncli to add custom commands by defining a module "plugins" at the same level as "ifncli"
The plugin module has to provide a Plugin class

In plugins/__init__.py

```python
from ifncli.plugin import BasePlugin

COMMANDS = []

def register(klass):
    COMMANDS.append(klass)

class Plugin(BasePlugin):
    
    def get_commands(self):
        return COMMANDS

from . import mycommands
```

You can then create new commands, for example in plugins/mycommands.py
```python
from cliff.command import Command
from . import register

class MyAwesomeCommand(Command):

    name = "my:awesome"

    def get_parser(self, prog_name):
        # Implements this method to parse options or arguments
        parser = super(MyAwesomeCommand, self).get_parser(prog_name)
        return parser  

    def take_action(self, args):
        # Here the commands
        pass

# This make the command available 
register(MyAwesomeCommand)


```


## Use with starship

[starship](https://starship.rs/) is a command line companion guessing from the current directory and env to show some information on what 
(for example starship can show the python version with the current python command found in path - or in venv ).

The following configuration extension can print in the header of your console the targeted Management API in use for ifncli if you are using IFN_CONFIG
environment variable. It requires sh/bash and [`yq`](https://github.com/mikefarah/yq) tool to be installed.

```toml
[custom.ifn_context]
when= """ test "$IFN_CONFIG" != "" -a -d ifncli """
command="cat $IFN_CONFIG | yq '.management_api_url'"
symbol="🦠"
```
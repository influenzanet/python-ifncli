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

The configuration (API url, credentials,...) are expected to be provided in a yaml file

Default location for this file is at `./resources/config.yaml`.

Content should be:
```yaml
management_api_url: "<http url with port>"
user_credentials:
  email: "<user-account@email.com>"
  password: "<strong-password>"
  instanceId: "<default-instanceID>"
email_vars:
  myvariable: value
```

To use another location either:

- use the '--config' argument
- Define the environment variable `IFN_CONFIG` with the path of the yaml file to use  

## Commands 

Commands are grouped by namespaces

- email: [emails and templates management](email.md)
- study: [study management commands](study.md)
- response: [fetch responses data](response.md)
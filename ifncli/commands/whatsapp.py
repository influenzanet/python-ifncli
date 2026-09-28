import json
import requests
from cliff.command import Command
from ..platform import PlatformResources
from . import register
from ..utils import read_json
from ..managers.whatsapp import DEFAULT_API_VERSION, bind_template_vars


FACEBOOK_API_BASE = "https://graph.facebook.com"
FACEBOOK_API_VERSION = DEFAULT_API_VERSION


def get_whatsapp_config(app):
    """Get WhatsApp configuration from the app config (orbyta.yaml whatsapp section)"""
    configs = app.appConfigManager.get_configs()
    wa_config = configs.get('whatsapp', None)
    if wa_config is None:
        raise Exception("WhatsApp configuration not found in config file. Add a 'whatsapp' section with business_account_id, phone_number_id, access_token")
    required = ['business_account_id', 'access_token']
    missing = [k for k in required if k not in wa_config]
    if missing:
        raise Exception("Missing WhatsApp config keys: %s" % ', '.join(missing))
    return wa_config


def get_api_url(wa_config):
    """Build the Facebook API URL for message templates"""
    version = wa_config.get('api_version', FACEBOOK_API_VERSION)
    account_id = wa_config['business_account_id']
    return "%s/%s/%s/message_templates" % (FACEBOOK_API_BASE, version, account_id)


def get_api_headers(wa_config):
    return {
        "Authorization": "Bearer %s" % wa_config['access_token'],
        "Content-Type": "application/json",
    }


class WhatsAppListTemplates(Command):
    """
        List available WhatsApp templates from local files

        Scans the whatsapp_templates directory for JSON template files organized by language.
    """

    name = 'whatsapp:list-templates'

    def get_parser(self, prog_name):
        parser = super(WhatsAppListTemplates, self).get_parser(prog_name)
        parser.add_argument("--language", help="Filter by language code (e.g. en, it)", default=None)
        return parser

    def take_action(self, args):
        platform: PlatformResources = self.app.appConfigManager.get_platform()
        templates_path = platform.get_path().get_whatsapp_templates_path()

        if not templates_path.exists():
            print("WhatsApp templates path not found: %s" % templates_path)
            return

        print("WhatsApp templates in: %s" % templates_path)
        print()

        found = False
        for lang_dir in sorted(templates_path.iterdir()):
            if not lang_dir.is_dir():
                continue
            lang = lang_dir.name
            if args.language and lang != args.language:
                continue

            json_files = sorted(lang_dir.glob("*.json"))
            if not json_files:
                continue

            found = True
            print("[%s]" % lang)
            for f in json_files:
                try:
                    data = read_json(str(f))
                    name = data.get('name', f.stem)
                    category = data.get('category', 'N/A')
                    print("  %-30s  category=%-15s  file=%s" % (name, category, f.name))
                except Exception as e:
                    print("  %-30s  ERROR: %s" % (f.name, e))
            print()

        if not found:
            print("No templates found")


class WhatsAppRegisterTemplate(Command):
    """
        Register a WhatsApp template with Facebook

        Registers a specific template by name and language.
        Looks for the JSON file in whatsapp_templates/<language>/<name>.json
    """

    name = 'whatsapp:register-template'

    def get_parser(self, prog_name):
        parser = super(WhatsAppRegisterTemplate, self).get_parser(prog_name)
        parser.add_argument("--dry-run", help="Show what would be sent without making API calls", default=False, action="store_true")
        parser.add_argument("--language", help="Language code (e.g. en, it). If not provided, registers for all languages.", default=None)
        parser.add_argument("name", help="Template name (filename without .json extension)")
        return parser

    def take_action(self, args):
        wa_config = get_whatsapp_config(self.app)
        platform: PlatformResources = self.app.appConfigManager.get_platform()
        templates_path = platform.get_path().get_whatsapp_templates_path()

        url = get_api_url(wa_config)
        headers = get_api_headers(wa_config)

        languages = []
        if args.language:
            languages = [args.language]
        else:
            for lang_dir in sorted(templates_path.iterdir()):
                if lang_dir.is_dir() and (lang_dir / (args.name + ".json")).exists():
                    languages.append(lang_dir.name)

        if not languages:
            print("No template files found for '%s'" % args.name)
            return

        for lang in languages:
            template_file = templates_path / lang / (args.name + ".json")
            if not template_file.exists():
                print("Template file not found: %s" % template_file)
                continue

            try:
                template_data = bind_template_vars(read_json(str(template_file)), platform.get_vars())
            except Exception as e:
                print("Error reading %s: %s" % (template_file, e))
                continue

            template_name = template_data.get('name', args.name)

            if args.dry_run:
                print("[DRY RUN] Would register template '%s' (%s)" % (template_name, lang))
                print("[DRY RUN] POST %s" % url)
                print("[DRY RUN] Payload:")
                print(json.dumps(template_data, indent=2))
                print()
                continue

            print("Registering template '%s' (%s)..." % (template_name, lang))

            try:
                response = requests.post(url, headers=headers, json=template_data)
                response.raise_for_status()
                result = response.json()
                print("  OK - ID: %s, Status: %s" % (result.get('id'), result.get('status', 'unknown')))
            except requests.exceptions.RequestException as e:
                print("  ERROR: %s" % e)
                if hasattr(e, 'response') and e.response is not None:
                    try:
                        error_data = e.response.json()
                        print("  Details: %s" % error_data)
                    except Exception:
                        print("  Response: %s" % e.response.text)


class WhatsAppRegisterAll(Command):
    """
        Register all WhatsApp templates with Facebook

        Finds and registers all JSON template files across all languages.
    """

    name = 'whatsapp:register-all'

    def get_parser(self, prog_name):
        parser = super(WhatsAppRegisterAll, self).get_parser(prog_name)
        parser.add_argument("--dry-run", help="Show what would be sent without making API calls", default=False, action="store_true")
        parser.add_argument("--language", help="Filter by language code (e.g. en, it)", default=None)
        return parser

    def take_action(self, args):
        wa_config = get_whatsapp_config(self.app)
        platform: PlatformResources = self.app.appConfigManager.get_platform()
        templates_path = platform.get_path().get_whatsapp_templates_path()

        if not templates_path.exists():
            print("WhatsApp templates path not found: %s" % templates_path)
            return

        url = get_api_url(wa_config)
        headers = get_api_headers(wa_config)

        count = 0
        errors = 0

        for lang_dir in sorted(templates_path.iterdir()):
            if not lang_dir.is_dir():
                continue
            lang = lang_dir.name
            if args.language and lang != args.language:
                continue

            for template_file in sorted(lang_dir.glob("*.json")):
                try:
                    template_data = bind_template_vars(read_json(str(template_file)), platform.get_vars())
                except Exception as e:
                    print("Error reading %s: %s" % (template_file, e))
                    errors += 1
                    continue

                template_name = template_data.get('name', template_file.stem)

                if args.dry_run:
                    print("[DRY RUN] Would register '%s' (%s) from %s" % (template_name, lang, template_file.name))
                    count += 1
                    continue

                print("Registering '%s' (%s)..." % (template_name, lang))

                try:
                    response = requests.post(url, headers=headers, json=template_data)
                    response.raise_for_status()
                    result = response.json()
                    print("  OK - ID: %s, Status: %s" % (result.get('id'), result.get('status', 'unknown')))
                    count += 1
                except requests.exceptions.RequestException as e:
                    print("  ERROR: %s" % e)
                    if hasattr(e, 'response') and e.response is not None:
                        try:
                            error_data = e.response.json()
                            print("  Details: %s" % error_data)
                        except Exception:
                            print("  Response: %s" % e.response.text)
                    errors += 1

        print()
        print("Done: %d registered, %d errors" % (count, errors))


class WhatsAppStatus(Command):
    """
        Check status of WhatsApp templates on Facebook

        Queries the Facebook Graph API to show the approval status of all registered templates.
    """

    name = 'whatsapp:status'

    def get_parser(self, prog_name):
        parser = super(WhatsAppStatus, self).get_parser(prog_name)
        return parser

    def take_action(self, args):
        wa_config = get_whatsapp_config(self.app)
        url = get_api_url(wa_config)
        headers = get_api_headers(wa_config)
        del headers['Content-Type']

        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            templates = data.get('data', [])

            if not templates:
                print("No templates found on Facebook")
                return

            print("WhatsApp templates on Facebook:")
            print()
            print("  %-30s %-10s %-15s %s" % ("NAME", "LANG", "STATUS", "CATEGORY"))
            print("  " + "-" * 75)
            for t in templates:
                name = t.get('name', 'N/A')
                status = t.get('status', 'N/A')
                language = t.get('language', 'N/A')
                category = t.get('category', 'N/A')
                marker = '*' if status == 'APPROVED' else ' '
                print("  %s %-30s %-10s %-15s %s" % (marker, name, language, status, category))

        except requests.exceptions.RequestException as e:
            print("Error checking status: %s" % e)
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_data = e.response.json()
                    print("Details: %s" % error_data)
                except Exception:
                    print("Response: %s" % e.response.text)


class WhatsAppDetails(Command):
    """
        Get details of a specific WhatsApp template from Facebook

        Queries the Facebook Graph API for a specific template by name.
    """

    name = 'whatsapp:details'

    def get_parser(self, prog_name):
        parser = super(WhatsAppDetails, self).get_parser(prog_name)
        parser.add_argument("name", help="Template name to look up on Facebook")
        return parser

    def take_action(self, args):
        wa_config = get_whatsapp_config(self.app)
        url = get_api_url(wa_config)
        headers = get_api_headers(wa_config)
        del headers['Content-Type']

        try:
            response = requests.get(url, headers=headers, params={"name": args.name})
            response.raise_for_status()
            data = response.json()
            templates = data.get('data', [])

            if not templates:
                print("Template '%s' not found on Facebook" % args.name)
                return

            for t in templates:
                print("Template: %s" % t.get('name'))
                print("  Status:   %s" % t.get('status'))
                print("  Language: %s" % t.get('language'))
                print("  Category: %s" % t.get('category'))
                components = t.get('components', [])
                if components:
                    print("  Components:")
                    for i, comp in enumerate(components):
                        print("    %d. Type: %s" % (i + 1, comp.get('type')))
                        if comp.get('text'):
                            print("       Text: %s" % comp.get('text'))
                        if comp.get('format'):
                            print("       Format: %s" % comp.get('format'))
                        if comp.get('example'):
                            print("       Example: %s" % comp.get('example'))
                print()

        except requests.exceptions.RequestException as e:
            print("Error getting template details: %s" % e)
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_data = e.response.json()
                    print("Details: %s" % error_data)
                except Exception:
                    print("Response: %s" % e.response.text)


class WhatsAppDelete(Command):
    """
        Delete a WhatsApp template from Facebook

        Removes a template by name from the Facebook Business Account.
    """

    name = 'whatsapp:delete'

    def get_parser(self, prog_name):
        parser = super(WhatsAppDelete, self).get_parser(prog_name)
        parser.add_argument("--dry-run", help="Show what would be done without making API calls", default=False, action="store_true")
        parser.add_argument("name", help="Template name to delete")
        return parser

    def take_action(self, args):
        wa_config = get_whatsapp_config(self.app)
        url = get_api_url(wa_config)
        headers = get_api_headers(wa_config)
        del headers['Content-Type']

        if args.dry_run:
            print("[DRY RUN] Would delete template '%s'" % args.name)
            print("[DRY RUN] DELETE %s?name=%s" % (url, args.name))
            return

        print("Deleting template '%s'..." % args.name)

        try:
            response = requests.delete(url, headers=headers, params={"name": args.name})
            response.raise_for_status()
            result = response.json()
            if result.get('success'):
                print("Template '%s' deleted successfully" % args.name)
            else:
                print("Unexpected response: %s" % result)
        except requests.exceptions.RequestException as e:
            print("Error deleting template: %s" % e)
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_data = e.response.json()
                    print("Details: %s" % error_data)
                except Exception:
                    print("Response: %s" % e.response.text)


register(WhatsAppListTemplates)
register(WhatsAppRegisterTemplate)
register(WhatsAppRegisterAll)
register(WhatsAppStatus)
register(WhatsAppDetails)
register(WhatsAppDelete)

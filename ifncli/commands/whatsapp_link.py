import os
from typing import Dict, List

import requests
from cliff.command import Command

from . import register
from .whatsapp import get_api_headers, get_api_url, get_whatsapp_config
from ..managers.messaging import AutoMessageCollection
from ..managers.whatsapp import (
    WhatsAppTemplateError,
    missing_approvals,
    next_time_too_close,
    read_binding,
    with_binding,
)
from ..platform import PlatformResources
from ..utils import read_yaml


def read_auto_message_settings(platform: PlatformResources, name: str, settings_file: str):
    """Read the settings of an auto message folder and the languages of its e-mail translations."""
    folder = platform.get_path().get_auto_messages_path(name)
    if not folder.exists():
        raise Exception("Automessage path '%s' doesnt exists" % folder)
    settings: Dict = read_yaml(os.path.join(folder, settings_file))
    translations_file = os.path.join(folder, 'translations.yaml')
    if os.path.isfile(translations_file):
        translations = read_yaml(translations_file)['translations']
    else:
        translations = settings.get('translations', [])
    return settings, [tr['lang'] for tr in translations]


def fetch_template_statuses(wa_config, template_name: str) -> Dict[str, str]:
    """Ask Meta for the state of a template in each of its languages."""
    response = requests.get(get_api_url(wa_config), headers=get_api_headers(wa_config),
                            params={"name": template_name, "fields": "name,language,status", "limit": 100})
    response.raise_for_status()
    return {t['language']: t['status'] for t in response.json().get('data', []) if t.get('name') == template_name}


def find_auto_message(client, settings: Dict):
    """Find the auto message of the settings on the platform, the way email:import-auto does."""
    wanted = {'type': settings['sendTo'], 'template': {'messageType': settings['messageType']}, 'studyKey': settings.get('studyKey')}
    return AutoMessageCollection(client.get_auto_messages()).find_same(wanted)


class WhatsAppLinkAutoMessage(Command):
    """
        Bind an auto message on the platform to its WhatsApp template (second step, after Meta approval)

        Reads the `whatsapp` section of auto_messages/<name>/settings.yaml, checks on Meta that the
        template is APPROVED in every language of the message, then saves the auto message with the
        binding. Only the binding changes: the message is read from the platform and saved back.
    """

    name = 'whatsapp:link-auto'

    def get_parser(self, prog_name):
        parser = super(WhatsAppLinkAutoMessage, self).get_parser(prog_name)
        parser.add_argument("--dry-run", help="Check everything and show the change without saving it", default=False, action="store_true")
        parser.add_argument("--unlink", help="Remove the WhatsApp binding of the auto message (e-mail only)", default=False, action="store_true")
        parser.add_argument("--languages", help="Comma-separated languages that must be approved (default: every translation of the message)", default=None)
        parser.add_argument("--margin", help="Refuse when the message is due within this many minutes (default 10)", type=int, default=10)
        parser.add_argument("--settings", help="Settings file name in the folder (default settings.yaml)", default="settings.yaml")
        parser.add_argument("name", help="Auto message folder under auto_messages (e.g. weekly_reminder)")
        return parser

    def take_action(self, args):
        platform: PlatformResources = self.app.appConfigManager.get_platform()
        settings, languages = read_auto_message_settings(platform, args.name, args.settings)
        if args.languages:
            languages = [lang.strip() for lang in args.languages.split(',') if lang.strip()]

        if args.unlink:
            template_name, params = "", {}
        else:
            template_name, params = read_binding(settings)
            self.check_approved(template_name, languages)

        client = self.app.appConfigManager.get_management_api()
        stored = find_auto_message(client, settings)
        if stored is None:
            raise WhatsAppTemplateError("Auto message '%s' not found on the platform: import it first with email:import-auto" % args.name)
        if next_time_too_close(stored['nextTime'], margin=args.margin * 60):
            raise WhatsAppTemplateError("The auto message is due within %d minutes (nextTime %s): try again after it has been sent" % (args.margin, stored['nextTime']))

        template = stored.get('template', {})
        print("Auto message %s (%s/%s)" % (stored.get('id'), stored.get('type'), template.get('messageType')))
        print("  now:   %s %s" % (template.get('whatsappTemplateName') or '(no WhatsApp)', template.get('whatsappParams') or ''))
        print("  after: %s %s" % (template_name or '(no WhatsApp)', params or ''))
        if args.dry_run:
            print("Dry run: nothing saved")
            return

        # The scheduler may have sent the message since it was read: saving the old copy would move
        # its next run back and send it again.
        current = find_auto_message(client, settings)
        if current is None or current.get('id') != stored.get('id') or current.get('nextTime') != stored.get('nextTime'):
            raise WhatsAppTemplateError("The auto message changed while it was being bound: nothing saved, run the command again")
        client.save_auto_message({'autoMessage': with_binding(stored, template_name, params)})

        saved = find_auto_message(client, settings).get('template', {})
        print("Saved: %s %s" % (saved.get('whatsappTemplateName') or '(no WhatsApp)', saved.get('whatsappParams') or ''))

    def check_approved(self, template_name: str, languages: List[str]):
        statuses = fetch_template_statuses(get_whatsapp_config(self.app), template_name)
        for lang in languages:
            print("  %-4s %s" % (lang, statuses.get(lang, "NOT FOUND")))
        missing = missing_approvals(statuses, languages)
        if missing:
            raise WhatsAppTemplateError("Template '%s' is not approved on Meta in: %s. Nothing saved; run it again once Meta has approved it (whatsapp:status)" % (
                template_name, ", ".join("%s (%s)" % item for item in missing)))


register(WhatsAppLinkAutoMessage)

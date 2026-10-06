import os
from typing import Dict, List

import requests
from cliff.command import Command

from . import register
from .whatsapp import get_api_headers, get_api_url, get_whatsapp_config
from ..api.messaging import SYSTEM_MESSAGE_TYPES
from ..managers.messaging import AutoMessageCollection
from ..managers.whatsapp import (
    WhatsAppTemplateError,
    bind,
    missing_approvals,
    next_time_too_close,
    read_binding,
    read_template_binding,
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


def check_approved(app, template_name: str, languages: List[str]):
    """Stop unless Meta reports the template APPROVED in every one of the languages."""
    statuses = fetch_template_statuses(get_whatsapp_config(app), template_name)
    for lang in languages:
        print("  %-4s %s" % (lang, statuses.get(lang, "NOT FOUND")))
    missing = missing_approvals(statuses, languages)
    if missing:
        raise WhatsAppTemplateError("Template '%s' is not approved on Meta in: %s. Nothing saved; run it again once Meta has approved it (whatsapp:status)" % (
            template_name, ", ".join("%s (%s)" % item for item in missing)))


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
        check_approved(self.app, template_name, languages)


def find_email_template(client, message_type: str, study_key: str):
    """Find the e-mail template of a message type and study on the platform, or None."""
    found = [template for template in client.get_all_templates().get('templates', []) or []
             if template.get('messageType') == message_type and (template.get('studyKey') or '') == study_key]
    if len(found) > 1:
        raise WhatsAppTemplateError("%d e-mail templates '%s' of study '%s' on the platform: nothing saved, there must be only one" % (
            len(found), message_type, study_key))
    return found[0] if found else None


def same_template(a: Dict, b: Dict) -> bool:
    """True when two reads of an e-mail template hold the same content, whatever the order of its translations."""
    def normalised(template):
        copy_ = dict(template)
        copy_['translations'] = sorted(template.get('translations', []) or [], key=lambda tr: tr.get('lang', ''))
        return copy_
    return normalised(a) == normalised(b)


class WhatsAppLinkTemplate(Command):
    """
        Bind a study e-mail template on the platform to its WhatsApp template (second step, after Meta approval)

        These are the templates of the messages that study rules queue for participants, imported with
        `email:import-template --study`. The binding is read from whatsapp.yaml in the e-mail template
        folder, keyed by message type; the command checks on Meta that the template is APPROVED in every
        language of the stored template, then saves the stored template with the binding. Auto messages
        are bound with whatsapp:link-auto.
    """

    name = 'whatsapp:link-template'

    def get_parser(self, prog_name):
        parser = super(WhatsAppLinkTemplate, self).get_parser(prog_name)
        parser.add_argument("--dry-run", help="Check everything and show the change without saving it", default=False, action="store_true")
        parser.add_argument("--unlink", help="Remove the WhatsApp binding of the template (e-mail only)", default=False, action="store_true")
        parser.add_argument("--languages", help="Comma-separated languages that must be approved (default: every translation of the stored template)", default=None)
        parser.add_argument("--email_template_folder", help="Folder holding whatsapp.yaml (by default 'email_templates' in resources directory)", default=None)
        parser.add_argument("--study_key", "--study", help="Study of the e-mail template", default=None)
        parser.add_argument("name", help="Message type of the e-mail template (e.g. study-reminder)")
        return parser

    def take_action(self, args):
        if args.name in SYSTEM_MESSAGE_TYPES:
            raise WhatsAppTemplateError("'%s' is a system message: it is sent by e-mail only (verification-code goes to WhatsApp through the user-management settings)" % args.name)
        if not args.study_key:
            raise WhatsAppTemplateError("--study is required: only the e-mail templates of a study can be bound")

        if args.unlink:
            template_name, params = "", {}
        else:
            template_name, params = read_template_binding(self.read_bindings(args.email_template_folder), args.name)

        client = self.app.appConfigManager.get_management_api()
        stored = find_email_template(client, args.name, args.study_key)
        if stored is None:
            raise WhatsAppTemplateError("E-mail template '%s' of study '%s' not found on the platform: import it first with email:import-template --study %s %s" % (
                args.name, args.study_key, args.study_key, args.name))

        if not args.unlink:
            languages = [tr.get('lang') for tr in stored.get('translations', []) or []]
            if not languages:
                raise WhatsAppTemplateError("The e-mail template '%s' of study '%s' has no translations: import it again with email:import-template" % (
                    args.name, args.study_key))
            if args.languages:
                languages = [lang.strip() for lang in args.languages.split(',') if lang.strip()]
            check_approved(self.app, template_name, languages)

        print("E-mail template %s (%s/%s)" % (stored.get('id'), args.study_key, args.name))
        print("  now:   %s %s" % (stored.get('whatsappTemplateName') or '(no WhatsApp)', stored.get('whatsappParams') or ''))
        print("  after: %s %s" % (template_name or '(no WhatsApp)', params or ''))
        if args.dry_run:
            print("Dry run: nothing saved")
            return

        # Saving sends the whole template back: if it was imported again since it was read, the old
        # copy would overwrite the new e-mail.
        current = find_email_template(client, args.name, args.study_key)
        if current is None or not same_template(current, stored):
            raise WhatsAppTemplateError("The e-mail template changed while it was being bound: nothing saved, run the command again")
        client.save_email_template(bind(stored, template_name, params))

        saved = find_email_template(client, args.name, args.study_key) or {}
        print("Saved: %s %s" % (saved.get('whatsappTemplateName') or '(no WhatsApp)', saved.get('whatsappParams') or ''))

    def read_bindings(self, folder):
        if folder is None:
            folder = self.app.appConfigManager.get_platform().get_path() / 'email_templates'
        path = os.path.join(folder, 'whatsapp.yaml')
        if not os.path.isfile(path):
            raise WhatsAppTemplateError("No whatsapp.yaml in '%s': add it, keyed by message type like subjects.yaml" % folder)
        return read_yaml(path)


register(WhatsAppLinkAutoMessage)
register(WhatsAppLinkTemplate)

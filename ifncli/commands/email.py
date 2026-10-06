import os
from datetime import datetime, timedelta
from argparse import Namespace
from cliff.command import Command
from cliff.formatters.table import TableFormatter  
from typing import Dict, Union,Optional
from ..platform import PlatformResources
from . import register
from ..utils import check_keys, read_yaml,  read_content,readable_yaml
from ..api.messaging import SYSTEM_MESSAGE_TYPES, Message, MessageTranslation, MessageHeaders,AutoMessage
from ..managers.whatsapp import LOGIN_TOKEN_MESSAGE_TYPES, WhatsAppTemplateError, login_params_without_token, read_binding
from .whatsapp_link import check_approved
from ..managers.messaging import read_and_convert_html, find_template_file, TemplateLoader, AutoMessageCollection, parse_time_rules


class UpdateAutoMessage(Command):
    """
        Import auto reminder email
    """

    name = "email:import-auto"

    def get_parser(self, prog_name):
        parser = super(UpdateAutoMessage, self).get_parser(prog_name)
        self.formatter = TableFormatter()
        parser.add_argument("--dry-run", help="Just prepare template, dont update", default=False, action="store_true")
        parser.add_argument("--force", help="Force replacement of an eventual existing automessage with same type ", action="store_true")
        parser.add_argument("--at", help="Force nexttime ")
        parser.add_argument("--settings", help="Use alternate settings name in the folder (instead of settings.yaml) ")
        
        parser.add_argument("name", help="Name of the message to send. Search files in subdir of auto_email")

        self.formatter.add_argument_group(parser)
        return parser

    def take_action(self, args):

        dry_run = args.dry_run

        platform: PlatformResources = self.app.appConfigManager.get_platform()

        path = platform.get_path()

        email_folder_path = path.get_auto_messages_path(args.name)

        if not email_folder_path.exists():
            raise Exception("Automessage path '%s' doesnt exists" % (email_folder_path))
        
        default_language = platform.get('default_language', 'en')
        
        print("Email folder: %s" % email_folder_path)

        settings_file =  'settings.yaml'
        if args.settings is not None:
            settings_file = args.settings

        email_config:Dict = read_yaml(os.path.join(email_folder_path, settings_file))

        if "defaultLanguage" in email_config:
            default_language = email_config["defaultLanguage"]

        print("Default language %s " % default_language)

        email = Message(email_config["messageType"], default_language,  )

        if 'headerOverrides' in email_config:
            headers = MessageHeaders()
            headers.fromDict(email_config['headerOverrides'])
            email.setHeaders(headers)

        layout_path = None
        if 'layout' in email_config:
            layout_path = email_folder_path / email_config['layout']
        
        templateLoader = TemplateLoader(layout_path, platform)

        translations_file = os.path.join(email_folder_path, 'translations.yaml')
        
        
        if os.path.isfile(translations_file):
            tr_config = read_yaml(translations_file)
            translations_config = tr_config['translations']
            if 'translations' in email_config:
                print("Warning: 'translations' exists in settings and in translations.yaml. The translations.yaml is used in place of the provided in settings.yaml")
        else:
            translations_config = email_config['translations']
            
        for tr in translations_config:
            trans = MessageTranslation(tr['lang'], tr['subject'])
            template_file = os.path.join(email_folder_path, tr['templateFile'])
            
            templateDef = templateLoader.load(template_file, tr['lang'])
            
            trans.setTemplate(templateDef)

            email.addTranslation(trans)

        studyKey = email_config.get("studyKey")

        if args.at is not None:
            nextTime = datetime.fromisoformat(args.at)
        else:
            nextTime = parse_time_rules(email_config["nextTime"])
        
        if nextTime < datetime.now():
                raise Exception("Nexttime (%s) is in the past, to force nextime use --at " % (str(nextTime)))

        nextTime = int(nextTime.timestamp())

        if 'untilTime' in email_config:
            untilTime = parse_time_rules(email_config["untilTime"])
            untilTime = int(untilTime.timestamp())
        else:
            untilTime = None

        print("nextTime", nextTime, datetime.fromtimestamp(nextTime).isoformat())
        if untilTime is not None:
            print("untilTime", untilTime, datetime.fromtimestamp(untilTime).isoformat())
        else:
            print("No untilTime set")

        autoMessage = AutoMessage(email_config["sendTo"], studyKey=studyKey, nextTime=nextTime,  period=email_config["period"] )
        if "label" in email_config:
            autoMessage.setLabel(email_config['label'])

        if untilTime is not None:
            autoMessage.setUntilTime(untilTime)

        autoMessage.setTemplate(email)

        if 'condition' in email_config:
            autoMessage.setCondition(email_config['condition'])
        
        client = self.app.appConfigManager.get_management_api()
        existing_auto_messages = AutoMessageCollection(client.get_auto_messages())
        
        if existing_auto_messages.exists(autoMessage):
            if args.force: 
                prev = existing_auto_messages.find_same(autoMessage)
                autoMessage.setId(prev['id'])
            else:
                list = existing_auto_messages.as_list()
                print("Already existing")
                self.formatter.emit_list(['id','type','template','studyKey', 'label'], list, self.app.stdout, args)
                print("Add argument force to force the replacement of this message")
                return
        
        if dry_run:
            print("Dry run mode, only show the result")
            m = autoMessage.toAPI()
            print(m)
        else:
            client.save_auto_message({'autoMessage': autoMessage.toAPI()})


class ListAutoMessages(Command):
    """
      List Auto messages loaded in the system
    """
    name = 'email:list-auto'

    def get_parser(self, prog_name):
        parser = super(ListAutoMessages, self).get_parser(prog_name)
        parser.add_argument('--json', help="Export as json")
        return parser
        
    def take_action(self, args):
        client = self.app.appConfigManager.get_management_api()
        existing_auto_messages = AutoMessageCollection(client.get_auto_messages())
        
        def remove_template(trans):
            trans['templateDef'] = '<base64>'
            return trans
        
        for m in existing_auto_messages.messages.values():
            if not args.json:
                m['template']['translations'] = [remove_template(t) for t in m['template']['translations']]
            time = datetime.fromtimestamp(int(m['nextTime']))
            m['_nextTime'] = time.isoformat()
            print(readable_yaml(m))


class EmailTemplate(Command):
    """
        Import a custom email template

        Email templates are described here https://github.com/influenzanet/messaging-service/blob/master/docs/email-templates.md
    """

    name = 'email:import-template'

    def get_parser(self, prog_name):
        parser = super(EmailTemplate, self).get_parser(prog_name)
        parser.add_argument("--dry-run", help="Just prepare template, dont update", default=False, action="store_true")
        parser.add_argument("--email_template_folder", help="Email template folder (by default 'email_templates' in resources directory)", default=None, required=False)
        parser.add_argument("--study_key", "--study", help="Study associated to this email template", default=None, required=False)
        parser.add_argument("name", help="Name of the message template to import.")
        return parser

    def take_action(self, args):

        dry_run = args.dry_run

        platform: PlatformResources = self.app.appConfigManager.get_platform()

        email_template_folder = args.email_template_folder
        if email_template_folder is None:
            email_template_folder = platform.get_path() / 'email_templates'

        default_language = platform.get('default_language', 'en')

        print("Using '%s' path " % (email_template_folder))
        print("Default language : %s" % default_language)

        # Automatically extract languages:
        languages = []
        for language_code in os.listdir(email_template_folder):
            p = os.path.join(email_template_folder, language_code)
            if os.path.isdir(p):
                languages.append({"code": language_code, "path": p})

        try:
            headerOverrides = read_yaml(os.path.join(email_template_folder, 'header-overrides.yaml'))
        except:
            headerOverrides = None

        templateLoader = TemplateLoader(os.path.join(email_template_folder, 'layout.html'), platform)

        template = Message(args.name, default_language)

        if headerOverrides is not None:
            if args.name in headerOverrides:
                headers = MessageHeaders()
                headers.fromDict(headerOverrides[args.name])
                template.setHeaders(headers)

        if args.study_key is not None:
            template.setStudy(args.study_key)
        elif args.name not in SYSTEM_MESSAGE_TYPES:
            raise Exception(f"{args.name} is not a system message --study_key argument is required")

        for lang in languages:
            translated_template = find_template_file(args.name, lang["path"])
            subject_lines = read_yaml(os.path.join(lang["path"], 'subjects.yaml'))

            tpl_content = templateLoader.load(translated_template, lang['code'])

            trans = MessageTranslation(lang['code'], subject_lines[args.name] )
            trans.setTemplate(tpl_content)

            template.addTranslation(trans)

        if dry_run:
            print("dry-run mode, template %s" % args.name)
        else:
            client = self.app.appConfigManager.get_management_api()
            r = client.save_email_template(template.toAPI())
            print('saved templates for: ' + args.name)

class EmailTemplates(Command):
    """
        Import email templates

        Email templates are described here https://github.com/influenzanet/messaging-service/blob/master/docs/email-templates.md
    """
    
    name = 'email:import-templates'

    def get_parser(self, prog_name):
        parser = super(EmailTemplates, self).get_parser(prog_name)
        parser.add_argument("--dry-run", help="Just prepare template, dont update", default=False, action="store_true")
        parser.add_argument("--email_template_folder", help="Email template folder (by default 'email_templates' in resources directory)", default=None, required=False)
        return parser
        
    def take_action(self, args):

        for m_type in SYSTEM_MESSAGE_TYPES:
            email_template_cmd = EmailTemplate(self.app, self.app_args)
            args_ = Namespace(**args.__dict__, name=m_type, study_key=None)
            email_template_cmd.take_action(args_)

class SendCustom(Command):
    """ Send a custom email message

        Expect a folder with a settings.yaml file
    """

    name = "email:send-custom"

    def get_parser(self, prog_name):
        parser = super(SendCustom, self).get_parser(prog_name)
        parser.add_argument("--email_folder", help="path to the custom email folder", default=os.path.join('resources', 'custom_email'))
        parser.add_argument("--study_key", help="to send only to participants of a with this study key", default=None)
        parser.add_argument("--ignore-weekday", help="send to every user now, not only to those whose weekly day is today", default=False, action="store_true")
        parser.add_argument("--dry-run", help="check everything and show what would be sent, without sending", default=False, action="store_true")
        return parser
        
    def take_action(self, args):

        client = self.app.appConfigManager.get_management_api()

        study_key = args.study_key
        email_folder_path = args.email_folder

        print(study_key, email_folder_path)

        email_config = read_yaml(
            os.path.join(email_folder_path, 'settings.yaml')
        )

        message = Message(email_config["messageType"], email_config["defaultLanguage"])

        for tr in email_config['translations']:
           trans = MessageTranslation(tr['lang'], tr['subject'])
           trans.setTemplate(read_and_convert_html(os.path.join(email_folder_path, tr['templateFile'])))
           message.addTranslation(trans)

        template = message.toAPI()
        if "whatsapp" in email_config:
            template = with_whatsapp_binding(self.app, email_config, template)

        condition = email_config.get("condition")
        if args.dry_run:
            print("Dry run, nothing sent:")
            print("  message:   %s, languages %s" % (email_config["messageType"], [tr['lang'] for tr in email_config['translations']]))
            print("  to:        %s" % ("participants of %s, condition %s" % (study_key, condition or {"dtype": "num", "num": 1}) if study_key else "all users"))
            print("  WhatsApp:  %s %s" % (template.get("whatsappTemplateName", "(none)"), template.get("whatsappParams", "")))
            print("  ignore weekday: %s" % args.ignore_weekday)
            return
        if study_key is not None:
            if condition is None:
                condition = {"dtype": "num", "num": 1}
            client.send_message_to_study_participants(study_key, condition, template, ignore_weekday=args.ignore_weekday)
        else:
            client.send_message_to_all_users(template, ignore_weekday=args.ignore_weekday)


def with_whatsapp_binding(app, email_config: Dict, template: Dict) -> Dict:
    """
        Return the message to send with the WhatsApp template named in the `whatsapp` section of the
        settings, once Meta reports it APPROVED in every language of the message. The platform then
        sends it on WhatsApp to the users who chose that channel, as it does for auto messages.
    """
    template_name, params = read_binding(email_config)
    wrong = login_params_without_token(email_config["messageType"], params)
    if wrong:
        raise WhatsAppTemplateError("%s use loginToken/loginUrl, which the platform only provides for %s messages: the WhatsApp send of a '%s' would be dropped" % (
            ", ".join(wrong), " and ".join(LOGIN_TOKEN_MESSAGE_TYPES), email_config["messageType"]))
    print("Meta approval of WhatsApp template '%s':" % template_name)
    check_approved(app, template_name, [tr['lang'] for tr in email_config['translations']])
    return {**template, "whatsappTemplateName": template_name, "whatsappParams": params}

register(EmailTemplate)
register(EmailTemplates)
register(UpdateAutoMessage)
register(ListAutoMessages)
register(SendCustom)
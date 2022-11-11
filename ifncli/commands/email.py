import os
from datetime import datetime
from cliff.command import Command

from ..platform import PlatformResources
from . import register

from ..utils import check_keys, read_yaml,  read_content
from ..api.messaging import auto_message_types, Message, MessageTranslation, MessageHeaders

from ..managers.messaging import read_and_convert_html, find_template_file, read_and_encode_template

class EmailAutoReminder(Command):
    """
        Import auto reminder email
    """

    name = "email:import-auto"

    def get_parser(self, prog_name):
        parser = super(EmailAutoReminder, self).get_parser(prog_name)
       
        parser.add_argument("--dry-run", help="Just prepare template, dont update", default=False, action="store_true")
        parser.add_argument("--email_folder", help="path to the email folder containing template and config", default=None)
        parser.add_argument("--ignore_existing", 
            help="If set to true, existing auto message will be ignored and a new one will be created. By default (false), existing auto message with same type, study key and message type will be replaced ", 
            default=False
            )
        return parser

    def take_action(self, args):

        platform: PlatformResources = self.app.get_platform()

        email_folder_path = args.email_folder
        if email_folder_path is None:
            email_folder_path = platform.get_path() / 'auto_reminder_email'
        
        default_language = platform.get('default_language', 'en')
        
        print("Email folder: %s" % email_folder_path)
        ignore_existing = args.ignore_existing

        email_config = read_yaml(os.path.join(email_folder_path, 'settings.yaml'))

        if "defaultLanguage" in email_config:
            default_language = email_config["defaultLanguage"]

        print("Default language %s " % default_language)
        
        email = {
            "messageType": email_config["messageType"],
            "defaultLanguage": default_language,
            "translations": []
        }

        for tr in email_config['translations']:
            email['translations'].append({
                'lang': tr['lang'],
                'subject': tr['subject'],
                'templateDef': read_and_convert_html(os.path.join(email_folder_path, tr['templateFile']))
            })

        auto_message = {
            "autoMessage": {
                "type": email_config["sendTo"],
                "studyKey": email_config["studyKey"],
                "nextTime": int(datetime.strptime(email_config["nextTime"], "%Y-%m-%d-%H:%M:%S").timestamp()),
                "period": email_config["period"],
                "template": email
            }
        }

        if "studyKey" in email_config.keys() and email_config["studyKey"] != "":
            condition = {
                "dtype": "num",
                "num": 1
            }
            auto_message["autoMessage"]["condition"] = condition

        client = self.app.get_management_api()
        existing_auto_messages = client.get_auto_messages()
        print(existing_auto_messages)

        id = ''
        if not ignore_existing and 'autoMessages' in existing_auto_messages.keys():
            for m in existing_auto_messages['autoMessages']:
                if auto_message['autoMessage']['type'] == m['type'] and  auto_message['autoMessage']['template']['messageType'] == m['template']['messageType']:
                    if auto_message['autoMessage']['studyKey'] != "":
                        if 'studyKey' in m.keys() and auto_message['autoMessage']['studyKey'] == m['studyKey']:
                            id = m['id']
                            break
                    else:
                        id = m['id']
                        break
        auto_message['autoMessage']['id'] = id
        client.save_auto_message(auto_message)


class EmailTemplate(Command):
    """
        Import email templates

        Email templates are described here https://github.com/influenzanet/messaging-service/blob/master/docs/email-templates.md
    """
    
    name = 'email:import-templates'

    def get_parser(self, prog_name):
        parser = super(EmailTemplate, self).get_parser(prog_name)
        parser.add_argument("--dry-run", help="Just prepare template, dont update", default=False, action="store_true")
        parser.add_argument("--email_template_folder", help="Email template folder (by default 'email_templates' in resources directory)", default=None, required=False)
        return parser
        
    def take_action(self, args):

        dry_run = args.dry_run

        platform: PlatformResources = self.app.get_platform()

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

        layout = read_content(os.path.join(email_template_folder, 'layout.html'), default=None)
        if layout is not None:
            print("Using layout")

        template_vars = platform.get_vars()
        
        if 'web_app_url' in template_vars:
            url:str = template_vars.get('web_app_url')
            if url.endswith('/'): # Remove ending slash 
                url = url[:-1] 

        for m_type in auto_message_types:
            
            template = Message(m_type, default_language)

            if headerOverrides is not None:
                if m_type in headerOverrides:
                    headers = MessageHeaders()
                    headers.fromDict(headerOverrides[m_type])
                    template.setHeaders(headers)

            for lang in languages:
                translated_template = find_template_file(m_type, lang["path"])
                subject_lines = read_yaml(os.path.join(lang["path"], 'subjects.yaml'))

                try:
                    check_keys(subject_lines, auto_message_types, True)
                except KeyError as e:
                    raise Exception("Invalid %s/subject.yaml : %s " % (lang['code'], str(e)) )

                data = template_vars.copy()
                data['language'] = lang['code'] 

                tpl_content = read_and_encode_template(translated_template, layout=layout, vars=data)
            
                trans = MessageTranslation(lang['code'], subject_lines[m_type] )
                trans.setTemplate(tpl_content)
                
                template.addTranslation(trans)

            if dry_run:
                print("dry-run mode, template %s" % m_type)
            else:
                client = self.app.get_management_api()
                r = client.save_email_template(template.toAPI())
                print('saved templates for: ' + m_type)


class SendCustom(Command):
    """ Send a custom email message

        Expect a folder with a settings.yaml file
    """

    name = "email:send-custom"

    def get_parser(self, prog_name):
        parser = super(SendCustom, self).get_parser(prog_name)
        parser.add_argument("--email_folder", help="path to the custom email folder", default=os.path.join('resources', 'custom_email'))
        parser.add_argument("--study_key", help="to send only to participants of a with this study key", default=None)
        return parser
        
    def take_action(self, args):

        client = self.app.get_management_api()

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

        condition = email_config.get("condition")
        if study_key is not None:
            if condition is None:
                condition = {"dtype": "num", "num": 1}
            client.send_message_to_study_participants(study_key, condition, message.toAPI())
        else:
            client.send_message_to_all_users(message.toAPI())

register(EmailTemplate)
register(EmailAutoReminder)
register(SendCustom)
import os
import json
import base64

from cliff.command import Command
from . import register

from ifncli.utils import read_yaml, read_json, read_content, write_content

########  PARAMETERS #############

default_language = 'en'

default_email_template_folder = 'resources/email_templates'
##################################

########  PARAMETERS #############
message_types = [
    'registration',
    'invitation',
    'verify-email',
    'verification-code',
    'password-reset',
    'password-changed',
    'account-id-changed',  # email address changed
    'account-deleted'
]

def find_template_file(m_type, folder_with_templates):
    found = False
    for ext in ['','.html','.htm','.txt']:
        file = os.path.join(folder_with_templates, m_type + ext)
        if os.path.exists(file):
            found = True
            break
    if not found:
        raise ValueError("no template file found to message type: " + m_type)
    return file

def read_and_convert_html(path, vars=None, layout=None):
    content = open(path, 'r', encoding='UTF-8').read()

    built = False
    if vars is not None:
        built = True
        for name, value in vars.items():
            var = '{=' + name + '=}'
            content = content.replace(var, value)

    if layout is not None:
        content = layout.replace('{=main_content=}', content)
        built = True

    if built:
        write_content(path + '.built', content)

    return base64.b64encode(content.encode()).decode()

def read_and_encode_template(path, vars=None, layout=None):
    return read_and_convert_html(path, vars=vars, layout=layout)

class EmailAutoReminder(Command):
    """
        Import auto reminder email
    """

    name = "email:import-auto"

    def get_parser(self, prog_name):
        parser = super(EmailAutoReminder, self).get_parser(prog_name)
       
        parser.add_argument(
            "--email_folder", help="path to the email folder containing template and config", default=os.path.join('resources', 'auto_reminder_email'))
        parser.add_argument(
            "--ignore_existing", help="If set to true, existing auto message will be ignored and a new one will be created. By default (false), existing auto message with same type, study key and message type will be replaced ", default=False)
        return parser

    def take_action(self, args):

        email_folder_path = args.email_folder
        ignore_existing = args.ignore_existing

        email_config = read_yaml(os.path.join(email_folder_path, 'settings.yaml'))

        email = {
            "messageType": email_config["messageType"],
            "defaultLanguage": email_config["defaultLanguage"],
            "translations": []
        }

        for tr in email_config['translations']:
            email['translations'].append({
                'lang': tr['lang'],
                'subject': tr['subject'],
                'templateDef': read_and_convert_html(
                    os.path.join(email_folder_path, tr['templateFile']))
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
        parser.add_argument("--default_language", help="Default language", default='en', required=False)
        parser.add_argument("--email_template_folder", help="Email template folder", default=default_email_template_folder, required=False)
        return parser
        
    def take_action(self, args):

        dry_run = args.dry_run

        default_language = args.default_language
        email_template_folder = args.email_template_folder

        client = self.app.get_management_api()
        
        # Automatically extract languages:
        languages = [{"code": d, "path": os.path.join(email_template_folder, d)} for d in os.listdir(
            email_template_folder) if os.path.isdir(os.path.join(email_template_folder, d))]

        try:
            headerOverrides = read_yaml(os.path.join(email_template_folder, 'header-overrides.yaml'))
        except:
            headerOverrides = None

        layout = read_content(os.path.join(email_template_folder, 'layout.html'), default=None)
        if layout is not None:
            print("Using layout")

        template_vars = self.app.get_configs('email_vars', must_exist=False)
        
        for m_type in message_types:
            template_def = {
                'messageType': m_type,
                'defaultLanguage': default_language,
                'translations': [],
            }

            if headerOverrides is not None:
                currentHeaderOverrides = headerOverrides[m_type]
                if  currentHeaderOverrides is not None:
                    template_def['headerOverrides'] = currentHeaderOverrides

            for lang in languages:
                translated_template = find_template_file(m_type, lang["path"])
                subject_lines = read_yaml(os.path.join(lang["path"], 'subjects.yaml'))

                tpl_content = read_and_encode_template(translated_template, layout=layout, vars=template_vars)
                
                template_def["translations"].append(
                    {
                        "lang": lang["code"],
                        "subject": subject_lines[m_type],
                        "templateDef": tpl_content
                    }
                )

            if dry_run:
                print("dry-run mode, template %s" % m_type)
            else:
                r = client.save_email_template(template_def)
                print('saved templates for: ' + m_type)


class SendCustom(Command):
    """ Send a custom email message

        Expect a folder with a settings.yaml file
    """

    name = "email:send-custom"

    def get_parser(self, prog_name):
        parser = super(SendCustom, self).get_parser(prog_name)
        parser.add_argument(
                "--email_folder", help="path to the custom email folder", default=os.path.join('resources', 'custom_email'))
        parser.add_argument(
            "--to_study_participants", help="to send only to participants of a with this study key", default=None)
        return parser
        
    def take_action(self, args):

        client = self.app.get_management_api()

        study_key = args.to_study_participants
        email_folder_path = args.email_folder

        print(study_key, email_folder_path)

        email_config = read_yaml(
            os.path.join(email_folder_path, 'settings.yaml')
        )

        email = {
            "messageType": email_config["messageType"],
            "defaultLanguage": email_config["defaultLanguage"],
            "translations": []
        }

        for tr in email_config['translations']:
            email['translations'].append({
                'lang': tr['lang'],
                'subject': tr['subject'],
                'templateDef':  read_and_convert_html(
                    os.path.join(email_folder_path, tr['templateFile']))
            })

        if study_key is not None:
            condition = {
                "dtype": "num",
                "num": 1
            }
            client.send_message_to_study_participants(study_key, condition, email)
        else:
            client.send_message_to_all_users(email)

register(EmailTemplate)
register(EmailAutoReminder)
register(SendCustom)
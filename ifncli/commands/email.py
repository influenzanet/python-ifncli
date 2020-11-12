import os
import json
import base64

from cliff.command import Command
from . import register

from ifncli.utils import read_yaml, read_json


########  PARAMETERS #############
message_types = [
    'registration',
    'invitation',
    'verify-email',
    'verification-code',
    'password-reset',
    'password-changed',
    'account-id-changed',  # email address changed
    # 'weekly',
    'account-deleted'
]

default_language = 'en'

email_template_folder = 'resources/email_templates'
##################################


def find_template_file(m_type, folder_with_templates):
    c = [f for f in os.listdir(folder_with_templates)
         if f.split('.')[0] == m_type]
    if len(c) != 1:
        raise ValueError("no template file found to message type: " + m_type)
    return os.path.join(folder_with_templates, c[0])


def read_and_convert_html(path):
    content = open(path, 'r', encoding='UTF-8').read()
    return base64.b64encode(content.encode()).decode()

def read_and_endcode_template(path):
    return read_and_convert_html(path)

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

        Emai templates are described here https://github.com/influenzanet/messaging-service/blob/master/docs/email-templates.md
    """
    
    name = 'email:import-templates'

    def get_parser(self, prog_name):
        parser = super(EmailTemplate, self).get_parser(prog_name)
        return parser
        
    def take_action(self, args):
        client = self.app.get_management_api()

        # Automatically extract languages:
        languages = [{"code": d, "path": os.path.join(email_template_folder, d)} for d in os.listdir(
            email_template_folder) if os.path.isdir(os.path.join(email_template_folder, d))]

        for m_type in message_types:
            template_def = {
                'messageType': m_type,
                'defaultLanguage': default_language,
                'translations': []
            }

            for lang in languages:
                translated_template = find_template_file(m_type, lang["path"])
                subject_lines = read_yaml(os.path.join(lang["path"], 'subjects.yaml'))
                   
                template_def["translations"].append(
                    {
                        "lang": lang["code"],
                        "subject": subject_lines[m_type],
                        "templateDef": read_and_endcode_template(translated_template)
                    }
                )

            r = client.save_email_template(template_def)
            print('saved templates for: ' + m_type)

class SendCustom(Command):
    """ Send a custom email message

        Expect a folder with a settings.yaml file
        
    """

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
import os
from datetime import datetime, timedelta
from cliff.command import Command
from cliff.formatters.table import TableFormatter  
from typing import Dict, Union,Optional
from ..platform import PlatformResources
from . import register
from dateutil.relativedelta import relativedelta
from ..utils import check_keys, read_yaml,  read_content,readable_yaml
from ..api.messaging import SYSTEM_MESSAGE_TYPES, Message, MessageTranslation, MessageHeaders,AutoMessage

from ..managers.messaging import read_and_convert_html, find_template_file, read_and_encode_template

"""
        Load a Template html and wrap it with an optional layout and bind platform variables 
"""
class TemplateLoader:

    def __init__(self, path, platform:PlatformResources):
        
        self.layout = None
        # Check if global layout exists
        if path is None and not platform.template_layout is None:
               path = platform.template_layout
        
        if not path is None and path != "":
            self.layout = read_content(path, must_exist=True)
        
        if self.layout is None:
            print("Using layout in '%s'" % (path))
    
        template_vars = platform.get_vars()
        
        if 'web_app_url' in template_vars:
            url:str = template_vars.get('web_app_url')
            if url.endswith('/'): # Remove ending slash 
                url = url[:-1] 
        self.vars = template_vars

    def load(self, template_path, language:str)->str:
        data = self.vars.copy()
        data['language'] = language
        return read_and_encode_template(template_path, layout=self.layout, vars=data)

class AutoMessageCollection:

    def __init__(self, data):
        """
            Manage a collection of automessages
            param: data the result of ManagementAPI.get_auto_messages()
        """
        self.messages = {}
        if 'autoMessages' in data:
            for m in data['autoMessages']:
                key = self.get_key(m)
                self.messages[key] = m

    def get_key(self, m:Union[Dict, AutoMessage])->str:
        if isinstance(m, AutoMessage):
            m = m.toAPI()
        key = m['type'] + '/' + m['template']['messageType']
        studyKey = m.get('studyKey', None)
        if studyKey is not None and studyKey != "":
            key += '/' + m['studyKey']
        return key
    
    def find_same(self, m:Dict):
        key = self.get_key(m)
        return self.messages.get(key, None)

    def exists(self, m: Dict):
        key = self.get_key(m)
        return key in self.messages

    def as_list(self):
        data = []
        for m in self.messages.values():
            data.append( (m['id'], m['type'], m['template']['messageType'], m.get('studyKey', ''), m.get('label', '') ) )
        return data

def parse_next_time(time):
    if isinstance(time, dict):
        now = datetime.now().replace(second=0)
        if 'relative' in time and time['relative']:
            if 'hour' in time:
               r = relativedelta(hours=int(time['hour']))
               now = now + r
            if 'min' in time:
                r = relativedelta(minutes=int(time['min']))
                now = now + r
            if 'day' in time:
                r = relativedelta(days=int(time['day']))
                now = now + r
        else:
            if 'hour' in time:
                now = now.replace(hour=int(time['hour']))
            if 'min' in time:
                now = now.replace(minute=int(time['min']))
            if now < datetime.now():
                now = now + relativedelta(days=1)
    else:
        now = datetime.strptime(time, "%Y-%m-%d-%H:%M:%S")
    return int(now.timestamp())

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
        parser.add_argument("name", help="Name of the message to send. Search files in subdir of auto_email")

        self.formatter.add_argument_group(parser)
        return parser

    def take_action(self, args):

        dry_run = args.dry_run

        platform: PlatformResources = self.app.get_platform()

        path = platform.get_path()

        email_folder_path = path.get_auto_messages_path(args.name)

        if not email_folder_path.exists():
            raise Exception("Automessage path '%s' doesnt exists" % (email_folder_path))
        
        default_language = platform.get('default_language', 'en')
        
        print("Email folder: %s" % email_folder_path)

        email_config:Dict = read_yaml(os.path.join(email_folder_path, 'settings.yaml'))

        if "defaultLanguage" in email_config:
            default_language = email_config["defaultLanguage"]

        print("Default language %s " % default_language)

        email = Message(email_config["messageType"], default_language,  )

        layout_path = None
        if 'layout' in email_config:
            layout_path = email_folder_path / email_config['layout']
        
        templateLoader = TemplateLoader(layout_path, platform)

        for tr in email_config['translations']:
            trans = MessageTranslation(tr['lang'], tr['subject'])
            template_file = os.path.join(email_folder_path, tr['templateFile'])
            
            templateDef = templateLoader.load(template_file, tr['lang'])
            
            trans.setTemplate(templateDef)

            email.addTranslation(trans)

        studyKey = email_config["studyKey"]
        nextTime = parse_next_time(email_config["nextTime"])

        print("nextTime", nextTime, datetime.fromtimestamp(nextTime).isoformat())

        autoMessage = AutoMessage(email_config["sendTo"], studyKey=studyKey, nextTime=nextTime,  period=email_config["period"] )
        if "label" in email_config:
            autoMessage.setLabel(email_config['label'])

        autoMessage.setTemplate(email)
        
        client = self.app.get_management_api()
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
            print(autoMessage.toAPI())
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
        client = self.app.get_management_api()
        existing_auto_messages = AutoMessageCollection(client.get_auto_messages())
        
        def remove_template(trans):
            trans['templateDef'] = '<base64>'
            return trans
        
        for m in existing_auto_messages.messages.values():
            if not args.json:
                m['template']['translations'] = [  remove_template(t) for t in m['template']['translations']]
            time = datetime.fromtimestamp(int(m['nextTime']))
            m['_nextTime'] = time.isoformat()
        print(readable_yaml(m))
        


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

        templateLoader = TemplateLoader(os.path.join(email_template_folder, 'layout.html'), platform)

        for m_type in SYSTEM_MESSAGE_TYPES:
            
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
                    check_keys(subject_lines, SYSTEM_MESSAGE_TYPES, True)
                except KeyError as e:
                    raise Exception("Invalid %s/subject.yaml : %s " % (lang['code'], str(e)) )
                
                tpl_content = templateLoader.load(translated_template, lang['code'])
                
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
register(UpdateAutoMessage)
register(ListAutoMessages)
register(SendCustom)
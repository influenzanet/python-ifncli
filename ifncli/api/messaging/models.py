from typing import Dict
from .types import all_message_types

class MessageException(Exception):
    pass

class MessageTranslation:
    """
        Message translation
    """
    def __init__(self, lang: str, subject: str) -> None:
        self.lang = lang
        self.subject = subject
    
    def setTemplate(self, template: str):
        self.template = template

    def toAPI(self):
        return {
                'lang':self.lang,
                'subject': self.subject,
                'templateDef': self.template
        }

class MessageHeaders:
    """
        Custom headers for a message
    """

    FIELDS = [
            ('from', '_from'),
            ('sender', 'sender'),
            ('reply_to', 'reply_to'),
            ('no_reply_to', 'no_reply_to')
    ]

    def __init__(self):
        self._from = None
        self.sender = None
        self.reply_to = []
        self.no_reply_to = False

    def fromDict(self, d: Dict):
        for field in self.FIELDS:
            name, attr_name = field
            if name not in d:
                continue
            value = d[name]
            if isinstance(getattr(self, attr_name), list) and not isinstance(value, list):
                raise MessageException("Field '%s' must be a list" % name)
            if  isinstance(getattr(self, attr_name), bool):
                if isinstance(value, int):
                    value = value > 0
                if not isinstance(value, bool):
                    raise MessageException("Field '%s' must be a list" % name)
        
    def toAPI(self):
        data = {}
        
        for field in self.FIELDS:
            name, attr_name = field
            value = getattr(self, attr_name)
            if value is None:
                continue
            if isinstance(value, list) and len(value) == 0:
                continue
            data[name] = value
        return data


class Message:
    def __init__(self, messageType: str, defaultLanguage: str) -> None:
        if not messageType in all_message_types:
            raise Exception("Unknown type message type '%s'" % (messageType,))
        self.messageType = messageType
        self.defaultLanguage = defaultLanguage
        self.headerOverrides = None
        self.translations = []

    def addTranslation(self, trans: MessageTranslation):
        self.translations.append(trans)

    def setHeaders(self, headerOverrides:MessageHeaders):
        self.headerOverrides = headerOverrides

    def toAPI(self):

        tt = [ x.toAPI() for x in self.translations ]

        data = {
            "messageType": self.messageType,
            "defaultLanguage": self.defaultLanguage,
            "translations": tt,
        }

        if self.headerOverrides is not None:
            data['headerOverrides'] = self.headerOverrides

        return data





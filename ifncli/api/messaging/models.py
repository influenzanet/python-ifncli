from typing import Dict, Optional
from .types import *

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
        if not messageType in ALL_MESSAGE_TYPES:
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

class AutoMessage:

    def __init__(self, type: str, studyKey:Optional[str], period:int, nextTime: int):
        self.id:str = None
        
        if not type in AUTO_MESSAGE_TYPES:
            raise Exception("Invalid bulk message type '%s'" % (type))
        
        self.type:str = type
        
        self.studyKey:Optional[str] = studyKey
        self.period = period
        self.nextTime = nextTime
        self.template: Message = None
        self.condition = None
        self.label = None
        self.id = None
        if studyKey is not None and studyKey != "":
            self.condition =  {
                "dtype": "num",
                "num": 1
            }
    
    def setLabel(self, label:str):
        self.label = label

    def setId(self, id):
        self.id = id

    def setCondition(self, condition):
        self.condition = condition
    
    def setTemplate(self, msg:Message):
        self.template = msg

    def toAPI(self):
        d= {
            "type": self.type,
            "studyKey": self.studyKey,
            "nextTime": self.nextTime,
            "period": self.period,
            "template": self.template.toAPI()
        }
        if self.label is not None:
            d['label'] = self.label
        if self.condition is not None:
            d['condition'] = self.condition
        if self.id is not None:
            d['id'] = self.id
        return d



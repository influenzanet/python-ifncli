from typing import Dict, Union,Optional
from ...api.messaging import AutoMessage

class AutoMessageCollection:
    
    def __init__(self, data):
        """
            Manage a collection of automessages
            data: data the result of ManagementAPI.get_auto_messages()
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
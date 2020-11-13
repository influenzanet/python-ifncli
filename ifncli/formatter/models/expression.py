
KNOWN_EXPRESSION = {
    'IFTHEN': {
        'params': ['condition']
    },
    'ADD_NEW_SURVEY': {
        'params': ['surveyKey','validFrom','validUntil','category']
    },
    'responseHasKeysAny': {
        'params': ['item', 'response']
    },
    'checkEventType': {
        'params': ['type']
    },
    'hasStudyStatus': {
        'params': ['status']
    }
}

class Expression:
    
    def __init__(self, name, params=None):
        self.name = name
        if params is None:
            params = []
        self.params = params
        self._has_expression_param = False
        for p in params:
            if p.is_expression():
                self._has_expression_param = True
                break
    
    def is_expression(self):
        return True

    def has_expression_param(self):
        return self._has_expression_param

    def is_scalar(self):
        return False

    def param_name(self, index):
        if not self.name in KNOWN_EXPRESSION:
            return None
        action = KNOWN_EXPRESSION[self.name]
        if 'params' in action:
            params_list = action['params']
            if(index > len(params_list)-1):
                return None
            return params_list[index]

class Scalar:

    def __init__(self, type, value):
        self.type = type
        self.value = value

    def is_expression(self):
        return False

    def is_scalar(self):
        return True

    def __str__(self):
        if self.type == "str":
            return '"' + self.value + '"'
        return str(self.value)


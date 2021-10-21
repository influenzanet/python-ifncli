from collections import OrderedDict

SINGLE_CHOICE_TYPE = 'single_choice'
MULTIPLE_CHOICE_TYPE = 'multiple_choice'
MATRIX_CHOICE_TYPE = 'matrix'
TEXT_TYPE = 'text'
NUMERIC_TYPE = 'numeric'
DATE_TYPE = 'date'

class StandardParserException(Exception):
    pass

class StandardSurvey:

    def __init__(self, name):
        self.name = name
        self.questions = OrderedDict()
        self.comment = None

    def add_question(self, question):
        n = question.data_name
        if n in self.questions:
            raise StandardParserException("Question with data_name '%s' is already defined" % (n))
        self.questions[n] = question

    def __repr__(self):
        qq = []
        for q in self.questions:
            qq.append(q.__repr__())
        return '<Survey %s %s>' % (self.name, ",".join(qq), )

class StandardQuestion:
    
    def __init__(self, data_name, type, title):
        self.data_name = data_name
        self.data_type = None
        self.type = type
        self.mandatory = False
        self.title = title
        self.comment = None
        self.data_type = None
        self.responses = StandardResponseList()
        self.rows = StandardMatrixDimensionList()
        self.columns = StandardMatrixDimensionList()
        self.order = 0
        self.active = True
        self.plateforms = []
        self.target = None
    
    def add_response(self, response):
        self.responses[response.key] = response
    
    def set_rows(self, rows):
        self.rows = rows
    
    def set_columns(self, columns):
        self.columns = columns

class StandardResponseList(OrderedDict):

    def find_by(self, name, value):
        for k, r in self.items():
            if hasattr(r, name):
                if getattr(r, name) == value:
                    return r
        return None

class StandardResponse:
      """
        key: local key in the spec
        text: label of the response
        order: order in the spec
        value: 
      """
      
      def __init__(self, key, text, order):
          self.key = key
          self.text = text
          self.order = order
          self.value = None
          self.comment = None
          self.active = True
          self.extra = None
          self.added_at = None
          self.removed_at = None
          self.plateforms = []


class StandardMatrixDimension:
    def __init__(self, text, key, value, order):
        """
            text: label
            key: key of the element in the definition (db id or json key dict)
            value: value to be used in the model
            order: order of the element in the definition
        """
        self.text = text
        self.key = key
        self.value = value
        self.order = order
        self.added_at = None
        self.removed_at = None

    def __repr__(self):
        return "[%s](%s)#%d" % (self.value, self.text, self.order)

class StandardMatrixDimensionList(OrderedDict):
    
    def find_by(self, name, value):
        for k, r in self.items():
            if hasattr(r, name):
                if getattr(r, name) == value:
                    return r
        return None


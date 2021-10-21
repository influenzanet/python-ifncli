
class RGRole:
    """
    Roles of ResponseGroup
    """
    def __init__(self, name, data:bool) -> None:
        self.name = name
        self.data = data

    def __eq__(self, value):
        if isinstance(value, str):
            return value == self.name
        if isinstance(value, self.__class__):
            return self.name == value.name
        return False

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return '<%s,%s>' % (self.__class__.name, self.name)

    def to_readable(self, ctx):
        return self.name

class RGROLES:
    # Display Roles
    TEXT = RGRole('text', False)
    MARKDOWN = RGRole('markdown', False)
    
    # Data Input Roles
    SINGLE = RGRole('singleChoiceGroup', True)
    DROPDOWN = RGRole('dropDownGroup', True)
    MATRIX = RGRole('matrix', True)
    MULTIPLE = RGRole('multipleChoiceGroup', True)
    DATE = RGRole('dateInput', True)
    INPUT = RGRole('input', True)
    MULTIPLELINE=RGRole('multilineTextInput', True)
    NUMBER = RGRole('numberInput', True)
    SLIDER_NUM = RGRole('sliderNumeric', True)
    SLIDER_RANGE = RGRole('sliderNumericRange', True)
    SLIDER_CAT = RGRole('sliderCategorical', True)
    LIKERT = RGRole('likert', True)
    LIKERTGROUP = RGRole('likertGroup', True)
    BIPOLARLIKERT = RGRole('responsiveBipolarLikertScaleArray', True)
    SINGLE_ARRAY = RGRole('responsiveSingleChoiceArray', True)

"""
    Known ResponseGroup Roles
"""
RG_ROLES = [v for k,v in RGROLES.__dict__.items() if isinstance(v,RGRole)]

"""
    Roles for Response Groups holding Data input
"""
RG_ROLES_DATA = [v for v in RG_ROLES if v.data]

"""
    Dictionnary associating role name (provided in json) and internal class
"""
RG_ROLES_DICT = zip( [v.name, v ] for v in RG_ROLES)


class SurveyItem:
    
    def __init__(self, key, id=None, version=None  ):
        self.key = key
        self.id = id
        self.version = version

    def get_readable_label(self, name):
        if self.id is not None:
            k = "key=%s, id=%s" % (self.key, self.id)
        else:
            k = str(self.key)
        label = "%s<key=%s>" % (name, k, )
        if self.version is not None:
            label += "[%d]" % (self.version)
        return label
    
class SurveySingleItem(SurveyItem):

    def __init__(self, key, components, validations, type, id=None, version=None):
        super(SurveySingleItem, self).__init__(key=key, id=id, version=version)
        self.components = components
        self.validations = validations
        self.type = type

    def to_readable(self):
        o = {
            '_ref': self.get_readable_label('SingleItem'),
        }
        if self.type is not None:
            o['type'] = self.type
        o['components'] = self.components
        if self.validations is not None:
            o['validations'] = self.validations
        return o

    def __str__(self):
        return '<SurveySingleItem key=%s, type=%s>' % (self.key, self.type)

class SurveyGroupItem(SurveyItem):

    def __init__(self, key, items, selection, id=None, version=None):
        super(SurveyGroupItem, self).__init__(key=key, id=id, version=version)
        self.items = items
        self.selection = selection

    def to_readable(self):
        return {
            '_ref': self.get_readable_label('GroupsItem'),
            'items': self.items,
            'selection': self.selection
        }

    def __str__(self):
        return '<SurveyGroupItem %s, %s>' % (self.key, str(self.items))


class SurveyItemComponent:
    
    def __init__(self, key, role ):
        self.key = key
        self.role = role

    def get_readable_label(self, name):
        if self.key is not None and self.key != '':
            k = "key=%s, role=%s" % (self.key, self.role)
        else:
            k = str(self.role)
        label = "%s<role=%s>" % (name, k, )
        return label

    def get_common_fields(self, o):
        for a in ['content', 'description', 'disabled', 'displayCondition','style']:
            v = getattr(self, a, None)
            if v is not None:
                o[a] = v

    def to_readable(self):
        o = {
            '_ref': self.get_readable_label('DisplayComponent')
        }
        self.get_common_fields(o)
        return o

       
class SurveyItemGroupComponent(SurveyItemComponent):
    
    def __init__(self, key, role, items, order):
        super(SurveyItemGroupComponent, self).__init__(key=key, role=role)
        self.items = items
        self.order = order
        
    def to_readable(self):
        o = {
            '_ref': self.get_readable_label('GroupComponent'),
            'items': self.items,
            'order': self.order
        }
        self.get_common_fields(o)
        return o

class SurveyItemResponseComponent(SurveyItemComponent):
    
    def __init__(self, key, role, dtype, props):
        super(SurveyItemResponseComponent, self).__init__(key=key, role=role)
        self.dtype = dtype
        self.props = props

    def to_readable(self):
        o = {
            '_ref': self.get_readable_label('ResponseComponent'),
            'dtype': self.dtype,
            'properties': self.props
        }
        self.get_common_fields(o)
        return o

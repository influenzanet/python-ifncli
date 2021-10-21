from typing import List, Optional

from ifncli.formatter.models.responses import RG_ROLES, RG_ROLES_DATA
from .dictionnary import ItemDictionnary, OptionDictionnary

TYPE_PAGE_BREAK = 'pageBreak'
ROLE_RESPONSE_GROUP = 'responseGroup'
ROLE_TEXT = 'text'
DISPLAY_ROLES = [ROLE_TEXT, 'label']
TYPE_SURVEY_END = 'surveyEnd'


# Response group roles

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

    def get_dictionnary(self)-> Optional[ItemDictionnary]:
        """
        Get flat list of data elements
        """
        return None

    def is_group(self):
        """
        is Item a group Item (with sub items)
        """
        return False
    
    def flatten(self):
        yield self

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

    def get_dictionnary(self)-> Optional[ItemDictionnary]:
        rg = self.get_response_group()
        
        if self.type == TYPE_SURVEY_END:
            return None

        if rg is None:
            return None
        
        if len(rg) > 1:
            raise Exception("Several response group for %s "  % str(self) )
        
        if len(rg) == 0:
                print("Warning no response group for %s" % str(self) )
                
        if len(rg) == 1:
                rg = rg[0]
                # print("ResponseGroup of %s %s" %  (self.key, type(rg)))
                for rg_item in rg.items:
                    role = rg_item.role
                    if not role in RG_ROLES:
                        print("Warning unknown role %s" % (role, ))
                    if not role in RG_ROLES_DATA:
                        continue
                    # Find the component item with options
                    oo = None
                    if rg_item.is_group():
                        # If it's a group let's find options
                        oo = self._get_response_options(rg_item)
                    d = ItemDictionnary(self.key, role, oo, self)
                    return d
        return None  
            
    def _get_response_options(self, responseGroup, root_key=None)->List[OptionDictionnary]:
        key = responseGroup.key
        if root_key is not None:
            key = root_key + '.' + responseGroup.key
        options = []
        for item in responseGroup.items:
            if item.role in DISPLAY_ROLES:
                continue
            if item.is_group():
                options.extend( self._get_response_options(item, key) )
            else:
                options.append(
                    OptionDictionnary(key + '.' + item.key, item.role, item.key)
                )
        return options    

    def get_response_group(self):
        if self.components is None:
            return None

        if self.type == TYPE_PAGE_BREAK:
            # No response for page break
            return None

        return self.components.items_by_role(ROLE_RESPONSE_GROUP)
        

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

    def get_dictionnary(self):
        d = []
        for item in self.items:
            item_dict = item.get_dictionnary()
            if item_dict is None:
                continue
            if isinstance(item_dict, list):
                d.extend(item_dict)
            else:
                d.append(item_dict)
        return d

    def __str__(self):
        return '<SurveyGroupItem %s, %s>' % (self.key, str(self.items))

    def is_group(self):
        """
        is Item a group Item (with sub items)
        """
        return True

    def flatten(self):
        yield self
        for item in self.items:
            yield from item.flatten()

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
        for a in ['content', 'description', 'disabled', 'displayCondition','style', 'properties']:
            v = getattr(self, a, None)
            if v is not None:
                o[a] = v

    def to_readable(self):
        o = {
            '_ref': self.get_readable_label('DisplayComponent')
        }
        self.get_common_fields(o)
        return o

    def is_group(self):
        return False

    def is_response(self):
        return False

    def is_base(self):
        return True

    def get_type(self):
        return 'base'
       
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

    def items_by_role(self, role):
        if self.items is None:
            return None
        ii = []
        for item in self.items:
            if item.role == role:
                ii.append(item)
        return ii

    def items_by_roles(self):
        ## Group items by roles
        if self.items is None:
            return None
        roles = {}
        for item in self.items:
            r = item.role
            if not r in roles:
                roles[r] = []
            roles[r].append(item)
        return roles 
    
    def is_group(self):
        return True

    def is_response(self):
        return False

    def is_base(self):
        return False

    def get_type(self):
        return 'group'

class SurveyItemResponseComponent(SurveyItemComponent):
    
    def __init__(self, key, role, dtype):
        super(SurveyItemResponseComponent, self).__init__(key=key, role=role)
        self.dtype = dtype
    
    def to_readable(self):
        o = {
            '_ref': self.get_readable_label('ResponseComponent'),
            'dtype': self.dtype,
        }
        self.get_common_fields(o)
        return o

    def is_group(self):
        return False

    def is_response(self):
        return True

    def is_base(self):
        return False

    def get_type(self):
        return 'response'

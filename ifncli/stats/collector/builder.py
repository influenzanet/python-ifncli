from collections import OrderedDict
from typing import List
from .collector import Collector,FieldCountCollector
from .fields import SummaryCollector, CategoricalCollector

KnownCollectors = {
    'counts': FieldCountCollector,
    'summary': SummaryCollector,
    'category': CategoricalCollector,
}

class CollectorBuilder:

    def create(self, collector_type, name, field=None):
            collector_class = KnownCollectors.get(collector_type, None)
            if collector_class is None:
                return None
            need_field = getattr(collector_class, 'need_field')
            if need_field and field is None:
                raise ValueError("'%s' collector needs field name after :" % (collector_type))
            if name is None:
                if need_field:
                    name = "%s_%s" % (collector_type, field)
                else:
                    name = getattr(collector_class, 'default_name', None)
                    if name is None:
                        raise ValueError("'%s' cannot instanciate without a name, class is missing 'default_name'" % (collector_type))
            args = {"name": name}
            if need_field:
                args['field'] = field
            return collector_class(**args)

    def from_string(self, schema:str)->List[Collector]:
        defs = schema.split(',')
        collectors = []
        for d in defs:
            field = None
            if ':' in d:
                collector_type, field = d.split(':')
            else:
                collector_type = d
            if isinstance(collector_type, str):
                collector_type = collector_type.strip()
            if isinstance(field, str):
                field = field.strip()
            collector = None
            collector = self.create(collector_type, None, field)
            if collector is None:
                raise ValueError("Unknown collector type '%s'" % (collector_type))        
            collectors.append(collector)
        return collectors
         

    def from_list(self, schema:List)->List[Collector]:
        collectors = []
        for index, definition in enumerate(schema):
            if(isinstance(definition, str)):
                try: 
                    cc = self.from_string(definition)
                except Exception as e:
                    raise ValueError("Error in definition %d" % (index)) from e
                collectors.extend(cc)
            else:
                if not isinstance(definition, dict):
                    raise ValueError("Collector definition must be string or dict")
                collector_type = definition.get('type', None)
                field = definition.get('field', None)
                name = definition.get('name', None)
                try:
                    collector = self.create(collector_type, name, field)
                    collectors.append(collector)
                except Exception as e:
                    raise ValueError("Error in definition %d" % (index)) from e
        return collectors

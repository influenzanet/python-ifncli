"""
App configuration management
"""
from typing import Dict, List
import sys
import os
from pathlib import Path
from .utils import read_yaml, readable_yaml, write_content

class ConfigException(Exception):
    pass

class ConfigManager:
    """
        Manage configuration loading and context (known configuration location you can switch)
    """
    def __init__(self):
        self.context_file = None # File where contexts are defined
        self.contexts: Dict[str] = {}
        self.current:str = None
        self.cfg_from = None
 
    def load(self, cfg_path=None):
        # Warning for common error
        if os.getenv('INF_CONFIG') is not None:
            print("INF_CONFIG is defined, are you sure you didnt mistyped IFN_CONFIG ?")
        
        context_file = os.getenv('IFNCLI_CONTEXT')
        if context_file is not None:
            ctx = read_yaml(context_file)
            self.contexts = ctx['configs']
            self.current = ctx['current']
            self.context_file = context_file
            self.cfg_from = "context_file"
        else:
            # Create a single context with default config
            # IFN_CONFIG can be used to override the default config passed in argument
            # Caution when used it's not possible to use the --config option
            env_path = os.getenv('IFN_CONFIG', '')
            if env_path != "":
                cfg_path = env_path
                self.cfg_from = "env:IFN_CONFIG"
            else:
                self.cfg_form = "arg:--config"
            self.contexts['default'] = cfg_path
            self.current = 'default'
            
        return self.load_context()

    def load_context(self, name=None):
        if name is None:
            name = self.current
        if name is None:
            raise ConfigException("Context name is None")
        cfg_path = self.get_context(name) 
        return self.load_config(cfg_path)

    def get_context(self, name:str):
        if not name in self.contexts:
            raise ConfigException("Context '%s' not found in contexts list" % (name))
        return self.contexts[name]

    def load_config(self, path):
        if not Path(path).is_file():
            raise ConfigException("Unable to find config file at %s" % (path,))
        try:
            config = read_yaml(path)
            config['__config_file'] = path
            return config
        except:
            print("Unable to load configuration file")
            raise

    def get_contexts(self):
        return self.contexts

    def get_current(self,):
        return self.current

    def switch(self, name:str):
        if self.context_file is None:
            raise ConfigException("No context file in use")
        if not name in self.contexts:
            raise ConfigException("Unknown context name '%s'" % name)
        if self.current == name:
            return
        ctx = {
            'current': name,
            'configs': self.contexts
        }
        write_content(self.context_file, readable_yaml(ctx))

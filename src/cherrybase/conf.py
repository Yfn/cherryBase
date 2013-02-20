# -*- coding: utf-8 -*-

import cherrypy
from cherrybase.utils import AttributeDict

class ConfigNamespace (object):
    '''
    Класс-утилита для чтения конфигурации
    '''
    def __init__ (self, name, defaults = {}):
        '''
        Конструктор. Привязывает пространство имен к конфигурации CherryPy по умолчанию.
        
        Args:
            name (str): Название пространства имен
            defaults (dict): Значения параметров конфигурации по умолчанию
        '''
        self.config = defaults
        cherrypy.config.namespaces [name] = self

    def __call__ (self, key, value):
        self.config [key] = value

    def __getattr__ (self, name):
        return self.config [name] if name in self.config else super (ConfigNamespace, self).__getattr__ (name)

    def __getitem__ (self, name):
        return self.config [name]


class DictConfigNamespace (dict):
    '''
    Класс-утилита для чтения конфигурационных словарей
    '''
    def __init__ (self, name, prefixes = (), defaults = {}, default_singles = {}):
        super (DictConfigNamespace, self).__init__({prefix: AttributeDict (defaults) for prefix in prefixes})
        self.defaults = defaults
        self.singles = default_singles
        cherrypy.config.namespaces [name] = self

    def __call__ (self, key, value):
        if '.' not in key:
            self.singles [key] = value
            return

        section, key = key.split ('.', 2)
        if section not in self:
            self [section] = AttributeDict (self.defaults)
        self [section][key] = value

    def __getattr__ (self, name):
        return self [name] if name in self else self.singles.get (name)

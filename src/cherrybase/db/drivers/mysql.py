# -*- coding: utf-8 -*-
from __future__ import absolute_import

from ..base import ThreadedPool, ShortcutsMixin
from mysql.connector import MySQLConnection as Connection
from mysql.connector.cursor import MySQLCursorDict as DictCursor
from mysql.connector.errors import Error as MySQLError

import os


class _Connection (Connection, ShortcutsMixin):

    default_cursor = DictCursor

    def __init__ (self, *args, **kwargs):
        super (_Connection, self).__init__ (*args, **kwargs)
        self.cmd_query ('set WAIT_TIMEOUT=%d' % 31536000 if os.name == 'posix' else 2147483)

    def is_connected (self):
        try:
            self.cmd_ping ()
            return True
        except MySQLError:
            return False


class MySql (ThreadedPool):

    defaults = {
        'host': '127.0.0.1',
        'port': 3306,
        'unix_socket': '',
        'db': 'mysql',
        'user': 'root',
        'passwd': '',
        'charset': 'utf8',
        'compress': False
    }

    def __init__ (self, min_connections = 0, max_connections = 40, timeout = 0, **kwargs):
        super (MySql, self).__init__ (_Connection, min_connections, max_connections, timeout, **kwargs)


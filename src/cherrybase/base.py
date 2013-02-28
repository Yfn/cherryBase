# -*- coding: utf-8 -*-

import cherrypy
import os, logging
from uuid import uuid1
from cherrybase.conf import ConfigNamespace
from cherrypy import _cptree, _cpconfig, _cpwsgi
from . import utils

class _Stub (object):
    pass


class ApplicationTree (object):

    def __init__ (self, name, stub_factory = _Stub):
        self.name = name
        self.stub_factory = stub_factory
        self.clear ()

    def clear (self):
        self.root = None

    def handler_exists (self, path_list):
        if not path_list:
            return bool (self.root)
        current = self.root
        for element in path_list:
            try:
                current = getattr (current, element)
            except AttributeError:
                return False
        return True

    def find_owner (self, path_list):
        if not path_list and not self.root:
            self.root = self.stub_factory ()
        result = self.root
        for element in path_list:
            if not hasattr (result, element):
                setattr (result, element, self.stub_factory ())
            result = getattr (result, element)
        return result

    def add (self, path, handler, config = None):
        stripped_path = path.strip ('/')
        path_list = stripped_path.split ('/') if stripped_path else []

        if self.handler_exists (path_list):
            raise AttributeError ('Path "{0}" is busy in "{1}"'.format (path, self.name))

        if config:
            if not hasattr (handler, '_cp_config'):
                handler._cp_config = {}
            _cpconfig.merge (handler._cp_config, config)

        handler._mount_path = '/' + stripped_path
        if not path_list:
            self.root = handler
        else:
            setattr (self.find_owner (path_list [0:-1]), path_list [-1], handler)
        cherrypy.log.error ('{} is mounted on "{}" in "{}"'.format (type (handler).__name__, path, self.name), 'TREE')


class Application (object):

    def __init__ (self, name = None, config = None, vhosts = None, routes = None):
        self.name = name or uuid1 ()
        self.vhosts = vhosts or [self.name]
        self.tree = ApplicationTree (self.name)
        self.config = config
        self.app = None
        if routes:
            for path, handler, cfg in routes:
                self.tree.add (path, handler, cfg)

    def _log_name (self, log_type = 'access'):
        name = 'log.f_' + log_type
        cfg = self.app.find_config ('/', name, None)
        if cfg:
            return cfg
        cfg = cherrypy.config.get (name, None)
        return '{}/{}.{}.log'.format (os.path.dirname (cfg), self.name, log_type) if cfg else None

    def prepare (self, debug = True):
        self.app = _cptree.Application (self.tree.root, '', self.config)
        if not debug:
            self.app.merge ({
                '/': {
                    'log.f_access': self._log_name ('access'),
                    'log.f_error': self._log_name ('error')
                }
            })
        utils.setup_log (self.app.log, debug)


_daemon_conf = ConfigNamespace (
    'daemon',
    {
        'on': False,
        'user': 'www-data',
        'group': 'www-data',
        'pid_file': '/var/run/cherrybase.pid'
    }
)
_server_conf = ConfigNamespace (
    'server',
    {
        'pkg_path': os.path.dirname (os.path.dirname (__file__)),
        'packages': [],
        'main_handler': _Stub (),
        'block_interval': 0.1,
    }
)


class Server (object):

    def __init__ (self, applications = None, config = None, debug = True):
        self.applications = applications or []
        self.debug = debug
        if config:
            cherrypy.config.update (config)

    def start (self):
        vhosts = {}
        for app in self.applications:
            app.prepare (self.debug)
            vhosts.update ({host: app.app for host in app.vhosts})

        self.daemonize ()

        cherrypy.tree.graft (
            _cpwsgi.VirtualHost (
                _cptree.Application (_server_conf.main_handler),
                domains = vhosts
            )
        )

        if hasattr (cherrypy.engine, 'signal_handler'):
            cherrypy.engine.signal_handler.subscribe ()
        cherrypy.engine.start ()
        cherrypy.engine.block ()

    def daemonize (self):
        if not _daemon_conf.on:
            return

        from cherrypy.process.plugins import PIDFile, Daemonizer, DropPrivileges
        if os.name == 'posix':
            import grp, pwd
            try:
                uid = pwd.getpwnam (_daemon_conf.user)[2]
                gid = grp.getgrnam (_daemon_conf.group)[2]
            except KeyError:
                cherrypy.log.error (
                    'Cannot find user "{0}" or group "{1}"'.format (_daemon_conf.user, _daemon_conf.group),
                    'SERVER',
                    logging.FATAL
                )
                raise
        else:
            uid = None
            gid = None

        DropPrivileges (cherrypy.engine, uid = uid, gid = gid).subscribe ()
        if _daemon_conf.pid_file:
            PIDFile (cherrypy.engine, _daemon_conf.pid_file).subscribe ()
        Daemonizer (cherrypy.engine).subscribe ()
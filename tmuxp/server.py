# -*- coding: utf8 - *-
"""
    tmuxp.server
    ~~~~~~~~~~~~

    tmuxp helps you manage tmux workspaces.

    :copyright: Copyright 2013 Tony Narlock.
    :license: BSD, see LICENSE for details
"""
from __future__ import absolute_import, division, print_function, with_statement

import os
from .util import tmux, TmuxRelationalObject
from .session import Session
from . import formats
import logging

logger = logging.getLogger(__name__)


class Server(TmuxRelationalObject):

    '''
    The :term:`tmux(1)` server. Container for:

    - :attr:`Server._sessions` [:class:`Session`, ...]

      - :attr:`Session._windows` [:class:`Window`, ...]

        - :attr:`Window._panes` [:class:`Pane`, ...]

          - :class:`Pane`

    When instantiated, provides the ``t`` global. stores information on live,
    running tmux server.
    '''

    socket_name = None
    socket_path = None
    config_file = None
    childIdAttribute = 'session_id'

    def __init__(self, socket_name=None, socket_path=None, config_file=None,
                 **kwargs):
        self._windows = []
        self._panes = []
        self._sessions = []

        if socket_name:
            self.socket_name = socket_name

        if socket_path:
            self.socket_path = socket_path

        if config_file:
            self.config_file = config_file

    def tmux(self, *args, **kwargs):
        args = list(args)
        if self.socket_name:
            args.insert(0, '-L{}'.format(self.socket_name))
        if self.socket_path:
            args.insert(0, '-S{}'.format(self.socket_path))
        if self.config_file:
            args.insert(0, '-f{}'.format(self.config_file))

        return tmux(*args, **kwargs)

    def _list_sessions(self):
        '''
        Return a list of :class:`Session` from tmux server.

        ``$ tmux list-sessions``
        '''
        sformats = formats.SESSION_FORMATS
        tmux_formats = ['#{%s}' % format for format in sformats]
        sessions = self.tmux(
            'list-sessions',
            '-F%s' % '\t'.join(tmux_formats),   # output
        )

        if sessions.stderr:
            raise Exception(sessions.stderr)

        return sessions.stdout

    def _update_sessions(self):
        '''
        Return a list of :class:`Session` from tmux server.

        ``$ tmux list-sessions``
        '''
        sformats = formats.SESSION_FORMATS
        tmux_formats = ['#{%s}' % format for format in sformats]
        sessions = self._list_sessions()

        # combine format keys with values returned from ``tmux list-windows``
        sessions = [dict(zip(
            sformats, session.split('\t'))) for session in sessions]

        # clear up empty dict
        new_sessions = [
            dict((k, v) for k, v in session.iteritems() if v) for session in sessions
        ]

        if self._sessions:
            # http://stackoverflow.com/a/14465359
            self._sessions[:] = []

        self._sessions.extend(new_sessions)

        return self

    @property
    def sessions(self):
        '''
        Return a list of :class:`session` from the ``tmux(1)`` session.

        :rtype: :class:`session`
        '''
        new_sessions = self.server._update_sessions()._sessions

        new_sessions = [
           s for s in new_sessions if w['session_id'] == self.get('session_id')
        ]

        return [Session(server=self, **session) for session in new_sessions]
    list_children = sessions

    def _list_windows(self):
        '''
        Return dict of ``tmux(1) list-windows`` values.
        '''

        wformats = ['session_name', 'session_id'] + formats.WINDOW_FORMATS
        tmux_formats = ['#{%s}' % format for format in wformats]

        windows = self.tmux(
            'list-windows',                     # ``tmux list-windows``
            '-a',
            '-F%s' % '\t'.join(tmux_formats),   # output
        )

        if windows.stderr:
            raise Exception(windows.stderr)

        return windows.stdout

    def _update_windows(self):
        ''' take the outpout of _list_windows from shell and put it into
        a list of dicts'''

        wformats = ['session_name', 'session_id'] + formats.WINDOW_FORMATS

        windows = self._list_windows()

        # combine format keys with values returned from ``tmux list-windows``
        windows = [dict(zip(
            wformats, window.split('\t'))) for window in windows]

        # clear up empty dict
        windows = [
            dict((k, v) for k, v in window.iteritems() if v) for window in windows
        ]

        '''
        iterate through the returned windows, see if the window_id exists, if
        so update it.

        the new method doesn't care about diffs. independent pane and window
        objects look up their pane_id/window_id. if no pane_id or window_id
        exists, it's a zombie :O
        '''

        if self._windows:
            # http://stackoverflow.com/a/14465359
            self._windows[:] = []

        self._windows.extend(windows)

        return self

    def _list_panes(self):
        '''Return list of :class:`Pane` for the window.

        :rtype: list of :class:`Pane`
        '''
        pformats = ['session_name', 'session_id',
                   'window_index', 'window_id'] + formats.PANE_FORMATS
        tmux_formats = ['#{%s}\t' % f for f in pformats]

        # if isinstance(self.get('window_id'), basestring):
        #    window_id =

        panes = self.tmux(
            'list-panes',
            #'-t%s:%s' % (self.get('session_name'), self.get('window_id')),
            '-a',
            '-F%s' % ''.join(tmux_formats),     # output
        )

        if panes.stderr:
            raise Exception(panes.stderr)

        return panes.stdout

    def _update_panes(self):
        ''' take the outpout of _list_panes from shell and put it into
        a list of dicts'''

        pformats = ['session_name', 'session_id',
                   'window_index', 'window_id'] + formats.PANE_FORMATS


        panes = self._list_panes()

        # combine format keys with values returned from ``tmux list-panes``
        panes = [dict(zip(
            pformats, window.split('\t'))) for window in panes]

        # clear up empty dict
        panes = [
            dict((k, v) for k, v in window.iteritems() if v) for window in panes
        ]

        '''
        iterate through the returned panes, see if the window_id exists, if
        so update it.

        the new method doesn't care about diffs. independent pane and window
        objects look up their pane_id/window_id. if no pane_id or window_id
        exists, it's a zombie :O
        '''

        if self._panes:
            # http://stackoverflow.com/a/14465359
            self._panes[:] = []

        self._panes.extend(panes)

        return self

    def list_clients(self):
        '''
        Return a list of :class:`client` from tmux server.

        ``$ tmux list-clients``
        '''
        formats = CLIENT_FORMATS
        tmux_formats = ['#{%s}' % format for format in formats]
        # import ipdb
        # ipdb.set_trace()
        clients = self.tmux(
            'list-clients',
            '-F%s' % '\t'.join(tmux_formats),   # output
        ).stdout

        # combine format keys with values returned from ``tmux list-windows``
        clients = [dict(zip(
            formats, client.split('\t'))) for client in clients]

        # clear up empty dict
        new_clients = [
            dict((k, v) for k, v in client.iteritems() if v) for client in clients
        ]

        if not self._clients:
            for client in new_clients:
                logger.debug('adding client_tty %s' % (client['client_tty']))
                self._clients.append(client)
            return self._clients

        new = {client['client_tty']: client for client in new_clients}
        old = {client.get('client_tty'): client for client in self._clients}

        created = set(new.keys()) - set(old.keys())
        deleted = set(old.keys()) - set(new.keys())
        intersect = set(new.keys()).intersection(set(old.keys()))

        diff = {id: dict(set(new[id].items()) - set(old[id].items()))
                for id in intersect}

        logger.debug(
            "syncing clients"
            "\n\tdiff: %s\n"
            "\tcreated: %s\n"
            "\tdeleted: %s\n"
            "\tintersect: %s" % (diff, created, deleted, intersect)
        )

        for s in self._clients:
            # remove client objects if deleted or out of client
            if s.get('client_tty') in deleted:
                logger.debug("removing %s" % s)
                self._clients.remove(s)

            if s.get('client_tty') in intersect:
                logger.debug('updating client_tty %s' % (s.get('client_tty')))
                s.update(diff[s.get('client_tty')])

        # create client objects for non-existant client_tty's
        for client in [new[client_tty] for client_tty in created]:
            logger.debug('new client %s' % client['client_tty'])
            self._clients.append(client)

        return self._clients

    def server_exists(self):
        '''server is on and exists

        '''

        try:
            self.tmux('list-clients')
            self.tmux('list-sessions')
            return True
        except Exception:
            return False

    def has_clients(self):
        # are any clients connected to tmux
        if len(self.tmux('list-clients')) > int(1):
            return True
        else:
            return False
        # if e.stderr == 'failed to connect to server':
        #    raise TmuxNotRunning('tmux session not running. please start'
        #                            'a tmux session in another terminal '
        #                            'window and continue.')

    def attached_sessions(self):
        '''
            Returns active :class:`Session` object

            This will not work where multiple tmux sessions are attached.
        '''

        sessions = self._sessions
        attached_sessions = list()

        for session in sessions:
            if 'session_attached' in session:
                # for now session_active is a unicode
                if session.get('session_attached') == '1':
                    logger.debug('session %s attached', session.get(
                        'session_name'))
                    attached_sessions.append(session)
                else:
                    continue

        return attached_sessions or None

    def has_session(self, target_session):
        '''
        ``$ tmux has-session``

        :param: target_session: str of session name.

        returns True if session exists.
        '''

        proc = self.tmux('has-session', '-t%s' % target_session)

        if 'failed to connect to server' in proc.stdout:
            return False
        elif 'session not found' in proc.stdout:
            return False
        else:
            return True

    def kill_server(self):
        '''
        ``$ tmux kill-server``
        '''
        self.tmux('kill-server')

    def kill_session(self, target_session=None):
        '''
        ``$ tmux kill-session``

        :param: target_session: str. note this accepts fnmatch(3). 'asdf' will
                                kill asdfasd
        '''
        proc = self.tmux('kill-session', '-t%s' % target_session)

        if proc.stderr:
            raise Exception(proc.stderr)

        self._update_sessions()

        return self

    @property
    def sessions(self):
        return self._update_sessions()._sessions

    def switch_client(self, target_session):
        '''
        ``$ tmux switch-client``

        :param: target_session: str. name of the session. fnmatch(3) works.
        '''
        # tmux('switch-client', '-t', target_session)
        proc = self.tmux('switch-client', '-t%s' % target_session)

        if proc.stderr:
            raise Exception(proc.stderr)

    def attach_session(self, target_session=None):
        '''
        ``$ tmux attach-session`` aka alias: ``$ tmux attach``

        :param: target_session: str. name of the session. fnmatch(3) works.
        '''
        # tmux('switch-client', '-t', target_session)
        tmux_args = tuple()
        if target_session:
            tmux_args += ('-t%s' % target_session,)

        proc = self.tmux('attach-session', *tmux_args)

        if proc.stderr:
            raise Exception(proc.stderr)

    def new_session(self,
                    session_name=None,
                    kill_session=False,
                    attach=False,
                    *args,
                    **kwargs):
        '''
        ``$ tmux new-session``

        Returns :class:`Session`

        Uses ``-P`` flag to print session info, ``-F`` for return formatting
        returns new Session object.

        ``$ tmux new-session -d`` will create the session in the background
        ``$ tmux new-session -Ad`` will move to the session name if it already
        exists. todo: make an option to handle this.

        :param session_name: session name::

            $ tmux new-session -s <session_name>
        :type session_name: string

        :param detach: create session background::

            $ tmux new-session -d
        :type detach: bool

        :param attach_if_exists: if the session_name exists, attach it.
                                 if False, this method will raise a
                                 :exc:`tmuxp.exc.TmuxSessionExists` exception
        :type attach_if_exists: bool

        :param kill_session: Kill current session if ``$ tmux has-session``
                             Useful for testing workspaces.
        :type kill_session: bool
        '''

        # ToDo: Update below to work with attach_if_exists
        if self.has_session(session_name):
            if kill_session:
                self.tmux('kill-session', '-t%s' % session_name)
                logger.error('session %s exists. killed it.' % session_name)
            else:
                raise TmuxSessionExists(
                    'Session named %s exists' % session_name)

        logger.debug('creating session %s' % session_name)

        sformats = formats.SESSION_FORMATS
        tmux_formats = ['#{%s}' % f for f in sformats]

        env = os.environ.get('TMUX')

        if env:
            del os.environ['TMUX']

        tmux_args = (
            '-s%s' % session_name,
            '-P', '-F%s' % '\t'.join(tmux_formats),   # output
        )

        if not attach:
            tmux_args += ('-d',)

        session_info = self.tmux(
            'new-session',
            *tmux_args
        )

        if session_info.stderr:
            raise Exception(session_info.stderr)

        session_info = session_info.stdout[0]

        if env:
            os.environ['TMUX'] = env

        # combine format keys with values returned from ``tmux list-windows``
        session_info = dict(zip(sformats, session_info.split('\t')))

        # clear up empty dict
        session_info = dict((k, v) for k, v in session_info.iteritems() if v)

        session = Session(server=self, **session_info)

        #self._sessions.append(session)
        self._update_sessions()

        return session

# ============================================================================
# FILE: file.py
# AUTHOR: Shougo Matsushita <Shougo.Matsu at gmail.com>
# License: MIT license
# ============================================================================

import re
import os
import shlex
import subprocess
from itertools import filterfalse
from denite import util
from .openable import Kind as Openable


class Kind(Openable):

    def __init__(self, vim):
        super().__init__(vim)

        self.name = 'file'
        self.default_action = 'open'
        self.redraw_actions += ['delete', 'add', 'preview', 'highlight']
        self.persist_actions += ['preview', 'highlight', 'add', 'delete']
        self._previewed_target = {}

    def action_delete(self, context):
        path = ''
        for target in context['targets']:
            path = path + ' ' + target['action__path']
            self.vim.command('Rm ' + path)

    def action_add(self, context):
        cwd = self.vim.call('getcwd')
        target = context['targets'][0]
        dirpath = os.path.dirname(target['action__path'])
        if not os.path.isabs(dirpath):
            dirpath = os.path.join(cwd, dirpath)
        inputs = util.input(self.vim, context, 'Touch ')
        if not inputs:
            return
        args = 'touch %s' % (inputs)
        self.vim.command('lcd' + dirpath)
        try:
            self.vim.call('system', args)
        except Exception:
            pass
        self.vim.command('lcd' + cwd)

    def action_open(self, context):
        cwd = self.vim.call('getcwd')
        for target in context['targets']:
            path = target['action__path']
            match_path = '^{0}$'.format(path)

            if re.match('https?://', path):
                # URI
                self.vim.call('denite#util#open', path)
                return
            if path.startswith(cwd):
                path = os.path.relpath(path, cwd)

            if self.vim.call('bufwinnr', match_path) <= 0:
                self.vim.call(
                    'denite#util#execute_path', 'edit', path)
            elif self.vim.call('bufwinnr',
                               match_path) != self.vim.current.buffer:
                self.vim.call(
                    'denite#util#execute_path', 'buffer', path)
            self.__jump(context, target)

    def action_preview(self, context):
        return self.__preview(context, False)

    def action_highlight(self, context):
        return self.__preview(context, True)

    def action_quickfix(self, context):
        qflist = [{
            'filename': x['action__path'],
            'lnum': x['action__line'],
            'text': x['action__text'],
        } for x in context['targets']
                  if 'action__line' in x and 'action__text' in x]
        self.vim.call('setqflist', qflist)
        self.vim.command('copen')

    def __get_preview_window(self):
        return next(filterfalse(lambda x:
                                not x.options['previewwindow'],
                                self.vim.windows), None)

    def __preview(self, context, highlight):
        target = context['targets'][0]
        path = target['action__path'].replace('/./', '/')

        preview_window = self.__get_preview_window()
        if (preview_window and self._previewed_target == target):
            self.vim.command('pclose!')
        else:
            prev_id = self.vim.call('win_getid')
            self.vim.call('denite#helper#preview_file', context, path)
            self.vim.command('wincmd P')
            self.__jump(context, target)
            if highlight:
                self.vim.call('clearmatches')
                self.vim.call('matchaddpos', 'Search',
                              [int(target.get('action__line', 0))])
            self.vim.call('win_gotoid', prev_id)
            self._previewed_target = target

    def __jump(self, context, target):
        if 'action__pattern' in target:
            self.vim.call('search', target['action__pattern'], 'w')

        line = int(target.get('action__line', 0))
        col = int(target.get('action__col', 0))

        try:
            if line > 0:
                self.vim.call('cursor', [line, 0])
                if 'action__col' not in target:
                    pos = self.vim.current.line.lower().find(
                        context['input'].lower())
                    if pos >= 0:
                        self.vim.call('cursor', [0, pos + 1])
            if col > 0:
                self.vim.call('cursor', [0, col])
        except Exception:
            pass

        # Open folds
        self.vim.command('normal! zv')

    # Needed for openable actions
    def __winid(self, target):
        path = target['action__path']
        bufnr = self.vim.call('bufnr', path)
        if bufnr == -1:
            return None
        winids = self.vim.call('win_findbuf', bufnr)
        return None if len(winids) == 0 else winids[0]

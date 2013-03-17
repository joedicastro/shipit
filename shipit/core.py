# -*- coding: utf-8 -*-

import os
import subprocess
import tempfile

from urwid import MainLoop, ExitMainLoop

from .config import PALETTE

NEW_ISSUE = """
<!---
The first line will be used as the issue title. The rest will be the body of
the issue.
-->
"""


def spawn_editor(help_text=None):
    text = '' if help_text is None else help_text

    tmp_file = tempfile.NamedTemporaryFile(mode='w+',
                                           suffix='.markdown',
                                           delete=False)
    tmp_file.write(text)
    tmp_file.close()

    fname = tmp_file.name
    subprocess.call([os.getenv('EDITOR', 'vim'), fname])

    with open(fname, 'r') as f:
        contents = f.read()

    os.unlink(fname)

    return contents



def unlines(text):
    return text.split('\n')


def lines(line_list):
    return '\n'.join(line_list)


class Shipit():
    ISSUE_LIST = 0
    ISSUE_DETAIL = 1

    def __init__(self, ui, repo):
        self.ui = ui
        self.repo = repo

    def start(self):
        self.issue_list()

        self.loop = MainLoop(self.ui,
                             PALETTE,
                             handle_mouse=True,
                             unhandled_input=self.handle_keypress)
        self.loop.run()

    def issue_list(self):
        self.mode = self.ISSUE_LIST
        self.ui.issues(self.repo.iter_issues())

    def issue_detail(self, issue):
        self.mode = self.ISSUE_DETAIL
        self.ui.issue(issue)

    def handle_keypress(self, key):
        # Issue list
        # ==========
        #
        #  enter: detail X
        #
        #  C: close focused issue
        #  c: comment
        #  R: reopen
        #  e: edit
        #
        #  n: new issue
        #
        # Issue detail
        # ============
        #
        #  C: close
        #  c: comment
        #  R: reopen
        #  e: edit
        #
        #  esc: issue list X
        #
        if key == 'n':
            if self.mode is self.ISSUE_LIST:
                issue_text = spawn_editor(NEW_ISSUE)
                contents = unlines(issue_text)
                if not issue_text:
                    # TODO: No issue content
                    return
                title, *body = contents
                body = lines(body)
                issue = self.repo.create_issue(title=title, body=body)
                if issue:
                    self.issue_detail(issue)
        elif key == 'esc':
            if self.mode is self.ISSUE_DETAIL:
                self.issue_list()
        elif key == 'enter':
            if self.mode is self.ISSUE_LIST:
                issue = self.ui.frame.body.focus.issue
                self.issue_detail(issue)
        elif key == 'q':
            raise ExitMainLoop

# -*- coding: utf-8 -*-

import os
import subprocess
import tempfile

from urwid import MainLoop, ExitMainLoop

from .config import (
    PALETTE,

    KEY_NEW_ISSUE, KEY_CLOSE_ISSUE, KEY_BACK, KEY_DETAIL, KEY_EDIT,
    KEY_COMMENT, KEY_QUIT,
)
from .ui import time_since

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

    return_code = subprocess.call([os.getenv('EDITOR', 'vim'), fname])
    if return_code != 0:
        return None

    with open(fname, 'r') as f:
        contents = f.read()

    os.remove(fname)

    return contents

def unlines(text):
    return text.split('\n')


def lines(line_list):
    return '\n'.join(line_list)


def format_comment(comment):
    author = str(comment.user)
    time = time_since(comment.created_at)
    body = unlines(comment.body_text)
    body = ['    '.join(['', line]) for line in body]
    body = lines(body)
    return "{author} commented {time}\n\n{body}\n".format(author=author,
                                                          time=time,
                                                          body=body,)



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
        #  R: reopen
        #  D: delete
        if key == KEY_NEW_ISSUE:
            if self.mode is self.ISSUE_LIST:
                issue_text = spawn_editor(NEW_ISSUE)
                if issue_text is None:
                    # TODO: cancelled by the user
                    return

                contents = unlines(issue_text)
                title, *body = contents

                if not title:
                    # TODO: incorrect input, at least a title is needed
                    return
                body = lines(body)

                issue = self.repo.create_issue(title=title, body=body)
                if issue:
                    self.issue_detail(issue)
        elif key == KEY_CLOSE_ISSUE:
            issue = self.ui.frame.body.focus.issue
            issue.close()
            self.issue_list()
        elif key == KEY_BACK:
            if self.mode is self.ISSUE_DETAIL:
                self.issue_list()
        elif key == KEY_DETAIL:
            if self.mode is self.ISSUE_LIST:
                issue = self.ui.frame.body.focus.issue
                self.issue_detail(issue)
        elif key == KEY_EDIT:
            issue = self.ui.frame.body.focus.issue

            title_and_body = '\n'.join([issue.title, issue.body_text])
            issue_text = spawn_editor(title_and_body)

            contents = unlines(issue_text)
            title, *body = contents

            if not title:
                # TODO: incorrect input, at least a title is needed
                return
            body = lines(body)

            issue.edit(title=title, body=body)

            if self.mode is self.ISSUE_LIST:
                self.issue_list()
            elif self.mode is self.ISSUE_DETAIL:
                self.issue_detail(issue)
        elif key == KEY_COMMENT:
            issue = self.ui.frame.body.focus.issue

            # Inline all the thread comments
            issue_thread = [format_comment(comment) for comment in issue.iter_comments()]
            issue_thread.insert(0,'\n\n'.join([issue.title, issue.body_text, '']))
            # Make the whole thread a comment
            issue_thread.insert(0, '<!---\n')
            issue_thread.append('-->')

            comment_text = spawn_editor('\n'.join(issue_thread))

            if comment_text is None:
                # TODO: cancelled
                return

            # TODO: strip comments first!
            if not comment_text.strip():
                # TODO: invalid input
                return

            issue.create_comment(comment_text)

            self.issue_detail(issue)
        elif key == KEY_QUIT:
            raise ExitMainLoop

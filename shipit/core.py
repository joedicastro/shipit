# -*- coding: utf-8 -*-

import os
import subprocess
import tempfile

from urwid import MainLoop, ExitMainLoop, MonitoredList

from .config import (
    PALETTE,

    KEY_NEW_ISSUE, KEY_CLOSE_ISSUE, KEY_BACK, KEY_DETAIL, KEY_EDIT,
    KEY_COMMENT, KEY_DIFF, KEY_QUIT,
)
from .ui import time_since
from .events import on
from .models import is_issue, is_pull_request

NEW_ISSUE = """
<!---
The first line will be used as the issue title. The rest will be the body of
the issue.
-->
"""


def spawn_editor(help_text=None):
    """
    Open a editor with a temporary file containing ``help_text``.

    If the exit code is 0 the text from the file will be returned.

    Otherwise, ``None`` is returned.
    """
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


def show_diff(pr):
    raw_diff = bytes.decode(pr.diff())[2:]
    diff = raw_diff[:-1]

    tmp_file = tempfile.NamedTemporaryFile(mode='w+',
                                           suffix='.diff',
                                           delete=False)
    tmp_file.write(diff)
    tmp_file.close()

    fname = tmp_file.name

    pager = os.getenv('PAGER', 'less')
    args = pager.split()
    args.append(fname)

    subprocess.call(args)
    os.remove(fname)


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


# FIXME: don't use a workaround when `__eq__` is implemented
def item_index(issues, item):
    for index, issue in enumerate(issues):
        if issue.id == item.id:
            return index
    else:
        return -1


class Shipit():
    ISSUE_LIST = 0
    ISSUE_DETAIL = 1
    PR_DETAIL = 2

    def __init__(self, ui, repo):
        self.ui = ui
        self.repo = repo

        self.issue_and_pr_list = MonitoredList()
        self.issue_and_pr_list.set_modified_callback(self.on_modify_issue_and_pr_list)
        for i in self.repo.iter_issues():
            # TODO: take controls into account (open,closed,pr)
            self.issue_and_pr_list.append(i)

        # Event handlers
        on('show_open_issues', self.show_open_issues)
        on('hide_open_issues', self.hide_open_issues)

        on('show_closed_issues', self.show_closed_issues)
        on('hide_closed_issues', self.hide_closed_issues)

        on('show_open_pull_requests', self.show_open_pull_requests)
        on('hide_open_pull_requests', self.hide_open_pull_requests)

    def start(self):
        self.issue_list()

        self.loop = MainLoop(self.ui,
                             PALETTE,
                             handle_mouse=True,
                             unhandled_input=self.handle_keypress)
        self.loop.run()

    def on_modify_issue_and_pr_list(self):
        self.ui.issues_and_pulls(self.issue_and_pr_list)

    def issue_list(self):
        self.mode = self.ISSUE_LIST
        self.ui.issues_and_pulls(self.issue_and_pr_list)

    def issue_detail(self, issue):
        self.mode = self.ISSUE_DETAIL
        self.ui.issue(issue)

    def pull_request_detail(self, pr):
        self.mode = self.PR_DETAIL
        self.ui.pull_request(pr)

    def show_open_issues(self, **kwargs):
        for i in self.repo.iter_issues():
            self.issue_and_pr_list.append(i)

    def hide_open_issues(self, **kwargs):
        for i in filter(is_issue, self.issue_and_pr_list[:]):
            if i.state == 'open':
                index = item_index(self.issue_and_pr_list, i)
                self.issue_and_pr_list.pop(index)

    def show_closed_issues(self, **kwargs):
        for i in self.repo.iter_issues(state='closed'):
            self.issue_and_pr_list.append(i)

    def hide_closed_issues(self, **kwargs):
        for i in filter(is_issue, self.issue_and_pr_list[:]):
            if i.state == 'closed':
                index = item_index(self.issue_and_pr_list, i)
                self.issue_and_pr_list.pop(index)

    def show_open_pull_requests(self, **kwargs):
        for pr in self.repo.iter_pulls():
            self.issue_and_pr_list.append(pr)

    def hide_open_pull_requests(self, **kwargs):
        for i in filter(is_pull_request, self.issue_and_pr_list[:]):
            if i.state == 'open':
                index = item_index(self.issue_and_pr_list, i)
                self.issue_and_pr_list.pop(index)

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
            issue = self.ui.get_issue()

            if issue:
                issue.close()

            self.issue_list()
        elif key == KEY_BACK:
            if self.mode in [self.ISSUE_DETAIL, self.PR_DETAIL]:
                self.issue_list()
        elif key == KEY_DETAIL:
            if self.mode is self.ISSUE_LIST:
                issue_or_pr = self.ui.get_focused_item()

                if is_issue(issue_or_pr):
                    self.issue_detail(issue_or_pr)
                elif is_pull_request(issue_or_pr):
                    self.pull_request_detail(issue_or_pr)
        elif key == KEY_EDIT:
            # TODO: not the issue but what it's focused, could be a comment!
            issue = self.ui.get_issue()
            if issue is None:
                return

            title_and_body = '\n'.join([issue.title, issue.body_text])
            issue_text = spawn_editor(title_and_body)

            if issue_text is None:
                # TODO: cancelled
                return

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
            issue = self.ui.get_issue()
            if issue is None:
                return

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
        elif key == KEY_DIFF:
            if self.mode is self.PR_DETAIL:
                pr = self.ui.get_focused_item()
                show_diff(pr)

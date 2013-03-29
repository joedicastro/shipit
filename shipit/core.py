# -*- coding: utf-8 -*-

import os
import subprocess
import tempfile
import concurrent.futures

from urwid import MainLoop, ExitMainLoop, MonitoredList

from .config import (
    PALETTE,

    KEY_NEW_ISSUE, KEY_CLOSE_ISSUE, KEY_BACK, KEY_DETAIL, KEY_EDIT,
    KEY_COMMENT, KEY_DIFF, KEY_QUIT,
)
from .ui import time_since
from .events import on
from .models import is_issue, is_pull_request, is_open, is_closed
from .func import lines, unlines, both

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


def step(first, last):
    """Call ``first`` asynchronously, and then add ``last`` as a callback."""
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        future = executor.submit(first)
        future.add_done_callback(last)


class IssuesAndPullRequests(MonitoredList):
    def __init__(self, repo):
        self._issues = []
        self._prs = []
        self.repo = repo

    def show_open_issues(self, **kwargs):
        self._append_open_issues()
        step(self.fetch_open_issues, self._append_open_issues)

    def hide_open_issues(self, **kwargs):
        # FIXME: on github3.py 0.6.0
        for i in filter(both(is_issue, is_open), self[:]):
            index = item_index(self, i)
            self.pop(index)

    def show_closed_issues(self, **kwargs):
        self._append_closed_issues()
        step(self.fetch_closed_issues, self._append_closed_issues)

    def hide_closed_issues(self, **kwargs):
        for i in filter(both(is_issue, is_closed), self[:]):
            index = item_index(self, i)
            self.pop(index)

    def show_open_pull_requests(self, **kwargs):
        self._append_open_pull_requests()
        step(self.fetch_open_pull_requests, self._append_open_pull_requests)

    def hide_open_pull_requests(self, **kwargs):
        for pr in filter(both(is_pull_request, is_open), self[:]):
            index = item_index(self, pr)
            self.pop(index)

    def fetch_open_pull_requests(self):
        self._prs.extend([i for i in self.repo.iter_pulls()])

    def fetch_open_issues(self):
        self._issues.extend([i for i in self.repo.iter_issues() if not i.pull_request])

    def fetch_closed_issues(self):
        self._issues.extend([i for i in self.repo.iter_issues(state='closed')])

    def _append_open_issues(self, future=None):
        # FIXME: __eq__ is coming
        for i in filter(is_open, self._issues):
            index = item_index(self, i)
            if index == -1:
                self.append(i)

    def _append_closed_issues(self, future=None):
        # FIXME: __eq__ is coming
        for i in filter(is_closed, self._issues):
            index = item_index(self, i)
            if index == -1:
                self.append(i)

    def _append_open_pull_requests(self, future=None):
        # FIXME: __eq__ is coming
        for pr in self._prs:
            index = item_index(self, pr)
            if index == -1:
                self.append(pr)


class Shipit():
    ISSUE_LIST = 0
    ISSUE_DETAIL = 1
    PR_DETAIL = 2
    PR_DIFF = 3

    def __init__(self, ui, repo):
        self.ui = ui
        self.repo = repo

        self.issues_and_prs = IssuesAndPullRequests(self.repo)
        self.issues_and_prs.set_modified_callback(self.on_modify_issues_and_prs)
        self.issues_and_prs.show_open_issues()
        self.issues_and_prs.show_open_pull_requests()

        # Event handlers
        on("show_open_issues", self.issues_and_prs.show_open_issues)
        on("hide_open_issues", self.issues_and_prs.hide_open_issues)

        on("show_closed_issues", self.issues_and_prs.show_closed_issues)
        on("hide_closed_issues", self.issues_and_prs.hide_closed_issues)

        on("show_open_pull_requests", self.issues_and_prs.show_open_pull_requests)
        on("hide_open_pull_requests", self.issues_and_prs.hide_open_pull_requests)

    def start(self):
        self.issue_list()

        self.loop = MainLoop(self.ui,
                             PALETTE,
                             handle_mouse=True,
                             unhandled_input=self.handle_keypress)
        self.loop.run()

    def on_modify_issues_and_prs(self):
        self.ui.issues_and_pulls(self.issues_and_prs)

    def issue_list(self):
        self.mode = self.ISSUE_LIST
        self.ui.issues_and_pulls(self.issues_and_prs)

    def issue_detail(self, issue):
        self.mode = self.ISSUE_DETAIL
        self.ui.issue(issue)

    def pull_request_detail(self, pr):
        self.mode = self.PR_DETAIL
        self.ui.pull_request(pr)

    def diff(self, pr):
        self.mode = self.PR_DIFF
        self.ui.diff(pr)

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
                i = item_index(self.issues_and_prs, issue)
                if i != -1:
                    # FIXME: comparison is coming, until then...
                    self.issues_and_prs.pop(i)
        elif key == KEY_BACK:
            if self.mode is self.PR_DIFF:
                pr = self.ui.get_focused_item()
                self.pull_request_detail(pr)
            elif self.mode in [self.ISSUE_DETAIL, self.PR_DETAIL]:
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
                self.diff(pr)

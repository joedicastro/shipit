# -*- coding: utf-8 -*-

from urwid import MainLoop

from ui import IssueListWidget
from config import PALETTE

USER = 'alejandrogomez'
REPO = 'turses'


class Shipit():
    def __init__(self, ui, api):
        self.ui = ui
        self.api = api

    def start(self):
        self.ui.issue(REPO, list(self.api.iter_repo_issues(USER, REPO))[4])

        self.loop = MainLoop(self.ui, PALETTE, handle_mouse=True)
        self.loop.run()

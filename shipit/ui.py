# -*- coding: utf-8 -*-

import time
from calendar import timegm

import urwid
from x256 import x256

from .config import ISSUE_DIVIDER, COMMENT_DIVIDER


def timestamp_from_datetime(datetime):
    return timegm(datetime.utctimetuple())


def time_since(datetime):
    # This code is borrowed from `python-twitter` library
    fudge = 1.25
    delta = float(time.time() - timestamp_from_datetime(datetime))

    if delta < (1 * fudge):
        return "a second ago"
    elif delta < (60 * (1 / fudge)):
        return "%d seconds ago" % (delta)
    elif delta < (60 * fudge):
        return "a minute ago"
    elif delta < (60 * 60 * (1 / fudge)):
        return "%d minutes ago" % (delta / 60)
    elif delta < (60 * 60 * fudge) or delta / (60 * 60) == 1:
        return "an hour ago"
    elif delta < (60 * 60 * 24 * (1 / fudge)):
        return "%d hours ago" % (delta / (60 * 60))
    elif delta < (60 * 60 * 24 * fudge) or delta / (60 * 60 * 24) == 1:
        return "a day ago"
    else:
        return "%d days ago" % (delta / (60 * 60 * 24))


def create_label_widget(label):
    # TODO: sensible foreground color
    bg = 'h%s' % x256.from_hex(label.color)
    attr = urwid.AttrSpec('white', bg)

    label_name = ' '.join(['', label.name, ''])

    return urwid.Text((attr, label_name))



class UI(urwid.WidgetWrap):
    """
    Creates a curses interface for the program, providing functions to draw
    all the components of the UI.
    """
    HEADER_ISSUE_LIST = '{owner}/{repo}'
    HEADER_ISSUE_DETAIL = '{owner}/{repo} ─ #{num}: {title}'

    def __init__(self, repo):
        self.repo = repo

        header = urwid.Text('shipit')

        # body
        body = urwid.Text('shipit')

        # footer
        self.frame = urwid.Frame(body, header=header)

        super().__init__(self.frame)

    # -- Modes ----------------------------------------------------------------

    def issues(self, issues):
        header_text = self.HEADER_ISSUE_LIST.format(owner=(str(self.repo.owner)),
                                                    repo=self.repo.name)
        self.frame.header.set_text(header_text)
        self.frame.body = issue_list(issues)
        self.frame.set_body(self.frame.body)

    def issue(self, issue):
        header_text = self.HEADER_ISSUE_DETAIL.format(owner=(str(self.repo.owner)),
                                                      repo=self.repo.name,
                                                      num=issue.number,
                                                      title=issue.title,)
        self.frame.header.set_text(header_text)
        self.frame.body = issue_detail(issue)
        self.frame.set_body(self.frame.body)


class IssueListWidget(urwid.WidgetWrap):
    """
    Widget containing a issue's basic information, meant to be rendered on a
    list.
    """
    # --
    # num - Title [tags]
    # by author - timeago  --- num comments
    # --
    HEADER_FORMAT = "#{num} ─ {title}       "
    BODY_FORMAT = "by {author}  {time}      {comments}"

    def __init__(self, issue):
        self.issue = issue

        widget = self._build_widget(issue)

        super().__init__(widget)

    @classmethod
    def _build_widget(cls, issue):
        """Return a widget for the ``issue``."""
        header_widget = urwid.Columns([w for w in cls._header_widgets(issue)])
        body_widget = cls._create_body_widget(issue)

        divider = urwid.AttrMap(urwid.Divider(ISSUE_DIVIDER), 'line', 'focus')
        widget = urwid.Pile([header_widget, body_widget, divider], focus_item=2)

        return widget

    @classmethod
    def _header_widgets(cls, issue):
        # TODO: refine this
        # Header widget
        yield cls._create_header_widget(issue)
        # Labels
        yield cls._create_label_widgets(issue)

    @classmethod
    def _create_header_widget(cls, issue):
        """
        Return the header text for the issue associated with this widget.
        """
        header_text = cls.HEADER_FORMAT.format(
            num=issue.number,
            title=issue.title,
        )
        header = urwid.Text(header_text)

        return urwid.AttrMap(header, 'header')

    @classmethod
    def _create_label_widgets(cls, issue):
        label_widgets = [create_label_widget(label) for label in issue.labels]
        return urwid.Columns(label_widgets)

    @staticmethod
    def _create_label_widget(label):
        # TODO: sensible foreground color
        bg = 'h%s' % x256.from_hex(label.color)
        attr = urwid.AttrSpec('white', bg)

        label_name = ' '.join(['', label.name, ''])

        return urwid.Text((attr, label_name))

    @classmethod
    def _create_body_widget(cls, issue):
        comments = "%s comments" % issue.comments if issue.comments else ""

        body_text = cls.BODY_FORMAT.format(
            author=str(issue.user),
            time=time_since(issue.created_at),
            comments=comments,
        )

        body = urwid.AttrMap(urwid.Text(body_text), 'body')

        return urwid.Padding(body, left=1, right=1)

    def selectable(self):
        return True

    def keypress(self, size, key):
        return key


def issue_detail(issue):
    comments = [IssueCommentWidget(issue, comment) for comment in issue.iter_comments()]
    comments.insert(0, ListDetailWidget(issue))

    return urwid.ListBox(urwid.SimpleListWalker(comments))


def issue_list(issues):
    issue_widgets = [IssueListWidget(issue) for issue in issues]
    return urwid.ListBox(urwid.SimpleListWalker(issue_widgets))


class IssueCommentWidget(urwid.WidgetWrap):
    # Comment

    # {user} commented                  {time}
    # {body}
    HEADER_FORMAT = "{author} commented                                 {time}"
    BODY_FORMAT = "{body}"

    def __init__(self, issue, comment):
        self.issue = issue
        self.comment = comment

        header_text = self._create_header(comment)
        body_text = self._create_body(comment)

        widget = self._build_widget(header_text, body_text)

        super().__init__(widget)

    @classmethod
    def _create_header(cls, comment):
        """
        Return the header text for the comment associated with this widget.
        """
        return cls.HEADER_FORMAT.format(
            author=str(comment.user),
            time=time_since(comment.created_at),
        )

    @classmethod
    def _create_body(cls, comment):
        return cls.BODY_FORMAT.format(
            body=comment.body_text,
        )

    @staticmethod
    def _build_widget(header_text, body_text):
        """Return the wrapped widget."""

        header = urwid.AttrMap(urwid.Text(header_text), 'header')
        body = urwid.Padding(urwid.AttrMap(urwid.Text(body_text), 'body'), left=1, right=1)

        divider = urwid.AttrMap(urwid.Divider(COMMENT_DIVIDER), 'line', 'focus')
        widget = urwid.Pile([header, body, divider], focus_item=2)

        return widget

    def selectable(self):
        return True

    def keypress(self, size, key):
        return key


class ListDetailWidget(urwid.WidgetWrap):
    """
    A widget for rendering an issue in detail . It includes all the information
    regarding the issue.
    """
    # {user} opened this issue {time}
    # TODO: labels
    # {title}
    # TODO{assignee}                        {milestone}
    # {body}
    # TODO{participants}

    HEADER_FORMAT = "{author} opened this issue {time}\n{title}"
    BODY_FORMAT = "{body}"

    def __init__(self, issue):
        self.issue = issue
        widget = self._build_widget(issue)
        super().__init__(widget)

    @classmethod
    def _build_widget(cls, issue):
        """Return a widget for the ``issue``."""
        header_widget = cls._create_header_widget(issue)
        labels = urwid.Columns([create_label_widget(label) for label in issue.labels])

        header = urwid.Columns([header_widget, labels])
        body = cls._create_body_widget(issue)

        divider = urwid.AttrMap(urwid.Divider(ISSUE_DIVIDER), 'line', 'focus')

        widget = urwid.Pile([header, body, divider], focus_item=2)

        return widget

    @classmethod
    def _create_header_widget(cls, issue):
        text = cls.HEADER_FORMAT.format(
            author=str(issue.user),
            time=time_since(issue.created_at),
            title=issue.title,
        )
        widget = urwid.Text(text)
        return urwid.AttrMap(widget, 'header')

    @classmethod
    def _create_body_widget(cls, issue):
        text = cls.BODY_FORMAT.format(
            body=issue.body_text,
        )
        widget = urwid.Text(text)
        attr_widget = urwid.AttrMap(widget, 'body')
        return urwid.Padding(attr_widget, left=1, right=1)

    def selectable(self):
        return True

    def keypress(self, size, key):
        return key

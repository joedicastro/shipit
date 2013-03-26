# -*- coding: utf-8 -*-

import time
from calendar import timegm

import urwid


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


class UI(urwid.WidgetWrap):
    """
    Creates a curses interface for the program, providing functions to draw
    all the components of the UI.
    """
    HEADER_ISSUE_LIST = '{owner}/{repo}'
    HEADER_ISSUE_DETAIL  = '{owner}/{repo} ─ #{num}: {title}'

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
    HEADER_FORMAT = "#{num} ─ {title}    {labels}"
    BODY_FORMAT = "by {author}  {time}      {comments}"

    def __init__(self, issue):
        self.issue = issue

        header_text = self._create_header(issue)
        body_text = self._create_body(issue)

        widget = self._build_widget(header_text, body_text)

        super().__init__(widget)

    def _create_header(self, issue):
        """
        Return the header text for the issue associated with this widget.
        """
        labels = ','.join([label.name for label in issue.labels])
        return self.HEADER_FORMAT.format(
            num=issue.number,
            title=issue.title,
            labels=labels,
        )

    def _create_body(self, issue):
        comments = "%s comments" % issue.comments if issue.comments else ""
        return self.BODY_FORMAT.format(
            author=str(issue.user),
            time=time_since(issue.created_at),
            comments=comments,
        )

    def _build_widget(self, header_text, body_text):
        """Return the wrapped widget."""

        header = urwid.AttrMap(urwid.Text(header_text), 'header')
        body = urwid.Padding(urwid.AttrMap(urwid.Text(body_text), 'body'), left=1, right=1)

        border_attr = 'line'
        issue_divider = '─'

        divider = urwid.AttrMap(urwid.Divider(issue_divider), border_attr, 'focus')
        widget = urwid.Pile([header, body, divider], focus_item=2)

        return widget

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

    def _create_header(self, comment):
        """
        Return the header text for the comment associated with this widget.
        """
        return self.HEADER_FORMAT.format(
            author=str(comment.user),
            time=time_since(comment.created_at),
        )

    def _create_body(self, comment):
        return self.BODY_FORMAT.format(
            body=comment.body_text,
        )

    def _build_widget(self, header_text, body_text):
        """Return the wrapped widget."""

        header = urwid.AttrMap(urwid.Text(header_text), 'header')
        body = urwid.Padding(urwid.AttrMap(urwid.Text(body_text), 'body'), left=1, right=1)

        border_attr = 'line'
        comment_divider = '─'

        divider = urwid.AttrMap(urwid.Divider(comment_divider), border_attr, 'focus')
        widget = urwid.Pile([header, body, divider], focus_item=2)

        return widget

    def selectable(self):
        return True

    def keypress(self, size, key):
        return key



class ListDetailWidget(urwid.WidgetWrap):
    """
    """
    # {user} opened this issue {time}
    # {title}
    # TODO{assignee}                        {milestone}
    # {body}
    # TODO{participants}

    HEADER_FORMAT = "{author} opened this issue {time}\n{title}"
    BODY_FORMAT = "{body}"

    def __init__(self, issue):
        self.issue = issue

        header_text = self._create_header(issue)
        body_text = self._create_body(issue)

        widget = self._build_widget(header_text, body_text)

        super().__init__(widget)

    def _create_header(self, issue):
        """
        Return the header text for the issue associated with this widget.
        """
        return self.HEADER_FORMAT.format(
            author=str(issue.user),
            time=time_since(issue.created_at),
            title=issue.title,
        )

    def _create_body(self, issue):
        return self.BODY_FORMAT.format(
            body=issue.body_text,
        )

    def _build_widget(self, header_text, body_text):
        """Return the wrapped widget."""

        header = urwid.AttrMap(urwid.Text(header_text), 'header')
        body = urwid.Padding(urwid.AttrMap(urwid.Text(body_text), 'body'), left=1, right=1)

        border_attr = 'line'
        issue_divider = '─'

        divider = urwid.AttrMap(urwid.Divider(issue_divider), border_attr, 'focus')
        widget = urwid.Pile([header, body, divider], focus_item=2)

        return widget

    def selectable(self):
        return True

    def keypress(self, size, key):
        return key

# -*- coding: utf-8 -*-

import time
from calendar import timegm

import urwid
from x256 import x256

from .config import ISSUE_DIVIDER, COMMENT_DIVIDER
from .events import trigger
from .models import is_issue, is_pull_request, is_open
from .func import unlines

def issue_title(issue):
    return urwid.Text([("title", issue.title)])


def issue_comments(issue):
    if not issue.comments:
        return urwid.Text("")

    if issue.comments == 1:
        text = "1 comment"
    else:
        text = "%s comments" % issue.comments

    return urwid.Text(("text", text))


def issue_author(issue):
    return urwid.Text([("username", str(issue.user)),
                       ("text", " opened this issue")])


def issue_time(issue):
    return urwid.Text([("time", time_since(issue.created_at))],
                      align='right',)


def issue_milestone(issue):
    if not issue.milestone:
        return urwid.Text("")

    text = "Milestone: %s" % issue.milestone.title
    return  urwid.Text([("milestone", text)],
                       align='right',)


def issue_assignee(issue):
    if not issue.assignee:
        return urwid.Text("")

    username = "%s" % str(issue.assignee)

    return urwid.Text([("username", username),  ("assignee", " is assigned")])


def pr_author(pr):
    return urwid.Text([("username", str(pr.user)),
                       ("text", " opened this pull request")])


def pr_comments(pr):
    comments = len([_ for _ in pr.iter_comments()])

    if not comments:
        return None

    if comments == 1:
        text = "1 comment"
    else:
        text = "%s comments" % comments

    return urwid.Text(("text", text))


def pr_commits(pr):
    commits = len([_ for _ in pr.iter_commits()])
    if commits == 1:
        text = "1 commit"
    else:
        text = "%s commits" % commits

    return urwid.Text(("text", text))


def pr_additions(pr):
    additions = sum([file.additions for file in pr.iter_files()])
    return urwid.Text([("green_text", "+"), ("text", " %s additions" % additions)])


def pr_deletions(pr):
    deletions = sum([file.deletions for file in pr.iter_files()])
    return urwid.Text([("red_text", "-"), ("text", " %s deletions" % deletions)])


def pr_diff(pr):
    raw_diff = bytes.decode(pr.diff())[2:]
    return raw_diff[:-1]



pr_title = issue_title
#pr_assignee = issue_assignee
#pr_milestone = issue_assignee
pr_time = issue_time


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


def create_label_attr(label):
    # TODO: sensible foreground color
    bg = "h%s" % x256.from_hex(label.color)
    return urwid.AttrSpec("black", bg)


def create_label_widget(label):
    attr = create_label_attr(label)

    label_name = " ".join(["", label.name, ""])

    return urwid.Text((attr, label_name))


def box(widget):
    return urwid.AttrMap(urwid.LineBox(widget), "line", "focus")


def make_divider():
    return urwid.AttrMap(urwid.Divider(ISSUE_DIVIDER), "divider")


def make_vertical_divider():
    return urwid.Padding(urwid.SolidFill("·"), left=1, right=1)


class UI(urwid.WidgetWrap):
    """
    Creates a curses interface for the program, providing functions to draw
    all the components of the UI.
    """
    HEADER_ISSUE_LIST = "{owner}/{repo}"
    HEADER_ISSUE_DETAIL = "{owner}/{repo} ─ Issue #{num}: {title}"
    HEADER_PR_DETAIL = "{owner}/{repo} ─ Pull Request #{num}: {title}"

    def __init__(self, repo):
        self.repo = repo
        self.views = {}

        header = urwid.Text("shipit")

        # body
        body = urwid.Text("shipit")

        # footer
        self.frame = urwid.Frame(body, header=header)

        super().__init__(self.frame)

    # -- API ------------------------------------------------------------------

    def get_focused_item(self):
        """
        Return the currently focused item when a Issue or Pull Request is
        focused.
        """
        body = self.frame.body

        widget = body.focus.focus

        if isinstance(body, Diff):
            focused = body.pr
        elif not widget:
            focused = None
        elif isinstance(widget, PRDetailWidget):
            focused = widget.pr
        else:
            focused = widget.issue if hasattr(widget, 'issue') else None

        issue_or_pr = is_issue(focused) or is_pull_request(focused)

        return focused if issue_or_pr else None

    def get_issue(self):
        """Return a issue if it"s focused, otherwise return ``None``."""
        issue = self.get_focused_item()
        return issue if is_issue(issue) else None

    # -- Modes ----------------------------------------------------------------

    def issues_and_pulls(self, issues_and_pulls):
        header_text = self.HEADER_ISSUE_LIST.format(owner=(str(self.repo.owner)),
                                                    repo=self.repo.name)
        self.frame.header.set_text(header_text)

        if isinstance(self.frame.body, ListWidget):
            self.frame.body.reset_list(issues_and_pulls)
            return

        if self.views.get("issues", None):
            body = self.views["issues"]
        else:
            body = ListWidget(self.repo, issues_and_pulls)
            self.views["issues"] = body
            #self.frame.body = body

        self.frame.set_body(body)

    def issue(self, issue):
        header_text = self.HEADER_ISSUE_DETAIL.format(owner=(str(self.repo.owner)),
                                                      repo=self.repo.name,
                                                      num=issue.number,
                                                      title=issue.title,)
        self.frame.header.set_text(header_text)
        body = issue_detail(issue)
        self.frame.set_body(body)

    def pull_request(self, pr):
        """Render a detail view for the `pr` pull request."""
        header_text = self.HEADER_PR_DETAIL.format(owner=(str(self.repo.owner)),
                                                   repo=self.repo.name,
                                                   num=pr.number,
                                                   title=pr.title,)
        self.frame.header.set_text(header_text)
        self.frame.body = pull_request_detail(pr)
        self.frame.set_body(self.frame.body)

    def diff(self, pr):
        self.frame.body = Diff(pr)
        self.frame.set_body(self.frame.body)


class IssueListWidget(urwid.WidgetWrap):
    """
    Widget containing a issue's basic information, meant to be rendered on a
    list.
    """
    HEADER_FORMAT = "#{num} ─ {title}       "
    BODY_FORMAT = "by {author}  {time}      {comments}"

    def __init__(self, issue):
        self.issue = issue

        widget = self._build_widget(issue)

        super().__init__(widget)

    @classmethod
    def _build_widget(cls, issue):
        """Return a widget for the ``issue``."""
        number = urwid.Text([("number", "#%s" % issue.number)])

        title = issue_title(issue)
        labels = cls._create_label_widgets(issue)
        title_labels = urwid.Columns([(60, title), labels])

        author = issue_author(issue)
        time = issue_time(issue)
        author_time = urwid.Columns([author, time])

        widget_list = [title_labels, author_time]

        if issue.assignee or issue.milestone:
            assignee = issue_assignee(issue)
            milestone = issue_milestone(issue)
            assignee_milestone = urwid.Columns([assignee, milestone])
            widget_list.append(assignee_milestone)

        if issue.comments:
            widget_list.append(issue_comments(issue))

        pile = urwid.Pile(widget_list)
        info = urwid.Columns([(5, number), pile])

        return box(info)

    @classmethod
    def _create_label_widgets(cls, issue):
        label_widgets = [create_label_widget(label) for label in issue.labels]
        return urwid.Columns(label_widgets)

    def selectable(self):
        return True

    def keypress(self, size, key):
        return key


class PRListWidget(IssueListWidget):
    """
    Widget containing a Pull Requests's basic information, meant to be rendered
    on a list.
    """
    @classmethod
    def _build_widget(cls, pr):
        """Return a widget for the ``pr``."""
        number = urwid.Text([("pull", "PR\n#%s" % pr.number)])

        title = pr_title(pr)

        author = pr_author(pr)
        time = pr_time(pr)
        author_time = urwid.Columns([author, time])

        widget_list = [title,
                       author_time,]

        comments = pr_comments(pr)
        if comments:
            widget_list.append(comments)

        pile = urwid.Pile(widget_list)
        widget = urwid.Columns([(5, number), pile])

        return box(widget)


def issue_detail(issue):
    comments = [IssueCommentWidget(issue, comment) for comment in issue.iter_comments()]
    comments.insert(0, IssueDetailWidget(issue))

    thread = urwid.ListBox(urwid.SimpleListWalker(comments))

    info_widgets = []
    if is_open(issue):
        state_indicator = urwid.Text(("green", " Open "), align='center')
    else:
        state_indicator = urwid.Text(("red", " Closed "), align='center')

    info_widgets.append(state_indicator)
    info_widgets.append(issue_comments(issue))

    label_widgets = [make_divider(), Legend("Labels"), urwid.Text("")]
    label_widgets.extend([create_label_widget(label) for label in issue.labels])

    info_widgets.extend(label_widgets)

    info = urwid.ListBox(urwid.SimpleListWalker(info_widgets))
    vertical_divider = make_vertical_divider()

    widget = urwid.Columns([(110, thread), (3, vertical_divider), info])

    return widget


def pull_request_detail(pr):
    comments = [PRCommentWidget(pr, comment) for comment in pr.iter_comments()]
    comments.insert(0, PRDetailWidget(pr))

    thread = urwid.ListBox(urwid.SimpleListWalker(comments))

    info_widgets = []
    if is_open(pr):
        state_indicator = urwid.Text(("green", " Open "), align='center')
    else:
        state_indicator = urwid.Text(("red", " Closed "), align='center')

    info_widgets.append(state_indicator)
    info_widgets.append(pr_commits(pr))

    additions = pr_additions(pr)
    deletions = pr_deletions(pr)

    info_widgets.append(additions)
    info_widgets.append(deletions)

    # TODO: don't allow selection
    info = urwid.ListBox(urwid.SimpleListWalker(info_widgets))

    vertical_divider = make_vertical_divider()

    widget = urwid.Columns([(110, thread), (3, vertical_divider), info])

    return widget


def issue_list(issues):
    for issue in issues:
        if is_issue(issue):
            yield IssueListWidget(issue)
        elif is_pull_request(issue):
            yield PRListWidget(issue)


class ListWidget(urwid.Columns):
    """
    A widget that represents a list of issues and Pull Requests, along with
    controls for sorting and filtering the aforementioned entities.
    """
    def __init__(self, repo, items):
        issue_widgets = [w for w in issue_list(items)]

        self.issues = urwid.ListBox(urwid.SimpleListWalker(issue_widgets))
        vertical_divider = make_vertical_divider()
        self.controls = Controls(repo, items)

        super().__init__([(90, self.issues),
                          (3, vertical_divider),
                          self.controls])

    def reset_list(self, items):
        widgets = [w for w in issue_list(items)]
        list_walker = self.issues.body
        del list_walker[:]
        list_walker.extend(widgets)


class Controls(urwid.ListBox):
    # TODO: Milestone
    # TODO: Assigned to you, Created by you
    def __init__(self, repo, issues):
        self.repo = repo
        self.issues = issues

        widgets = self._build_widgets()

        super().__init__(urwid.SimpleListWalker(widgets))

    def _build_widgets(self):
        br = Legend("")
        controls = []
        # Open/Closed/Pull Request
        controls.append(Legend("Filter by state\n"))
        filters = []
        controls.extend([OpenIssuesFilter(filters),
                         ClosedIssuesFilter(filters),
                         PullRequestsFilter(filters),])
        controls.append(br)

        # Labels
        labels = [LabelWidget(label) for label in self.repo.iter_labels()]
        labels.insert(0, Legend("Filter by label\n"))

        controls.extend(labels)
        controls.append(br)

        return controls

    def get_focused(self):
        pass


class Legend(urwid.Text):
    def __init__(self, text):
        super().__init__(("legend", text))

    def selectable(self):
        return False


class RadioButtonWrap(urwid.WidgetWrap):
    def __init__(self, filters, label, check=None):
        self.chec = check

        widget = urwid.RadioButton(filters, label)

        urwid.connect_signal(widget, "change", self.on_change)

        super().__init__(widget)


    def on_change(self, checkbox, new_state):
        if new_state and callable(self.on_check):
            self.on_check()

    def on_check(self):
        pass


class OpenIssuesFilter(RadioButtonWrap):
    def __init__(self, filters):
        super().__init__(filters, "Open")

    def on_check(self):
        trigger("show_open_issues")


class ClosedIssuesFilter(RadioButtonWrap):
    def __init__(self, filters):
        super().__init__(filters, "Closed")

    def on_check(self):
        trigger("show_closed_issues")


class PullRequestsFilter(RadioButtonWrap):
    def __init__(self, filters):
        super().__init__(filters, "Pull Requests")

    def on_check(self):
        trigger("show_pull_requests")


class LabelWidget(urwid.WidgetWrap):
    """Represent a label."""
    def __init__(self, label):
        checkbox = urwid.AttrMap(urwid.CheckBox(" "), "checkbox", "focus")
        label_widget = create_label_widget(label)
        widget = urwid.Columns([(5, checkbox), label_widget])
        super().__init__(widget)


class IssueDetailWidget(urwid.WidgetWrap):
    """
    A widget for rendering an issue in detail . It includes all the information
    regarding the issue.

    Includes the following information:

         ---------------------------------
        |{title}                          |
        |{user} opened this issue {time}  |
        |{assignee}           {milestone} |
        |{participants}                   |
        |---------------------------------|
        |{body}                           |
         ---------------------------------
    """
    # TODO: participants
    BODY_FORMAT = "{body}"

    def __init__(self, issue):
        self.issue = issue
        widget = self._build_widget(issue)
        super().__init__(widget)

    @classmethod
    def _build_widget(cls, issue):
        """Return a widget for the ``issue``."""
        header = cls._create_header_widget(issue)
        if issue.body_text:
            body = cls._create_body_widget(issue)
            divider = make_divider()
            widget = urwid.Pile([header, divider, body])
        else:
            widget = header

        return box(widget)

    @classmethod
    def _create_header_widget(cls, issue):
        title = issue_title(issue)
        labels = urwid.Columns([create_label_widget(label) for label in issue.labels])
        title_labels = urwid.Columns([(60, title), labels])

        author = issue_author(issue)
        time = issue_time(issue)
        author_time = urwid.Columns([author, time])

        assignee = issue_assignee(issue)
        milestone = issue_milestone(issue)
        assignee_milestone = urwid.Columns([assignee, milestone])

        widget = urwid.Pile([title_labels, author_time, assignee_milestone])

        return widget

    @classmethod
    def _create_body_widget(cls, issue):
        text = cls.BODY_FORMAT.format(
            body=issue.body_text,
        )
        widget = urwid.Text(["\n", ("body", text)])
        return urwid.Padding(widget, left=2, right=2)

    def selectable(self):
        return True

    def keypress(self, size, key):
        return key



class IssueCommentWidget(urwid.WidgetWrap):
    def __init__(self, issue, comment):
        self.issue = issue
        self.comment = comment

        widget = self._build_widget(issue, comment)

        super().__init__(widget)

    @classmethod
    def _build_widget(cls, issue, comment):
        """Return the wrapped widget."""
        header = cls._create_header(comment)
        body = cls._create_body(comment)

        divider = make_divider()

        widget = urwid.Pile([header, divider, body])

        return box(widget)

    @classmethod
    def _create_header(cls, comment):
        """
        Return the header text for the comment associated with this widget.
        """
        author = cls.comment_author(comment)
        time = cls.comment_time(comment)

        return urwid.Columns([author, time])

    @classmethod
    def _create_body(cls, comment):
        widget = urwid.Text(("body", comment.body_text))
        return urwid.Padding(widget, left=2, right=2)

    @staticmethod
    def comment_author(comment):
        return urwid.Text([("username", str(comment.user)),
                           ("text", " commented")],)

    @staticmethod
    def comment_time(comment):
        return urwid.Text(("time", time_since(comment.created_at)),
                          align='right',)

    def selectable(self):
        return True

    def keypress(self, size, key):
        return key


class PRDetailWidget(urwid.WidgetWrap):
    """
    Includes the following information:

         ---------------------------------
        |{title}                          |
        |{user} opened this pr     {time} |
        |{assignee}           {milestone} |
        |{participants}                   |
        |---------------------------------|
        |{body}                           |
         ---------------------------------
        |{merge_status}                   |
         ---------------------------------
    """
    # TODO: participants
    def __init__(self, pr):
        self.pr = pr
        widget = self._build_widget(pr)
        super().__init__(widget)

    @classmethod
    def _build_widget(cls, pr):
        """Return a widget for the ``pr``."""
        title = pr_title(pr)

        author = pr_author(pr)
        time = pr_time(pr)
        author_time = urwid.Columns([author, time])

        widget_list = [title, author_time]

        #assignee = pr_assignee(pr)
        #milestone = pr_milestone(pr)
        #assignee_milestone = urwid.Columns([assignee, milestone])
        divider = make_divider()

        body = cls._create_body_widget(pr)

        if pr.body:
            widget_list.extend([divider, body])

        # FIXME: is this always false? maybe a bug in the library
        if pr.mergeable:
            mergeable = urwid.Text(("green", "Can be automatically merged"))
        else:
            mergeable = urwid.Text(("red", "Can't be automatically merged"))
        widget_list.extend([divider, mergeable])

        widget = urwid.Pile(widget_list)

        return box(widget)

    @classmethod
    def _create_body_widget(cls, pr):
        widget = urwid.Text(["\n", ("body", pr.body_text)])
        return urwid.Padding(widget, left=2, right=2)

    def selectable(self):
        return True

    def keypress(self, size, key):
        return key


# TODO: Base CommentWidget
class PRCommentWidget(IssueCommentWidget):
    def __init__(self, pr, comment):
        self.pr = pr
        self.comment = comment

        header_text = self._create_header(comment)
        body_text = self._create_body(comment)

        widget = self._build_widget(header_text, body_text)

        super(IssueCommentWidget, self).__init__(widget)

    @classmethod
    def _create_body(cls, comment):
        return cls.BODY_FORMAT.format(
            body=comment.body,
        )


class Diff(urwid.ListBox):
    def __init__(self, pr):
        self.pr = pr
        self.diff = pr_diff(pr)
        super().__init__(urwid.SimpleListWalker([l for l in
                                                 self._build_lines(self.diff)]))

    @staticmethod
    def _build_lines(diff):
        for line in unlines(diff):
            if line.startswith("ff"):
                yield urwid.Text(("text", line))
            elif line.startswith("index"):
                yield urwid.Text(("text", line))
            elif line.startswith("@@"):
                yield urwid.Text(("cyan_text", line))
            elif line.startswith("+++"):
                yield urwid.Text(("text", line))
            elif line.startswith("+"):
                yield urwid.Text(("green_text", line))
            elif line.startswith("---"):
                yield urwid.Text(("text", line))
            elif line.startswith("-"):
                yield urwid.Text(("red_text", line))
            else:
                yield urwid.Text(("code", line))

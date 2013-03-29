from github3.issues import Issue
from github3.pulls import PullRequest


def is_issue(item):
    return isinstance(item, Issue)


def is_open(item):
    if hasattr(item, "state"):
        return item.state == "open"


def is_closed(item):
    if hasattr(item, "state"):
        return item.state == "closed"


def is_pull_request(item):
    return isinstance(item, PullRequest)

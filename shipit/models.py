from github3.issues import Issue
from github3.pulls import PullRequest


def is_issue(item):
    return isinstance(item, Issue)


def is_pull_request(item):
    return isinstance(item, PullRequest)

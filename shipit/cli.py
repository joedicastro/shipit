import os
import tempfile
import subprocess
from argparse import ArgumentParser

from .ui import UI
from .core import Shipit
from .auth import login


ERR_NO_REPO_SPECIFIED = 1
ERR_UNABLE_TO_FIND_REMOTE = 2
ERR_ORIGIN_REMOTE_NOT_FOUND = 3

VERSION = "alpha"


def extract_user_and_repo_from_remote(remote_url):
    # TODO: name slices
    if remote_url.startswith('git://'):
        # Git remote
        user_repo = remote_url.split('/')[3:]
        user, repo = user_repo[0], user_repo[1][:-4]
    elif remote_url.startswith('http'):
        # HTTP[S] remote
        user_repo = remote_url.split('/')[3:]
        user, repo = user_repo[0], user_repo[1][:-4]
    else:
        # SSH remote
        user_repo = remote_url.split(':')[1][:-4]
        user, repo = tuple(user_repo.split('/'))

    return user, repo


def get_remotes():
    """
    Get a list of the git remote URLs for this repository.

    Return a dictionary of remote names mapped to URL strings if remotes were
    found.

    Otherwise return ``None``.
    """
    tmp_file = tempfile.NamedTemporaryFile(mode='w+', delete=False)

    retcode = subprocess.call(['git', 'remote', '-v'], stdout=tmp_file.file)

    # Store the output of the command and delete temporary file
    tmp_file.file.seek(0)
    raw_remotes = tmp_file.read()
    os.remove(tmp_file.name)

    # Get the GitHub remote strings
    nonempty_remotes = [r for r in raw_remotes.split('\n') if 'github' in r]

    # Process the raw remotes for returning a list of URLs
    def remote_name_and_url(remotestring):
        name_url = remotestring.split(' ')[0]
        return tuple(name_url.split('\t'))

    # Extract the url for each remote string
    remotes = dict(remote_name_and_url(r) for r in nonempty_remotes)

    return remotes if retcode == 0 else None


def read_arguments():
    """Read arguments from the command line."""

    parser_title = "shipit"
    parser = ArgumentParser(parser_title)

    # Repo
    parser.add_argument("user/repository",
                        nargs='?',
                        default="",
                        help="The repository to show")

    # version
    version = "shipit %s" % VERSION
    parser.add_argument("-v",
                        "--version",
                        action="version",
                        version=version,
                        help="Show the current version of shipit")

    args = parser.parse_args()

    # Coerce `args` to a dictionary
    return vars(args)


def main():
    args = read_arguments()

    api = login()

    # Get the user and repository that we are we going to manage
    user_repo_arg = args['user/repository'].strip()

    if not user_repo_arg:
        remotes = get_remotes()

        if remotes is None:
            # We aren't in a git repo
            exit(ERR_NO_REPO_SPECIFIED)
        elif not remotes:
            # No github remotes were found
            exit(ERR_UNABLE_TO_FIND_REMOTE)

        # Get the user and repo from the `origin` remote
        remote = remotes.get('origin', None)
        if remote is None:
            exit(ERR_ORIGIN_REMOTE_NOT_FOUND)

        USER, REPO = extract_user_and_repo_from_remote(remote)
    elif '/' in user_repo_arg:
        # Assume that we got a <username>/<repository>
        USER, REPO = user_repo_arg.split('/')
    else:
        # If a `/` isn't included, assume that it's the name of the repository
        # and the logged in user owns it
        USER, REPO = str(api.user()), user_repo_arg

    # fetch repo
    repo = api.repository(USER, REPO)

    # create view
    ui = UI(repo)

    # create controller
    shipit = Shipit(ui, repo)

    shipit.start()

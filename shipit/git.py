import os
import tempfile
import subprocess


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
    # Extract the url for each remote string
    remotes = dict(remote_name_and_url(r) for r in nonempty_remotes)

    return remotes if retcode == 0 else None


def remote_name_and_url(remotestring):
    """
    Given a remote string from the output of the ``git remote -v`` command,
    return a tuple of the name and URL of the remote.
    """
    name_url = remotestring.split(' ')[0]
    return tuple(name_url.split('\t'))


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

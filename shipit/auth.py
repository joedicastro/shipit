import os
from getpass import getpass
from configparser import ConfigParser

from github3 import authorize
from github3 import login as github_login

from shipit import DESCRIPTION


# Path to config file
CONFIG_FILE = os.path.join(os.environ['HOME'], '.shipit')

# The entities which our application can modify
SCOPES = ['repo']


def login():
    # Do we have the credentials stored?
    c = ConfigParser()
    c.read(CONFIG_FILE)

    if c.has_section('credentials'):
        # Get the token from the config file
        token = c.get('credentials', 'token').strip()
    else:
        # Ask for credentials
        print("Please insert your GitHub credentials below:")
        user = input("Username: ").strip()
        password = getpass()

        auth = authorize(user, password, SCOPES, DESCRIPTION)
        token = auth.token

        # Save credentials to the config file
        c.add_section('credentials')
        c.set('credentials', 'token', str(token))
        c.set('credentials', 'id', str(auth.id))

        with open(CONFIG_FILE, 'w') as f:
            c.write(f)

    return github_login(token=token)

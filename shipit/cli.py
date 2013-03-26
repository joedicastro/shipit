from argparse import ArgumentParser

from .ui import UI
from .core import Shipit
from .secrets import USER, PASSWORD
from .auth import login


VERSION = "alpha"

USER, REPO = 'alejandrogomez', 'shipit'


def read_arguments():
    """Read arguments from the command line."""

    parser_title = "shipit"
    parser = ArgumentParser(parser_title)

    # version
    version = "shipit %s" % VERSION
    parser.add_argument("-v",
                        "--version",
                        action="version",
                        version=version,
                        help="Show the current version of shipit")

    args = parser.parse_args()
    return args


def main():
    args = read_arguments()

    # fetch repo
    repo = login().repository(USER, REPO)

    # create view
    ui = UI(repo)

    # create controller
    shipit = Shipit(ui, repo)

    shipit.start()

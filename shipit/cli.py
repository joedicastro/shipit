from argparse import ArgumentParser

from github3 import login

from ui import UI
from core import Shipit
from secrets import USER, PASSWORD


VERSION = "alpha"


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


if __name__ == "__main__":
    args = read_arguments()

    # create view
    ui = UI()

    # create API
    api = login(USER, PASSWORD)

    # create controller
    shipit = Shipit(ui, api)

    shipit.start()

# shipit

A (Work In Progress) interface to GitHub issues written in Python 3.

The goal of this project is to create a keyboard-driven console application
that can be used to manage your issues and pull requests.

## Usage

For the moment you'll have to navigate with the arrow keys, although I'll
vimify it soon ☺

The available actions are:

`O` for opening an issue.

`R` for reopening closed issues.

`C` closes an issue.

`c` comments on an issue or pull request.

`e` for editing a issue or pull request text (soon for comments too).

`return` shows the selected issue or pull request with more detail.

`d` shows the diff when viewing a pull request in detail.

`esc` takes you back to the previous screen.

## Installation

If you downloaded the source code

    $ python setup.py install


## License

`shipit` is licensed under a GPLv3 license, see `LICENSE` for details.

## Authors

Alejandro Gómez.

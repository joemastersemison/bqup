from docopt import docopt

import bqup.main as main


def _parse(argv):
    return docopt(main.__doc__, argv=argv)


def test_changed_since_long_flag():
    args = _parse(["--changed-since", "7"])
    assert args["--changed-since"] == "7"


def test_changed_since_short_flag():
    args = _parse(["-c", "14"])
    assert args["--changed-since"] == "14"


def test_changed_since_defaults_to_none():
    args = _parse([])
    assert args["--changed-since"] is None

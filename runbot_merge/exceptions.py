from difflib import Differ
from typing import Iterator


class MergeError(Exception):
    pass


class FastForwardError(Exception):
    pass


class Mismatch(MergeError):
    def __init__(self, pr, diffable, invalid) -> None:
        diff = ''.join(Differ().compare(
            list(format_for_difflib((n, v) for n, v, _ in diffable)),
            list(format_for_difflib((n, v) for n, _, v in diffable)),
        ))
        super().__init__(pr, diff, invalid)


def format_for_difflib(items: Iterator[tuple[str, object]]) -> Iterator[str]:
    """ Bit of a pain in the ass because difflib really wants
    all lines to be newline-terminated, but not all values are
    actual lines, and also needs to split multiline values.
    """
    for name, value in items:
        yield name + ':\n'
        value = str(value)
        if not value.endswith('\n'):
            value += '\n'
        yield from value.splitlines(keepends=True)
        yield '\n'


class Unmergeable(MergeError):
    pass


class Skip(MergeError):
    pass


class InconsistentIntegration(Exception):
    pass

# SPDX-FileCopyrightText: 2023 Phu Hung Nguyen <phuhnguyen@outlook.com>
# SPDX-License-Identifier: LGPL-2.1-or-later

import re

from typing import Callable, Protocol, Tuple, List

SPACES_PATTERN = re.compile(r'\s+')
HARD_LINE_BREAK_PATTERN = re.compile(r'(?: {2,}|\\)\n *')
SINGLE_COMMENT_PATTERN = re.compile('((?://|#) *)(.*)')


# extraction
class I18NEntryProtocol(Protocol):
    msgid: str
    occurrences: List[Tuple[str, int]]
    comment: str
    msgctxt: str


class DomainExtractionProtocol(Protocol):
    entries: List[I18NEntryProtocol]

    def add_entry(self, path: str, msgid: str, line_num: int, comment: str = '', msgctxt: str = ''):
        ...

    def render_front_matter(self, path: str, content: str, markup: str):
        ...


# generation
class L10NResult:
    """Localized content, total number of messages, number of translations.
    If there are no messages, rate will be -1
    """
    def __init__(self, localized, total_count: int, l10n_count: int):
        self.localized = localized
        self.total_count = total_count
        self.l10n_count = l10n_count

    def __str__(self):
        return f'({self.l10n_count}/{self.total_count})'

    def __add__(self, other: 'L10NResult'):
        localized = self.localized + other.localized
        total_count = self.total_count + other.total_count
        l10n_count = self.l10n_count + other.l10n_count
        return L10NResult(localized, total_count, l10n_count)

    @property
    def rate(self):
        return self.l10n_count / self.total_count if self.total_count > 0 else -1


L10NFunc = Callable[[str], str]


class DomainGenerationProtocol(Protocol):
    l10n_func: L10NFunc

    def render_front_matter(self, content: str, markup: str):
        ...

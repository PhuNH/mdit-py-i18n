# SPDX-FileCopyrightText: 2023 Phu Hung Nguyen <phuhnguyen@outlook.com>
# SPDX-License-Identifier: LGPL-2.1-or-later

import importlib.resources as pkg_resources
import unittest
from dataclasses import dataclass, field
from typing import List, Tuple

from markdown_it import MarkdownIt
from mdit_py_plugins.deflist import deflist_plugin
from mdit_py_plugins.front_matter import front_matter_plugin

from mdit_py_i18n.renderer_i18n import RendererMarkdownI18N


@dataclass
class I18NEntry:
    msgid: str
    occurrences: List[Tuple[str, int]] = field(default_factory=list)
    comment: str = ''
    msgctxt: str = ''


class DomainExtraction:
    def __init__(self):
        self.entries: List[I18NEntry] = []

    def add_entry(self, path: str, msgid: str, line_num: int, comment: str = '', msgctxt: str = ''):
        self.entries.append(I18NEntry(msgid, [(path, line_num)], comment, msgctxt))


class RendererMarkdownI18NTestCase(unittest.TestCase):
    mdi = MarkdownIt(renderer_cls=RendererMarkdownI18N).use(front_matter_plugin)\
        .enable('table').use(deflist_plugin)

    def test_renderer(self):
        path = 'renderer.md'
        domain_e = DomainExtraction()
        with pkg_resources.open_text('tests.resources', path) as f_obj:
            env = {
                'path': path,
                'domain_extraction': domain_e
            }
            tokens = self.mdi.parse(f_obj.read(), env)
        # skip front matter
        self.mdi.renderer.render(tokens[1:], self.mdi.options, env)
        self.assertEqual(21, len(domain_e.entries))


if __name__ == '__main__':
    unittest.main()

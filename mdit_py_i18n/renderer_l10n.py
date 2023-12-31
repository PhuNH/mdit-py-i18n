# SPDX-FileCopyrightText: 2023 Phu Hung Nguyen <phuhnguyen@outlook.com>
# SPDX-License-Identifier: LGPL-2.1-or-later

"""Render localized markdown"""

import inspect
import textwrap
from dataclasses import dataclass
from typing import Sequence, Tuple, List

import pygments.token
from markdown_it import MarkdownIt
from markdown_it.token import Token
from markdown_it.utils import OptionsDict, EnvType
from pygments import lexers, util

from . import utils
from .utils import L10NResult, DomainGenerationProtocol

SETEXT_HEADING_MARKUPS = {'-', '='}
ORDERED_LIST_MARKUPS = {'.', ')'}


class MdCtx:
    def __init__(self, env: EnvType):
        self.line_indent = ''
        self.indent_1st_line = ''  # list item, definition detail, atx heading
        self.indent_1st_line_len = 0
        self.indents: List[int] = []
        self.setext_heading = ''
        self.table_sep = ''
        self.in_table = False
        self.parse_fence = env.get('parse_fence', False)
        self.domain_g: DomainGenerationProtocol = env['domain_generation']

    def get_line_indent(self):
        if not self.indent_1st_line:
            return self.line_indent
        if self.indent_1st_line_len > 0:
            line_indent = self.line_indent[:-self.indent_1st_line_len] + self.indent_1st_line
        else:
            line_indent = self.line_indent + self.indent_1st_line
        self.indent_1st_line = ''
        self.indent_1st_line_len = 0
        return line_indent


@dataclass
class _FenceCtx:
    localized: str = ''  # the l10n result
    # temporary content of the comment being parsed
    # also indicates whether we are parsing a comment or not
    comment: str = ''
    comment_markup: str = ''
    indent: str = ''  # things on the same line before the comment
    next_indent: str = ''  # a second field when 'indent' is busy


class RendererMarkdownL10N:
    """
    Implements `RendererProtocol`
    """
    __output__ = 'md'

    def __init__(self, mdi: MarkdownIt):
        self.rules = {
            k: v
            for k, v in inspect.getmembers(self, predicate=inspect.ismethod)
            if not (k.startswith("render") or k.startswith("_"))
        }
        self.mdi = mdi

    def render(self, tokens: Sequence[Token], _options: OptionsDict, env: EnvType) -> Tuple[L10NResult, L10NResult]:
        """
        :param tokens: list of block tokens to render
        :param _options: properties of parser instance
        :param env: containing 'domain_generation' an object compatible with `DomainGenerationProtocol`
        :return: an `L10NResult`
        """
        md_ctx = MdCtx(env)

        if (token := tokens[0]).type == 'front_matter':
            fm_result = md_ctx.domain_g.render_front_matter(token.content, token.markup)
            tokens = tokens[1:]
        else:
            fm_result = L10NResult('', 0, 0)

        content_result = L10NResult('', 0, 0)
        for i, token in enumerate(tokens):
            if token.type in self.rules:
                r = self.rules[token.type](tokens, i, md_ctx, content_result)
                if r == -1:
                    break
        self._link_ref(env, md_ctx, content_result)

        return fm_result, content_result

    @staticmethod
    def _link_ref(env: EnvType, md_ctx: MdCtx, content_result: L10NResult):
        refs = env.get('references', {}).items()
        if len(refs) == 0:
            return
        content_result.localized += '\n'
        for ref, details in refs:
            href = details['href']
            content_result.localized += f'[{ref}]: {href}'
            if title := details.get('title', ''):
                localized_title = md_ctx.domain_g.l10n_func(title)
                if localized_title is not title:
                    content_result.l10n_count += 1
                content_result.total_count += 1
                content_result.localized += f' "{localized_title}"'
            content_result.localized += '\n'

    # TODO: parameterize: fence code comment i18n, wrap width, comment identifiers
    # TODO: multiline comment?
    @staticmethod
    def _fence_comment(fence_ctx: _FenceCtx, md_ctx: MdCtx, content_result: L10NResult):
        localized_comment = md_ctx.domain_g.l10n_func(fence_ctx.comment)
        if localized_comment is not fence_ctx.comment:
            content_result.l10n_count += 1
        content_result.total_count += 1
        subsequent_indent = ' ' * len(fence_ctx.indent) if fence_ctx.indent.strip() else fence_ctx.indent
        comment_lines = textwrap.wrap(localized_comment,
                                      100,
                                      initial_indent=f'{fence_ctx.indent}{fence_ctx.comment_markup}',
                                      subsequent_indent=f'{subsequent_indent}{fence_ctx.comment_markup}')
        for line in comment_lines:
            fence_ctx.localized += f'{line}\n'
        fence_ctx.comment = ''

    @classmethod
    def _fence(cls, token: Token, md_ctx: MdCtx, content_result: L10NResult):
        if not md_ctx.parse_fence:
            return token.content

        try:
            lexer = lexers.get_lexer_by_name(token.info)
        except util.ClassNotFound:
            lexer = lexers.guess_lexer(token.content)
        code_toks = lexer.get_tokens(token.content)

        # values to use in _fence_comment function
        fence_ctx = _FenceCtx()
        # number of the last line with a comment token
        last_comment_line_num = 0
        # the token starts with one line of the fence, then the content. +1: 0-base -> 1-base
        line_num = token.map[0] + 1 + 1

        # concatenate comment tokens until either a non-comment token or a blank line or end of token stream
        for tok_type, tok_val in code_toks:
            if tok_type == pygments.token.Token.Comment.Single:
                # when another comment is already being parsed and there's a blank line
                if fence_ctx.comment and line_num - last_comment_line_num > 1:
                    cls._fence_comment(fence_ctx, md_ctx, content_result)
                    last_nl = fence_ctx.next_indent.rfind('\n')
                    fence_ctx.localized += fence_ctx.next_indent[:last_nl + 1]
                    fence_ctx.indent = fence_ctx.next_indent[last_nl + 1:]
                if fence_ctx.comment != '':
                    fence_ctx.comment += ' '
                if comment_match := utils.SINGLE_COMMENT_PATTERN.match(tok_val):
                    fence_ctx.comment += comment_match.group(2).strip()
                    fence_ctx.comment_markup = comment_match.group(1)
                last_comment_line_num = line_num
            else:
                if fence_ctx.comment:
                    if tok_val.strip():
                        cls._fence_comment(fence_ctx, md_ctx, content_result)
                        fence_ctx.indent = fence_ctx.next_indent + tok_val
                        fence_ctx.next_indent = ''
                    else:
                        fence_ctx.next_indent = '' if tok_val == '\n' else tok_val
                else:
                    last_nl = tok_val.rfind('\n')
                    if last_nl != -1:
                        fence_ctx.localized += fence_ctx.indent + tok_val[:last_nl + 1]
                        fence_ctx.indent = tok_val[last_nl + 1:]
                    else:
                        fence_ctx.indent += tok_val
            line_num += tok_val.count('\n')
        if fence_ctx.comment:
            cls._fence_comment(fence_ctx, md_ctx, content_result)
        return fence_ctx.localized

    @classmethod
    def inline(cls, tokens: Sequence[Token], idx: int, md_ctx: MdCtx, content_result: L10NResult):
        token = tokens[idx]
        content = utils.HARD_LINE_BREAK_PATTERN.sub('<br />', token.content.strip())
        content = utils.SPACES_PATTERN.sub(' ', content.replace('\n', ' '))
        if content and not utils.SPACES_PATTERN.fullmatch(content):
            localized_content = md_ctx.domain_g.l10n_func(content)
        else:
            localized_content = content
        if localized_content is not content:
            content_result.l10n_count += 1
        content_result.total_count += 1
        if md_ctx.in_table:
            content_result.localized += localized_content
        else:
            content_result.localized += f'{md_ctx.get_line_indent()}{localized_content}'

    # blockquote
    # TODO: blockquote inside list
    @classmethod
    def blockquote_open(cls, tokens: Sequence[Token], idx: int, md_ctx: MdCtx, _content_result: L10NResult):
        token = tokens[idx]
        md_ctx.line_indent = f'{md_ctx.get_line_indent()}{token.markup} '

    @classmethod
    def blockquote_close(cls, _tokens: Sequence[Token], _idx: int, md_ctx: MdCtx, content_result: L10NResult):
        md_ctx.line_indent = md_ctx.line_indent[:-2]
        content_result.localized += f'{md_ctx.line_indent}\n'

    # heading
    @classmethod
    def heading_open(cls, tokens: Sequence[Token], idx: int, md_ctx: MdCtx, _content_result: L10NResult):
        token = tokens[idx]
        if token.markup not in SETEXT_HEADING_MARKUPS:
            md_ctx.indent_1st_line += f'{token.markup} '
            # md_ctx.indent_1st_line_len += 0
            # md_ctx.line_indent += ' ' * 0
            md_ctx.indents.append(0)
        else:
            md_ctx.setext_heading = token.markup

    @classmethod
    def heading_close(cls, _tokens: Sequence[Token], _idx: int, md_ctx: MdCtx, content_result: L10NResult):
        if md_ctx.setext_heading:
            content_result.localized += f'\n{md_ctx.get_line_indent()}{md_ctx.setext_heading}'
            md_ctx.setext_heading = ''
        else:
            md_ctx.indents.pop()
            # the added len is 0, so line_indent remains the same
        content_result.localized += '\n'

    # thematic break
    @classmethod
    def hr(cls, tokens: Sequence[Token], idx: int, md_ctx: MdCtx, content_result: L10NResult):
        token = tokens[idx]
        # always use '_' here to differentiate this from setext headings and bullet list items
        content_result.localized += f'{md_ctx.get_line_indent()}{len(token.markup) * "_"}\n'

    # list
    # TODO: loose lists?
    @classmethod
    def list_item_open(cls, tokens: Sequence[Token], idx: int, md_ctx: MdCtx, _content_result: L10NResult):
        token = tokens[idx]
        markup = f'{token.info}{token.markup}' if token.markup in ORDERED_LIST_MARKUPS else f'{token.markup}'
        md_ctx.indent_1st_line += f'{markup} '
        added_len = len(markup) + 1
        md_ctx.indent_1st_line_len += added_len
        md_ctx.line_indent += ' ' * added_len
        md_ctx.indents.append(added_len)

    @classmethod
    def list_item_close(cls,
                        _tokens: Sequence[Token],
                        _idx: int,
                        md_ctx: MdCtx,
                        _content_result: L10NResult):
        latest_len = md_ctx.indents.pop()
        md_ctx.line_indent = md_ctx.line_indent[:-latest_len]

    @classmethod
    def bullet_list_close(cls,
                          tokens: Sequence[Token],
                          idx: int,
                          md_ctx: MdCtx,
                          content_result: L10NResult):
        # add a blank line when next token is not a closing one
        if idx < len(tokens) - 1 and tokens[idx + 1].nesting != -1:
            content_result.localized += f'{md_ctx.line_indent}\n'

    @classmethod
    def ordered_list_close(cls,
                           tokens: Sequence[Token],
                           idx: int,
                           md_ctx: MdCtx,
                           content_result: L10NResult):
        cls.bullet_list_close(tokens, idx, md_ctx, content_result)

    # paragraph
    @classmethod
    def paragraph_close(cls, tokens: Sequence[Token], idx: int, md_ctx: MdCtx, content_result: L10NResult):
        content_result.localized += '\n'
        if idx < len(tokens) - 1:
            next_token = tokens[idx + 1]
            # add a blank line when next token is a setext heading_open, an HTML block, an indented code block,
            # a paragraph open, or a definition list open
            if (next_token.type == 'heading_open' and next_token.markup in SETEXT_HEADING_MARKUPS) \
                    or next_token.type in {'code_block', 'html_block', 'paragraph_open', 'dl_open'}:
                content_result.localized += f'{md_ctx.line_indent}\n'

    # indented code block
    @classmethod
    def code_block(cls, tokens: Sequence[Token], idx: int, md_ctx: MdCtx, content_result: L10NResult):
        token = tokens[idx]
        localized_code_block = token.content.replace('\n', f'\n{md_ctx.line_indent}    ')
        content_result.localized += f'{md_ctx.get_line_indent()}    {localized_code_block}\n'

    # fenced code block
    @classmethod
    def fence(cls, tokens: Sequence[Token], idx: int, md_ctx: MdCtx, content_result: L10NResult):
        token = tokens[idx]
        localized_fence = cls._fence(token, md_ctx, content_result)
        localized_fence = localized_fence.replace('\n', f'\n{md_ctx.line_indent}')
        # a newline is at the end of token.content already, so we only need to append token.markup there
        content_result.localized += f'''{md_ctx.get_line_indent()}{token.markup}{token.info}
{md_ctx.line_indent}{localized_fence}{token.markup}
'''

    # html block
    @classmethod
    def html_block(cls, tokens: Sequence[Token], idx: int, md_ctx: MdCtx, content_result: L10NResult):
        token = tokens[idx]
        localized_html = md_ctx.domain_g.l10n_func(token.content)
        if localized_html is not token.content:
            content_result.l10n_count += 1
        content_result.total_count += 1
        localized_html = localized_html.replace('\n', f'\n{md_ctx.line_indent}')
        content_result.localized += f'{md_ctx.get_line_indent()}{localized_html}\n'

    # table
    @classmethod
    def table_open(cls, _tokens: Sequence[Token], _idx: int, md_ctx: MdCtx, _content_result: L10NResult):
        md_ctx.in_table = True

    @classmethod
    def tr_open(cls, _tokens: Sequence[Token], _idx: int, md_ctx: MdCtx, content_result: L10NResult):
        content_result.localized += f'{md_ctx.get_line_indent()}|'

    @classmethod
    def th_open(cls, _tokens: Sequence[Token], _idx: int, md_ctx: MdCtx, content_result: L10NResult):
        content_result.localized += ' '
        md_ctx.table_sep += '| --- '

    @classmethod
    def th_close(cls, _tokens: Sequence[Token], _idx: int, _md_ctx: MdCtx, content_result: L10NResult):
        content_result.localized += ' |'

    @classmethod
    def thead_close(cls, _tokens: Sequence[Token], _idx: int, md_ctx: MdCtx, content_result: L10NResult):
        md_ctx.table_sep += '|\n'
        content_result.localized += f'{md_ctx.line_indent}{md_ctx.table_sep}'
        md_ctx.table_sep = ''

    @classmethod
    def td_open(cls, _tokens: Sequence[Token], _idx: int, _md_ctx: MdCtx, content_result: L10NResult):
        content_result.localized += ' '

    @classmethod
    def td_close(cls, _tokens: Sequence[Token], _idx: int, _md_ctx: MdCtx, content_result: L10NResult):
        content_result.localized += ' |'

    @classmethod
    def tr_close(cls, _tokens: Sequence[Token], _idx: int, _md_ctx: MdCtx, content_result: L10NResult):
        content_result.localized += '\n'

    @classmethod
    def table_close(cls, _tokens: Sequence[Token], _idx: int, md_ctx: MdCtx, content_result: L10NResult):
        content_result.localized += f'{md_ctx.line_indent}\n'
        md_ctx.in_table = False

    # definition list
    @classmethod
    def dd_open(cls, _tokens: Sequence[Token], _idx: int, md_ctx: MdCtx, _content_result: L10NResult):
        md_ctx.indent_1st_line += f': '
        md_ctx.indent_1st_line_len += 2
        md_ctx.line_indent += ' ' * 2
        md_ctx.indents.append(2)

    @classmethod
    def dd_close(cls, _tokens: Sequence[Token], _idx: int, md_ctx: MdCtx, content_result: L10NResult):
        latest_len = md_ctx.indents.pop()
        md_ctx.line_indent = md_ctx.line_indent[:-latest_len]
        content_result.localized += f'{md_ctx.line_indent}\n'

    @classmethod
    def dt_close(cls, _tokens: Sequence[Token], _idx: int, _md_ctx: MdCtx, content_result: L10NResult):
        content_result.localized += '\n'

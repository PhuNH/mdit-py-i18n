# SPDX-FileCopyrightText: 2023 Phu Hung Nguyen <phuhnguyen@outlook.com>
# SPDX-License-Identifier: LGPL-2.1-or-later

import inspect
from typing import Sequence

import pygments.token
from markdown_it import MarkdownIt
from markdown_it.token import Token
from markdown_it.utils import OptionsDict, EnvType
from pygments import lexers, util

from . import utils
from .utils import DomainExtractionProtocol


class MdCtx:
    def __init__(self, env: EnvType):
        self.path: str = env['path']
        self.parse_fence = env.get('parse_fence', False)
        self.domain_e: DomainExtractionProtocol = env['domain_extraction']

    def add_entry(self, msgid: str, line_number: int, comment: str = '', msgctxt: str = ''):
        self.domain_e.add_entry(self.path, msgid, line_number, comment, msgctxt)


class RendererMarkdownI18N:
    """
    Implements `RendererProtocol`
    """
    __output__ = 'pot'
    
    def __init__(self, mdi: MarkdownIt):
        self.rules = {
            k: v
            for k, v in inspect.getmembers(self, predicate=inspect.ismethod)
            if not (k.startswith("render") or k.startswith("_"))
        }
        self.mdi = mdi

    def render(self, tokens: Sequence[Token], _options: OptionsDict, env: EnvType):
        """
        :param tokens: list of block tokens to render
        :param _options: properties of parser instance
        :param env: containing:
            - 'path': path of the source file
            - 'domain_extraction': an object compatible with `DomainExtractionProtocol`
        :return: None
        """
        md_ctx = MdCtx(env)

        for i, token in enumerate(tokens):
            if token.type in self.rules:
                r = self.rules[token.type](tokens, i, md_ctx)
                if r == -1:
                    break
        self._link_ref(env, md_ctx)

    @staticmethod
    def _link_ref(env: EnvType, md_ctx: MdCtx):
        refs = env.get('references', {}).items()
        if len(refs) == 0:
            return
        for ref, details in refs:
            if title := details.get('title', ''):
                md_ctx.add_entry(title, details['map'][0] + 1)

    @classmethod
    def front_matter(cls, tokens: Sequence[Token], idx: int, md_ctx: MdCtx):
        token = tokens[idx]
        md_ctx.domain_e.render_front_matter(md_ctx.path, token.content, token.markup)

    @classmethod
    def inline(cls, tokens: Sequence[Token], idx: int, md_ctx: MdCtx):
        token = tokens[idx]
        content = utils.HARD_LINE_BREAK_PATTERN.sub('<br />', token.content.strip())
        content = utils.SPACES_PATTERN.sub(' ', content.replace('\n', ' '))
        if content and not utils.SPACES_PATTERN.fullmatch(content):
            md_ctx.add_entry(content, token.map[0] + 1)

    @classmethod
    def fence(cls, tokens: Sequence[Token], idx: int, md_ctx: MdCtx):
        if not md_ctx.parse_fence:
            return
        token = tokens[idx]
        try:
            lexer = lexers.get_lexer_by_name(token.info)
        except util.ClassNotFound:
            lexer = lexers.guess_lexer(token.content)
        code_toks = lexer.get_tokens(token.content)

        # temporary content of the comment being parsed
        # also indicates whether we are parsing a comment or not
        comment = ''
        # number of the line where the comment starts
        comment_line_num = 0
        # number of the last line with a comment token
        last_comment_line_num = 0
        # the token starts with one line of the fence, then the content. +1: 0-base -> 1-base
        line_num = token.map[0] + 1 + 1

        # concatenate comment tokens until either a non-comment token or a blank line or end of token stream
        for tok_type, tok_val in code_toks:
            if tok_type == pygments.token.Token.Comment.Single:
                # when another comment is already being parsed and there's a blank line
                if comment and line_num - last_comment_line_num > 1:
                    md_ctx.add_entry(comment, comment_line_num)
                    comment = ''
                    comment_line_num = 0
                if comment != '':
                    comment += ' '
                if comment_match := utils.SINGLE_COMMENT_PATTERN.match(tok_val):
                    comment += comment_match.group(2).strip()
                if comment_line_num == 0:
                    comment_line_num = line_num
                last_comment_line_num = line_num
            elif tok_val.strip() and comment:
                md_ctx.add_entry(comment, comment_line_num)
                comment = ''
                comment_line_num = 0
            line_num += tok_val.count('\n')
        if comment:
            md_ctx.add_entry(comment, comment_line_num)

    @classmethod
    def html_block(cls, tokens: Sequence[Token], idx: int, md_ctx: MdCtx):
        token = tokens[idx]
        md_ctx.add_entry(token.content, token.map[0] + 1)

<!--
SPDX-FileCopyrightText: 2023 Phu Hung Nguyen <phuhnguyen@outlook.com>
SPDX-License-Identifier: CC-BY-SA-4.0
-->

# mdit-py-i18n

Markdown i18n and l10n using markdown-it-py.

CommonMark compliant. All core Markdown elements are supported, as well as
table, and definition list. Front matter handlers are left for users to
implement.

## Install

```bash
pip install mdit-py-i18n
```

## Notes

Some notes about how different elements are handled:
- Inlines: hard line breaks are replaced with `<br />`, newlines and
consecutive spaces are not kept;
- Content of each HTML block isn't parsed into finer tokens but processed
as a whole;
- Fenced code blocks: disabled by default. When enabled, only `//` and `#`
single comments are processed;

## Usage

### Extraction
- Implement `I18NEntryProtocol` and `DomainExtractionProtocol`
- Subclass `RendererMarkdownI18N`

### Generation
- Implement `DomainGenerationProtocol`
- Subclass `RendererMarkdownL10N`

## Development

### Environment

- With Conda

```bash
conda env create -f environment.yml
conda activate mpi
poetry install
```
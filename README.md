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
- Inlines: newlines and consecutive spaces are not kept;
- Content of each HTML block isn't parsed into finer tokens but processed
as a whole;
- Fenced code blocks: only `//` single comments are processed;

## Development

### Environment

- With Conda

```bash
conda env create -f environment.yml
conda activate mpi
poetry install
```

### Usage

#### Extraction
- Follow `I18NEntryProtocol` and `DomainExtractionProtocol`
- Subclass `RendererMarkdownI18N`

#### Generation
- Follow `DomainGenerationProtocol`
- Subclass `RendererMarkdownL10N`
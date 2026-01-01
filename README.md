# Journal

A TUI for a Journal application which uses a sqlite3 database.

## Features

- Create, view, and delete journal entries
- Search entries by title or content
- Paginated entry list
- Scrollable entry view with word wrapping
- Markdown rendering when viewing entries
- Word-wrapped text editor

## Markdown Support

The journal renders markdown formatting when viewing entries:

- **Headers**: `# H1`, `## H2`, `### H3` (displayed in yellow with bold)
- **Bold**: `**text**` (displayed in bold)
- **Italic**: `*text*` or `_text_` (displayed dimmed)
- **Inline code**: `` `code` `` (displayed in green)
- **Lists**: `- item`, `* item`, `1. item` (with bullet markers)
- **Code blocks**: Text between ` ``` ` markers (displayed in green)

## Usage

```bash
python journal.py
```

On Windows, install curses support first:
```bash
pip install windows-curses
```

## Controls

- **Navigation**: Arrow keys
- **Select**: Enter
- **Quit**: Q
- **Multi-line input**: Press Escape to save, Ctrl+C to cancel

## Running Tests

```bash
python -m unittest test_journal -v
```

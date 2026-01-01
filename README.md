# Journal

A TUI for a Journal application which uses a sqlite3 database.

## Features

- Create, view, edit, and delete journal entries
- Search entries by title or content
- Paginated entry list
- Scrollable entry view with word wrapping
- Markdown rendering when viewing entries
- Word-wrapped text editor
- Configurable database location with cloud sync support

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
- **Edit entry**: E (when viewing an entry)
- **Delete entry**: D (in entry list)
- **New entry**: N (in entry list)
- **Text editor**: Escape to save, Ctrl+C to cancel

## Configuration

The database location is determined in the following order:

1. **Config file** (`~/.journalrc`): Set a custom path
2. **Box folder**: `~/Library/CloudStorage/Box-Box/journal_app.db` (if Box Drive is installed)
3. **Current directory**: `./journal_app.db`

To use a custom database path, create `~/.journalrc`:

```
DATABASE_PATH=~/path/to/journal.db
```

The current database location is displayed on the main menu.

## Running Tests

```bash
python -m unittest test_journal -v
```

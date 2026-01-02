# Journal

A TUI for a Journal application which uses a sqlite3 database.

## Features

- Create, view, edit, and delete journal entries
- Quick add entries from command line
- Export entries to markdown for backup
- Tag entries for organization and filtering
- Search entries by title, content, or tag
- Filter entries by tag
- Paginated entry list
- Scrollable entry view with word wrapping
- Markdown rendering when viewing entries
- Word-wrapped text editor
- Dark/light mode toggle with saved preference
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

## Quick Add from CLI

Add entries directly from the command line without opening the TUI:

```bash
# Add an entry
python journal.py --add "Title" "Content"
python journal.py -a "Title" "Content"

# Add an entry with tags
python journal.py --add "Title" "Content" --tags "work, ideas"
python journal.py -a "Title" "Content" -t "work, ideas"

# Show help
python journal.py --help
```

## Export to Markdown

Export all journal entries to a markdown file for backup or sharing:

```bash
python journal.py --export journal_backup.md
python journal.py -e journal_backup.md
```

The exported file includes each entry's title, date, tags, and content in a readable markdown format.

## Controls

- **Navigation**: Arrow keys
- **Select**: Enter
- **Quit**: Q
- **Back**: B
- **Toggle theme**: T (switch between dark/light mode)
- **Edit entry**: E (when viewing an entry)
- **Delete entry**: D (in entry list)
- **New entry**: N (in entry list)
- **Search**: / (in entry list)
- **Text editor**: Escape to save, Ctrl+C to cancel

## Tags

Organize your entries with tags for easy filtering:

- **Adding tags**: After entering content, you'll be prompted to add tags
- **Format**: Enter tags separated by commas (e.g., `work, ideas, personal`)
- **Case-insensitive**: Tags are stored in lowercase
- **Editing tags**: Press E when viewing an entry to edit its tags
  - Press Enter to keep existing tags
  - Enter new tags to replace existing ones
  - Enter `-` to clear all tags
- **Filtering**: Use "Filter by Tag" from the main menu to browse entries by tag
- **Existing tags**: When adding or editing tags, existing tags are shown for reference

Tags are displayed when viewing an entry and show the entry count in the filter view.

## Configuration

The database location is determined in the following order:

1. **Config file** (`~/.journalrc`): Set a custom path
2. **Box folder**: `~/Library/CloudStorage/Box-Box/journal_app.db` (if Box Drive is installed)
3. **Current directory**: `./journal_app.db`

To customize settings, create `~/.journalrc`:

```
DATABASE_PATH=~/path/to/journal.db
THEME=dark
```

Available settings:
- **DATABASE_PATH**: Custom path to the SQLite database
- **THEME**: `dark` (default) or `light` - automatically saved when toggling with T

The current database location is displayed on the main menu.

## Running Tests

```bash
python -m unittest test_journal -v
```

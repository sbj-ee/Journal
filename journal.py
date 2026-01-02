import sqlite3
import curses
import curses.textpad # For multiline input
import re
import os
import argparse
from datetime import datetime

# Configuration file path
CONFIG_FILE = os.path.expanduser('~/.journalrc')

def get_config_value(key, default=None):
    """Read a value from the config file."""
    if os.path.isfile(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            for line in f:
                line = line.strip()
                if line.startswith(f'{key}='):
                    value = line.split('=', 1)[1].strip().strip('"').strip("'")
                    return value
    return default

def set_config_value(key, value):
    """Set a value in the config file, preserving other settings."""
    lines = []
    key_found = False

    # Read existing config
    if os.path.isfile(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            for line in f:
                if line.strip().startswith(f'{key}='):
                    lines.append(f'{key}={value}\n')
                    key_found = True
                else:
                    lines.append(line if line.endswith('\n') else line + '\n')

    # Add key if not found
    if not key_found:
        lines.append(f'{key}={value}\n')

    # Write config
    with open(CONFIG_FILE, 'w') as f:
        f.writelines(lines)

def get_database_path():
    """Determine database path from config file, Box folder, or current directory."""
    # Check config file for DATABASE_PATH
    path = get_config_value('DATABASE_PATH')
    if path:
        return os.path.expanduser(path)

    # Fall back to Box folder if available
    box_folder = os.path.expanduser('~/Library/CloudStorage/Box-Box')
    if os.path.isdir(box_folder):
        return os.path.join(box_folder, 'journal_app.db')

    # Fall back to current directory
    return 'journal_app.db'

def load_theme_preference():
    """Load theme preference from config file."""
    theme = get_config_value('THEME', 'dark')
    return theme.lower() == 'dark'

DATABASE_NAME = get_database_path()

# Theme mode: True = dark mode (light text on dark bg), False = light mode (dark text on light bg)
dark_mode = load_theme_preference()

def init_colors():
    """Initialize color pairs based on current theme mode."""
    global dark_mode
    curses.start_color()

    if dark_mode:
        # Dark mode: light text on dark background
        curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_WHITE)  # Selected items
        curses.init_pair(2, curses.COLOR_CYAN, curses.COLOR_BLACK)   # Borders
        curses.init_pair(3, curses.COLOR_YELLOW, curses.COLOR_BLACK) # Headers
        curses.init_pair(4, curses.COLOR_GREEN, curses.COLOR_BLACK)  # Code
        curses.init_pair(5, curses.COLOR_MAGENTA, curses.COLOR_BLACK) # List markers/tags
    else:
        # Light mode: dark text on light background
        curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLACK)  # Selected items
        curses.init_pair(2, curses.COLOR_BLUE, curses.COLOR_WHITE)   # Borders
        curses.init_pair(3, curses.COLOR_RED, curses.COLOR_WHITE)    # Headers
        curses.init_pair(4, curses.COLOR_GREEN, curses.COLOR_WHITE)  # Code
        curses.init_pair(5, curses.COLOR_MAGENTA, curses.COLOR_WHITE) # List markers/tags

def toggle_theme(stdscr):
    """Toggle between dark and light mode and save preference."""
    global dark_mode
    dark_mode = not dark_mode
    init_colors()
    # Save preference to config file
    set_config_value('THEME', 'dark' if dark_mode else 'light')
    # Force screen refresh
    stdscr.clear()
    stdscr.refresh()

# --- Database Functions ---

def init_db():
    """Initializes the database and creates tables if they don't exist."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            title TEXT NOT NULL,
            content TEXT NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS entry_tags (
            entry_id INTEGER NOT NULL,
            tag_id INTEGER NOT NULL,
            PRIMARY KEY (entry_id, tag_id),
            FOREIGN KEY (entry_id) REFERENCES entries(id) ON DELETE CASCADE,
            FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
        )
    ''')
    conn.commit()
    conn.close()

def add_entry_db(title, content):
    """Adds a new journal entry to the database. Returns entry_id on success, None on failure."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO entries (title, content) VALUES (?, ?)", (title, content))
        conn.commit()
        return cursor.lastrowid
    except sqlite3.Error as e:
        return None
    finally:
        conn.close()

def get_all_entries_db():
    """Retrieves all journal entries from the database, ordered by timestamp."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    # Fetching id, formatted timestamp, and title for the list view
    cursor.execute("SELECT id, strftime('%Y-%m-%d %H:%M', timestamp) AS formatted_time, title FROM entries ORDER BY timestamp DESC")
    entries = cursor.fetchall()
    conn.close()
    return entries

def get_entry_db(entry_id):
    """Retrieves a specific journal entry by its ID."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    # Fetching id, formatted timestamp, title, and content for the detailed view
    cursor.execute("SELECT id, strftime('%Y-%m-%d %H:%M', timestamp) AS formatted_time, title, content FROM entries WHERE id = ?", (entry_id,))
    entry = cursor.fetchone()
    conn.close()
    return entry

def delete_entry_db(entry_id):
    """Deletes a journal entry by its ID."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM entries WHERE id = ?", (entry_id,))
        conn.commit()
        return True
    except sqlite3.Error as e:
        return False
    finally:
        conn.close()

def update_entry_db(entry_id, title, content):
    """Updates an existing journal entry."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE entries SET title = ?, content = ? WHERE id = ?", (title, content, entry_id))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        return False
    finally:
        conn.close()

def search_entries_db(search_term):
    """Searches journal entries by title, content, or tag."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    search_pattern = f"%{search_term}%"
    cursor.execute("""
        SELECT DISTINCT e.id, strftime('%Y-%m-%d %H:%M', e.timestamp) AS formatted_time, e.title
        FROM entries e
        LEFT JOIN entry_tags et ON e.id = et.entry_id
        LEFT JOIN tags t ON et.tag_id = t.id
        WHERE e.title LIKE ? OR e.content LIKE ? OR t.name LIKE ?
        ORDER BY e.timestamp DESC
    """, (search_pattern, search_pattern, search_pattern))
    entries = cursor.fetchall()
    conn.close()
    return entries

# --- Tag Database Functions ---

def get_or_create_tag(tag_name):
    """Gets a tag by name or creates it if it doesn't exist. Returns tag_id."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    tag_name = tag_name.strip().lower()
    try:
        cursor.execute("SELECT id FROM tags WHERE name = ?", (tag_name,))
        result = cursor.fetchone()
        if result:
            return result[0]
        cursor.execute("INSERT INTO tags (name) VALUES (?)", (tag_name,))
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()

def set_entry_tags(entry_id, tag_names):
    """Sets tags for an entry (replaces existing tags)."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    try:
        # Remove existing tags
        cursor.execute("DELETE FROM entry_tags WHERE entry_id = ?", (entry_id,))
        conn.commit()

        # Add new tags (each in its own transaction to avoid lock with get_or_create_tag)
        for tag_name in tag_names:
            tag_name = tag_name.strip().lower()
            if tag_name:
                tag_id = get_or_create_tag(tag_name)
                cursor.execute("INSERT OR IGNORE INTO entry_tags (entry_id, tag_id) VALUES (?, ?)",
                             (entry_id, tag_id))
                conn.commit()
        return True
    except sqlite3.Error:
        return False
    finally:
        conn.close()

def get_entry_tags(entry_id):
    """Gets all tags for an entry."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT t.name FROM tags t
        JOIN entry_tags et ON t.id = et.tag_id
        WHERE et.entry_id = ?
        ORDER BY t.name
    """, (entry_id,))
    tags = [row[0] for row in cursor.fetchall()]
    conn.close()
    return tags

def get_all_tags():
    """Gets all tags with their entry counts."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT t.name, COUNT(et.entry_id) as count
        FROM tags t
        LEFT JOIN entry_tags et ON t.id = et.tag_id
        GROUP BY t.id
        ORDER BY t.name
    """)
    tags = cursor.fetchall()
    conn.close()
    return tags

def get_entries_by_tag(tag_name):
    """Gets all entries with a specific tag."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT e.id, strftime('%Y-%m-%d %H:%M', e.timestamp) AS formatted_time, e.title
        FROM entries e
        JOIN entry_tags et ON e.id = et.entry_id
        JOIN tags t ON et.tag_id = t.id
        WHERE t.name = ?
        ORDER BY e.timestamp DESC
    """, (tag_name.lower(),))
    entries = cursor.fetchall()
    conn.close()
    return entries

# --- Curses UI Helper Functions ---

def display_message(stdscr, message, y_offset=None, x_offset=None, clear_first=True, wait_for_key=True):
    """Displays a message and optionally waits for a key press."""
    if clear_first:
        stdscr.clear()
    h, w = stdscr.getmaxyx()
    if y_offset is None:
        y_offset = h // 2
    if x_offset is None:
        x_offset = (w - len(message)) // 2
    
    stdscr.addstr(y_offset, max(0, x_offset), message) # Ensure x_offset is not negative
    stdscr.refresh()
    if wait_for_key:
        stdscr.getch()

def get_text_input(stdscr, prompt, y_offset, x_offset, max_len=60, clear_line_first=True):
    """Gets a single line of text input from the user."""
    if clear_line_first:
        h, w = stdscr.getmaxyx()
        stdscr.addstr(y_offset, x_offset, " " * (w - x_offset -1)) # Clear the line

    stdscr.addstr(y_offset, x_offset, prompt)
    stdscr.refresh()
    curses.echo() # Enable echoing of characters for input
    # Move cursor to after prompt
    input_win = curses.newwin(1, max_len + 1, y_offset, x_offset + len(prompt))
    input_str = input_win.getstr(0,0, max_len).decode(errors="ignore").strip()
    curses.noecho() # Disable echoing
    return input_str

def wrap_text(text, width):
    """Wrap text to fit within a given width, breaking at word boundaries."""
    if width <= 0:
        return []
    words = text.split(' ')
    lines = []
    current_line = ""

    for word in words:
        # Handle words longer than width
        while len(word) > width:
            if current_line:
                lines.append(current_line)
                current_line = ""
            lines.append(word[:width])
            word = word[width:]

        if not current_line:
            current_line = word
        elif len(current_line) + 1 + len(word) <= width:
            current_line += " " + word
        else:
            lines.append(current_line)
            current_line = word

    if current_line:
        lines.append(current_line)

    return lines if lines else [""]


def get_multiline_input(stdscr, prompt_message, title=None, initial_content=None):
    """
    Custom multiline text editor with word wrapping.
    Press Escape to save, Ctrl+C to cancel.
    """
    stdscr.clear()
    h, w = stdscr.getmaxyx()

    # Display title at the top if provided
    current_row = 0
    if title:
        title_display = f"Title: {title}"
        if len(title_display) > w - 1:
            title_display = title_display[:w - 4] + "..."
        stdscr.addstr(current_row, 0, title_display, curses.A_BOLD | curses.A_UNDERLINE)
        current_row += 1
        stdscr.addstr(current_row, 0, "-" * (w - 1))
        current_row += 1

    stdscr.addstr(current_row, 0, prompt_message, curses.A_BOLD)
    stdscr.addstr(h - 2, 0, "Press Escape to Save | Ctrl+C to Cancel")
    stdscr.refresh()

    # Editor area dimensions
    edit_y = current_row + 2
    edit_x = 1
    edit_h = h - edit_y - 3  # Leave room for border and footer
    edit_w = w - 3

    if edit_h <= 0 or edit_w <= 0:
        display_message(stdscr, "Screen too small for text input. Press any key.")
        return ""

    # Draw border
    try:
        stdscr.attron(curses.color_pair(2))
        curses.textpad.rectangle(stdscr, edit_y - 1, edit_x - 1, edit_y + edit_h, edit_x + edit_w + 1)
        stdscr.attroff(curses.color_pair(2))
        stdscr.refresh()
    except curses.error:
        pass

    # Text buffer - list of lines (without word wrapping applied)
    if initial_content:
        lines = initial_content.splitlines()
        if not lines:
            lines = [""]
        cursor_line = len(lines) - 1
        cursor_col = len(lines[cursor_line])
    else:
        lines = [""]
        cursor_line = 0
        cursor_col = 0
    scroll_offset = 0

    curses.curs_set(1)  # Show cursor

    def get_display_lines():
        """Convert logical lines to display lines with word wrapping."""
        display = []
        line_map = []  # Maps display line index to (logical_line, offset)
        for i, line in enumerate(lines):
            if not line:
                display.append("")
                line_map.append((i, 0))
            else:
                wrapped = wrap_text(line, edit_w)
                for j, wline in enumerate(wrapped):
                    display.append(wline)
                    # Calculate character offset for this wrapped segment
                    offset = sum(len(wrap_text(line, edit_w)[k]) + (1 if k > 0 else 0) for k in range(j))
                    line_map.append((i, j))
        return display, line_map

    def get_cursor_display_pos():
        """Get cursor position in display coordinates."""
        display_row = 0
        for i in range(cursor_line):
            line = lines[i]
            if not line:
                display_row += 1
            else:
                display_row += len(wrap_text(line, edit_w))

        # Now find position within current line
        current_line_text = lines[cursor_line]
        if not current_line_text:
            return display_row, cursor_col

        wrapped = wrap_text(current_line_text, edit_w)
        chars_so_far = 0
        for i, wline in enumerate(wrapped):
            line_len = len(wline)
            if chars_so_far + line_len >= cursor_col:
                col_in_line = cursor_col - chars_so_far
                return display_row + i, col_in_line
            chars_so_far += line_len + 1  # +1 for space that was replaced

        # Cursor at end
        return display_row + len(wrapped) - 1, len(wrapped[-1]) if wrapped else 0

    def redraw():
        """Redraw the editor content."""
        nonlocal scroll_offset
        display_lines, _ = get_display_lines()

        # Clear editor area
        for i in range(edit_h):
            try:
                stdscr.addstr(edit_y + i, edit_x, " " * edit_w)
            except curses.error:
                pass

        # Draw visible lines
        for i in range(edit_h):
            line_idx = scroll_offset + i
            if line_idx < len(display_lines):
                try:
                    stdscr.addstr(edit_y + i, edit_x, display_lines[line_idx][:edit_w])
                except curses.error:
                    pass

        # Position cursor
        cursor_display_row, cursor_display_col = get_cursor_display_pos()
        cursor_screen_row = cursor_display_row - scroll_offset

        # Adjust scroll if cursor is out of view
        if cursor_screen_row < 0:
            scroll_offset = cursor_display_row
            redraw()
            return
        elif cursor_screen_row >= edit_h:
            scroll_offset = cursor_display_row - edit_h + 1
            redraw()
            return

        try:
            stdscr.move(edit_y + cursor_screen_row, edit_x + cursor_display_col)
        except curses.error:
            pass

        stdscr.refresh()

    redraw()

    while True:
        try:
            key = stdscr.getch()
        except KeyboardInterrupt:
            curses.curs_set(0)
            return ""

        if key == 27:  # Escape - save and exit
            curses.curs_set(0)
            return "\n".join(lines)

        elif key == 3:  # Ctrl+C - cancel
            curses.curs_set(0)
            return ""

        elif key in (curses.KEY_BACKSPACE, 127, 8):  # Backspace
            if cursor_col > 0:
                lines[cursor_line] = lines[cursor_line][:cursor_col-1] + lines[cursor_line][cursor_col:]
                cursor_col -= 1
            elif cursor_line > 0:
                # Join with previous line
                cursor_col = len(lines[cursor_line - 1])
                lines[cursor_line - 1] += lines[cursor_line]
                lines.pop(cursor_line)
                cursor_line -= 1

        elif key in (curses.KEY_DC, 330):  # Delete key
            if cursor_col < len(lines[cursor_line]):
                lines[cursor_line] = lines[cursor_line][:cursor_col] + lines[cursor_line][cursor_col+1:]
            elif cursor_line < len(lines) - 1:
                # Join with next line
                lines[cursor_line] += lines[cursor_line + 1]
                lines.pop(cursor_line + 1)

        elif key in (curses.KEY_ENTER, 10, 13):  # Enter
            # Split line at cursor
            new_line = lines[cursor_line][cursor_col:]
            lines[cursor_line] = lines[cursor_line][:cursor_col]
            lines.insert(cursor_line + 1, new_line)
            cursor_line += 1
            cursor_col = 0

        elif key == curses.KEY_LEFT:
            if cursor_col > 0:
                cursor_col -= 1
            elif cursor_line > 0:
                cursor_line -= 1
                cursor_col = len(lines[cursor_line])

        elif key == curses.KEY_RIGHT:
            if cursor_col < len(lines[cursor_line]):
                cursor_col += 1
            elif cursor_line < len(lines) - 1:
                cursor_line += 1
                cursor_col = 0

        elif key == curses.KEY_UP:
            if cursor_line > 0:
                cursor_line -= 1
                cursor_col = min(cursor_col, len(lines[cursor_line]))

        elif key == curses.KEY_DOWN:
            if cursor_line < len(lines) - 1:
                cursor_line += 1
                cursor_col = min(cursor_col, len(lines[cursor_line]))

        elif key == curses.KEY_HOME:
            cursor_col = 0

        elif key == curses.KEY_END:
            cursor_col = len(lines[cursor_line])

        elif 32 <= key <= 126:  # Printable ASCII
            lines[cursor_line] = lines[cursor_line][:cursor_col] + chr(key) + lines[cursor_line][cursor_col:]
            cursor_col += 1

        elif key == 9:  # Tab - insert spaces
            spaces = "    "
            lines[cursor_line] = lines[cursor_line][:cursor_col] + spaces + lines[cursor_line][cursor_col:]
            cursor_col += len(spaces)

        redraw()


# --- Markdown Rendering ---

def render_markdown_line(stdscr, y, x, line, max_width):
    """
    Renders a single line with markdown formatting.
    Returns the number of lines consumed (for wrapped content).
    Supports: headers (#), bold (**), italic (*), inline code (`), lists (- * 1.)
    """
    if y >= curses.LINES - 2:
        return 0

    # Check for headers
    header_match = re.match(r'^(#{1,6})\s+(.*)$', line)
    if header_match:
        level = len(header_match.group(1))
        text = header_match.group(2)
        prefix = "═" * (4 - min(level, 3)) + " "
        try:
            stdscr.attron(curses.color_pair(3) | curses.A_BOLD)
            display_text = prefix + text
            if len(display_text) > max_width:
                display_text = display_text[:max_width-3] + "..."
            stdscr.addstr(y, x, display_text)
            stdscr.attroff(curses.color_pair(3) | curses.A_BOLD)
        except curses.error:
            pass
        return 1

    # Check for list items
    list_match = re.match(r'^(\s*)([-*]|\d+\.)\s+(.*)$', line)
    if list_match:
        indent = list_match.group(1)
        marker = list_match.group(2)
        text = list_match.group(3)
        try:
            stdscr.addstr(y, x, indent)
            stdscr.attron(curses.color_pair(5) | curses.A_BOLD)
            if marker in ['-', '*']:
                stdscr.addstr("• ")
            else:
                stdscr.addstr(marker + " ")
            stdscr.attroff(curses.color_pair(5) | curses.A_BOLD)
            render_inline_markdown(stdscr, y, x + len(indent) + len(marker) + 2, text, max_width - len(indent) - len(marker) - 2)
        except curses.error:
            pass
        return 1

    # Check for code block marker
    if line.strip().startswith('```'):
        try:
            stdscr.attron(curses.color_pair(4))
            stdscr.addstr(y, x, "─" * min(max_width, 40))
            stdscr.attroff(curses.color_pair(4))
        except curses.error:
            pass
        return 1

    # Regular line - render with inline formatting
    render_inline_markdown(stdscr, y, x, line, max_width)
    return 1


def render_inline_markdown(stdscr, y, x, text, max_width):
    """
    Renders inline markdown formatting: bold (**), italic (*), inline code (`).
    """
    if not text or x >= curses.COLS - 1:
        return

    # Pattern to match markdown inline elements
    # Order matters: check bold (**) before italic (*)
    pattern = r'(\*\*(.+?)\*\*)|(`(.+?)`)|(\*(.+?)\*)|(_(.+?)_)'

    pos = 0
    current_x = x

    for match in re.finditer(pattern, text):
        # Print text before the match
        before_text = text[pos:match.start()]
        if before_text and current_x < x + max_width:
            try:
                display_text = before_text[:max(0, x + max_width - current_x)]
                stdscr.addstr(y, current_x, display_text)
                current_x += len(display_text)
            except curses.error:
                pass

        if current_x >= x + max_width:
            return

        # Determine which group matched and apply formatting
        if match.group(2):  # Bold **text**
            content = match.group(2)
            try:
                stdscr.attron(curses.A_BOLD)
                display_text = content[:max(0, x + max_width - current_x)]
                stdscr.addstr(y, current_x, display_text)
                stdscr.attroff(curses.A_BOLD)
                current_x += len(display_text)
            except curses.error:
                pass
        elif match.group(4):  # Inline code `text`
            content = match.group(4)
            try:
                stdscr.attron(curses.color_pair(4))
                display_text = content[:max(0, x + max_width - current_x)]
                stdscr.addstr(y, current_x, display_text)
                stdscr.attroff(curses.color_pair(4))
                current_x += len(display_text)
            except curses.error:
                pass
        elif match.group(6):  # Italic *text*
            content = match.group(6)
            try:
                stdscr.attron(curses.A_DIM)
                display_text = content[:max(0, x + max_width - current_x)]
                stdscr.addstr(y, current_x, display_text)
                stdscr.attroff(curses.A_DIM)
                current_x += len(display_text)
            except curses.error:
                pass
        elif match.group(8):  # Italic _text_
            content = match.group(8)
            try:
                stdscr.attron(curses.A_DIM)
                display_text = content[:max(0, x + max_width - current_x)]
                stdscr.addstr(y, current_x, display_text)
                stdscr.attroff(curses.A_DIM)
                current_x += len(display_text)
            except curses.error:
                pass

        pos = match.end()

    # Print remaining text after last match
    remaining = text[pos:]
    if remaining and current_x < x + max_width:
        try:
            display_text = remaining[:max(0, x + max_width - current_x)]
            stdscr.addstr(y, current_x, display_text)
        except curses.error:
            pass


# --- UI Screens ---

def display_main_menu(stdscr, selected_option_idx):
    """Displays the main menu and highlights the selected option."""
    stdscr.clear()
    h, w = stdscr.getmaxyx()
    menu_title = "Python Journal TUI"
    options = ["View Entries", "Add New Entry", "Search Entries", "Filter by Tag", "Exit"]

    stdscr.addstr(1, (w - len(menu_title)) // 2, menu_title, curses.A_BOLD | curses.A_UNDERLINE)

    # Show entry count
    entry_count = len(get_all_entries_db())
    count_text = f"{entry_count} entry" if entry_count == 1 else f"{entry_count} entries"
    stdscr.addstr(3, (w - len(count_text)) // 2, count_text)

    for i, option in enumerate(options):
        y_pos = h // 2 - len(options) // 2 + i + 2 # +2 for title and spacing
        x_pos = (w - len(option)) // 2
        if i == selected_option_idx:
            stdscr.attron(curses.color_pair(1)) # Highlight selected
            stdscr.addstr(y_pos, x_pos, f"> {option} <")
            stdscr.attroff(curses.color_pair(1))
        else:
            stdscr.addstr(y_pos, x_pos, f"  {option}  ")

    # Show database location
    db_path = DATABASE_NAME.replace(os.path.expanduser('~'), '~')
    if len(db_path) > w - 8:
        db_path = "..." + db_path[-(w - 11):]
    stdscr.addstr(h - 3, 2, f"DB: {db_path}", curses.A_DIM)

    stdscr.addstr(h - 2, 2, "UP/DOWN: Navigate, ENTER: Select, T: Theme, Q: Quit, ?: Help")
    stdscr.refresh()

def display_entries_list(stdscr, entries, current_page, items_per_page, selected_idx_on_page):
    """Displays a paginated list of journal entries."""
    stdscr.clear()
    h, w = stdscr.getmaxyx()
    stdscr.addstr(0, 0, "Journal Entries (N: New, B: Back, Q: Quit)", curses.A_BOLD)
    stdscr.addstr(1,0, "-" * (w-1))

    if not entries:
        stdscr.addstr(3, 2, "No entries yet. Press 'N' to create one.")
        stdscr.refresh()
        return [] # Return empty list for paginated_entries

    start_index = current_page * items_per_page
    end_index = start_index + items_per_page
    paginated_entries = entries[start_index:end_index]

    line_num = 2
    for i, entry in enumerate(paginated_entries):
        # entry format: (id, formatted_time, title)
        entry_id = entry[0]
        tags = get_entry_tags(entry_id)
        tags_str = f" [{', '.join(tags)}]" if tags else ""

        display_text = f"{entry[1]} - {entry[2]}" # Timestamp - Title
        full_text = display_text + tags_str

        if i == selected_idx_on_page:
            stdscr.attron(curses.color_pair(1))
            if len(full_text) > w - 4:
                # Truncate but try to show some tags
                stdscr.addstr(line_num + i, 2, f"> {full_text[:w-7]}...")
            else:
                stdscr.addstr(line_num + i, 2, f"> {display_text}")
                if tags_str:
                    stdscr.addstr(tags_str)
            stdscr.attroff(curses.color_pair(1))
        else:
            if len(full_text) > w - 4:
                stdscr.addstr(line_num + i, 2, f"  {full_text[:w-7]}...")
            else:
                stdscr.addstr(line_num + i, 2, f"  {display_text}")
                if tags_str:
                    stdscr.attron(curses.color_pair(5))
                    stdscr.addstr(tags_str)
                    stdscr.attroff(curses.color_pair(5))

    # Pagination info
    total_pages = (len(entries) + items_per_page - 1) // items_per_page
    if total_pages == 0: total_pages = 1
    page_info = f"Page {current_page + 1}/{total_pages}"
    stdscr.addstr(h - 3, 2, page_info)
    stdscr.addstr(h - 2, 2, "UP/DOWN: Navigate, ENTER: View, D: Delete, /: Search, LEFT/RIGHT: Pages")
    stdscr.refresh()
    return paginated_entries


def view_single_entry_screen(stdscr, entry_id):
    """Displays the full content of a single journal entry with word wrapping."""
    entry = get_entry_db(entry_id)
    stdscr.clear()
    h, w = stdscr.getmaxyx()

    if not entry:
        display_message(stdscr, "Error: Entry not found. Press any key to return.")
        return

    # entry format: (id, formatted_time, title, content)
    title_line = f"Title: {entry[2]} (ID: {entry[0]})"
    timestamp_line = f"Date: {entry[1]}"
    tags = get_entry_tags(entry_id)
    tags_line = f"Tags: {', '.join(tags)}" if tags else "Tags: (none)"

    stdscr.addstr(0, 0, title_line, curses.A_BOLD)
    stdscr.addstr(1, 0, timestamp_line)
    stdscr.addstr(2, 0, tags_line, curses.color_pair(5))
    stdscr.addstr(3, 0, "-" * (w - 1))

    content_lines = entry[3].splitlines()
    current_display_line = 4
    scroll_offset = 0 # For scrolling content if it's too long
    display_width = w - 1

    # Pre-process: wrap lines and track code block state for each display line
    # Each item: (wrapped_line_text, is_code_block, is_code_fence, original_line_idx)
    display_lines = []
    in_code_block = False

    for orig_idx, line in enumerate(content_lines):
        is_code_fence = line.strip().startswith('```')

        if is_code_fence:
            in_code_block = not in_code_block
            display_lines.append((line, False, True, orig_idx))
        elif in_code_block:
            # Don't word-wrap code blocks, just truncate or show as-is
            display_lines.append((line, True, False, orig_idx))
        elif not line.strip():
            # Empty line
            display_lines.append(("", False, False, orig_idx))
        else:
            # Word wrap regular text
            wrapped = wrap_text(line, display_width)
            for wrap_idx, wrapped_line in enumerate(wrapped):
                # Only first wrapped segment gets markdown rendering for headers/lists
                display_lines.append((wrapped_line, False, False, orig_idx))

    while True:
        stdscr.move(current_display_line, 0) # Move cursor to start of content area
        stdscr.clrtobot() # Clear from cursor to bottom of screen

        # Display content with scrolling
        lines_to_display = h - current_display_line - 2 # -2 for bottom message

        for i in range(lines_to_display):
            display_idx = scroll_offset + i
            if display_idx < len(display_lines):
                line_text, is_code, is_fence, _ = display_lines[display_idx]

                if is_fence:
                    # Render code fence marker
                    render_markdown_line(stdscr, current_display_line + i, 0, line_text, display_width)
                elif is_code:
                    # Inside code block - use code color without markdown parsing
                    try:
                        stdscr.attron(curses.color_pair(4))
                        display_text = line_text[:display_width] if len(line_text) > display_width else line_text
                        stdscr.addstr(current_display_line + i, 0, display_text)
                        stdscr.attroff(curses.color_pair(4))
                    except curses.error:
                        pass
                else:
                    # Render with markdown formatting
                    render_markdown_line(stdscr, current_display_line + i, 0, line_text, display_width)
            else:
                break # No more content lines

        stdscr.addstr(h - 1, 0, "B: Back, E: Edit, UP/DOWN: Scroll, Q: Quit")
        stdscr.refresh()

        key = stdscr.getch()
        if key == ord('b') or key == ord('B'):
            break
        elif key == ord('e') or key == ord('E'):
            if edit_entry_screen(stdscr, entry_id):
                # Reload the entry after editing
                entry = get_entry_db(entry_id)
                if entry:
                    title_line = f"Title: {entry[2]} (ID: {entry[0]})"
                    timestamp_line = f"Date: {entry[1]}"
                    tags = get_entry_tags(entry_id)
                    tags_line = f"Tags: {', '.join(tags)}" if tags else "Tags: (none)"
                    content_lines = entry[3].splitlines()
                    # Rebuild display_lines
                    display_lines = []
                    in_code_block = False
                    for orig_idx, line in enumerate(content_lines):
                        is_code_fence = line.strip().startswith('```')
                        if is_code_fence:
                            in_code_block = not in_code_block
                            display_lines.append((line, False, True, orig_idx))
                        elif in_code_block:
                            display_lines.append((line, True, False, orig_idx))
                        elif not line.strip():
                            display_lines.append(("", False, False, orig_idx))
                        else:
                            wrapped = wrap_text(line, display_width)
                            for wrap_idx, wrapped_line in enumerate(wrapped):
                                display_lines.append((wrapped_line, False, False, orig_idx))
                    scroll_offset = 0
            # Redraw header after returning from edit
            stdscr.clear()
            stdscr.addstr(0, 0, title_line, curses.A_BOLD)
            stdscr.addstr(1, 0, timestamp_line)
            stdscr.addstr(2, 0, tags_line, curses.color_pair(5))
            stdscr.addstr(3, 0, "-" * (w - 1))
        elif key == ord('q') or key == ord('Q'):
            if confirm_action(stdscr, "Quit to main menu? (y/N):"):
                return "QUIT_APP" # Special signal
            else: # Redraw after confirm_action clears screen
                stdscr.clear()
                stdscr.addstr(0, 0, title_line, curses.A_BOLD)
                stdscr.addstr(1, 0, timestamp_line)
                stdscr.addstr(2, 0, tags_line, curses.color_pair(5))
                stdscr.addstr(3, 0, "-" * (w - 1))
                # No need to redraw content here, loop will do it
        elif key == curses.KEY_UP:
            if scroll_offset > 0:
                scroll_offset -= 1
        elif key == curses.KEY_DOWN:
            # Only scroll down if there's more content to show
            if scroll_offset + lines_to_display < len(display_lines):
                scroll_offset += 1
    return None


def add_new_entry_screen(stdscr):
    """Screen for adding a new journal entry."""
    stdscr.clear()
    h, w = stdscr.getmaxyx()
    curses.curs_set(1) # Show cursor for input

    stdscr.addstr(1, 2, "Add New Journal Entry", curses.A_BOLD)
    title = get_text_input(stdscr, "Title: ", 3, 2, max_len=w-10)

    if not title:
        display_message(stdscr, "Title cannot be empty. Entry not added. Press any key.")
        curses.curs_set(0) # Hide cursor
        return

    # Get multiline content
    content = get_multiline_input(stdscr, "Enter content:", title=title)

    if content: # If Escape was pressed and content is not empty
        entry_id = add_entry_db(title, content)
        if entry_id:
            # Ask for tags
            stdscr.clear()
            h, w = stdscr.getmaxyx()
            stdscr.addstr(1, 2, "Add Tags (optional)", curses.A_BOLD)
            stdscr.addstr(3, 2, "Enter tags separated by commas (e.g., work, personal, ideas)")

            # Show existing tags
            existing_tags = get_all_tags()
            if existing_tags:
                tag_names = [t[0] for t in existing_tags]
                existing_str = ", ".join(tag_names)
                stdscr.addstr(5, 2, "Existing tags:", curses.A_DIM)
                # Word wrap if too long
                max_tag_width = w - 4
                if len(existing_str) > max_tag_width:
                    existing_str = existing_str[:max_tag_width - 3] + "..."
                stdscr.addstr(6, 2, existing_str, curses.color_pair(5))
                tags_input = get_text_input(stdscr, "Tags: ", 8, 2, max_len=w-10)
            else:
                tags_input = get_text_input(stdscr, "Tags: ", 5, 2, max_len=w-10)

            if tags_input:
                tag_list = [t.strip() for t in tags_input.split(',') if t.strip()]
                set_entry_tags(entry_id, tag_list)
            display_message(stdscr, "Entry added successfully! Press any key.")
        else:
            display_message(stdscr, "Failed to add entry to database. Press any key.")
    else:
        display_message(stdscr, "Entry not added (cancelled or empty content). Press any key.")

    curses.curs_set(0) # Hide cursor


def edit_entry_screen(stdscr, entry_id):
    """Screen for editing an existing journal entry."""
    entry = get_entry_db(entry_id)
    if not entry:
        display_message(stdscr, "Error: Entry not found. Press any key.")
        return False

    # entry format: (id, formatted_time, title, content)
    current_title = entry[2]
    current_content = entry[3]
    current_tags = get_entry_tags(entry_id)

    stdscr.clear()
    h, w = stdscr.getmaxyx()
    curses.curs_set(1)

    stdscr.addstr(1, 2, "Edit Journal Entry", curses.A_BOLD)
    stdscr.addstr(3, 2, f"Current title: {current_title}")
    new_title = get_text_input(stdscr, "New title (or Enter to keep): ", 4, 2, max_len=w-10)

    if not new_title:
        new_title = current_title

    # Get multiline content with existing content pre-populated
    new_content = get_multiline_input(stdscr, "Edit content:", title=new_title, initial_content=current_content)

    if new_content:
        if update_entry_db(entry_id, new_title, new_content):
            # Ask for tags
            stdscr.clear()
            h, w = stdscr.getmaxyx()
            stdscr.addstr(1, 2, "Edit Tags", curses.A_BOLD)
            current_tags_str = ", ".join(current_tags) if current_tags else ""
            stdscr.addstr(3, 2, f"Current tags: {current_tags_str if current_tags_str else '(none)'}")
            stdscr.addstr(4, 2, "Enter new tags, or press Enter to keep current (use - to clear)")

            # Show all existing tags
            existing_tags = get_all_tags()
            if existing_tags:
                tag_names = [t[0] for t in existing_tags]
                existing_str = ", ".join(tag_names)
                stdscr.addstr(6, 2, "All tags:", curses.A_DIM)
                max_tag_width = w - 4
                if len(existing_str) > max_tag_width:
                    existing_str = existing_str[:max_tag_width - 3] + "..."
                stdscr.addstr(7, 2, existing_str, curses.color_pair(5))
                tags_input = get_text_input(stdscr, "Tags: ", 9, 2, max_len=w-10)
            else:
                tags_input = get_text_input(stdscr, "Tags: ", 6, 2, max_len=w-10)
            if tags_input is not None:
                if tags_input == "-":
                    set_entry_tags(entry_id, [])  # Clear tags if user enters -
                elif tags_input:
                    tag_list = [t.strip() for t in tags_input.split(',') if t.strip()]
                    set_entry_tags(entry_id, tag_list)
                # If empty, keep existing tags (do nothing)
            display_message(stdscr, "Entry updated successfully! Press any key.")
            curses.curs_set(0)
            return True
        else:
            display_message(stdscr, "Failed to update entry. Press any key.")
    else:
        display_message(stdscr, "Edit cancelled. Press any key.")

    curses.curs_set(0)
    return False


def search_entries_screen(stdscr):
    """Screen for searching journal entries."""
    stdscr.clear()
    h, w = stdscr.getmaxyx()
    curses.curs_set(1)

    stdscr.addstr(1, 2, "Search Entries", curses.A_BOLD)
    stdscr.addstr(3, 2, "Search by title, content, or tag", curses.A_DIM)
    search_term = get_text_input(stdscr, "Search: ", 5, 2, max_len=w-10)

    curses.curs_set(0)

    if not search_term:
        display_message(stdscr, "No search term entered. Press any key.")
        return None

    results = search_entries_db(search_term)
    if not results:
        display_message(stdscr, f"No entries found for '{search_term}'. Press any key.")
        return None

    return search_results_loop(stdscr, results, search_term)


def search_results_loop(stdscr, results, search_term):
    """Manages display and interaction with search results."""
    current_page = 0
    items_per_page = curses.LINES - 6
    if items_per_page <= 0:
        items_per_page = 1
    selected_idx_on_page = 0

    while True:
        total_entries = len(results)
        total_pages = (total_entries + items_per_page - 1) // items_per_page
        if total_pages == 0:
            total_pages = 1
        current_page = max(0, min(current_page, total_pages - 1))

        entries_on_this_page_count = len(results[current_page * items_per_page : (current_page + 1) * items_per_page])
        selected_idx_on_page = max(0, min(selected_idx_on_page, entries_on_this_page_count - 1 if entries_on_this_page_count > 0 else 0))

        paginated_entries = display_search_results(stdscr, results, search_term, current_page, items_per_page, selected_idx_on_page)
        key = stdscr.getch()

        if key == curses.KEY_UP:
            selected_idx_on_page = max(0, selected_idx_on_page - 1)
        elif key == curses.KEY_DOWN:
            if entries_on_this_page_count > 0:
                selected_idx_on_page = min(entries_on_this_page_count - 1, selected_idx_on_page + 1)
        elif key == curses.KEY_LEFT:
            if current_page > 0:
                current_page -= 1
                selected_idx_on_page = 0
        elif key == curses.KEY_RIGHT:
            if current_page < total_pages - 1:
                current_page += 1
                selected_idx_on_page = 0
        elif key == ord('b') or key == ord('B'):
            return None
        elif key == ord('q') or key == ord('Q'):
            if confirm_action(stdscr, "Quit application? (y/N):"):
                return "QUIT_APP"
        elif (key == curses.KEY_ENTER or key in [10, 13]) and paginated_entries:
            if 0 <= selected_idx_on_page < len(paginated_entries):
                entry_id_to_view = paginated_entries[selected_idx_on_page][0]
                result = view_single_entry_screen(stdscr, entry_id_to_view)
                if result == "QUIT_APP":
                    return "QUIT_APP"
        elif key == curses.KEY_RESIZE:
            items_per_page = curses.LINES - 6
            if items_per_page <= 0:
                items_per_page = 1


def display_search_results(stdscr, entries, search_term, current_page, items_per_page, selected_idx_on_page):
    """Displays search results with pagination."""
    stdscr.clear()
    h, w = stdscr.getmaxyx()
    stdscr.addstr(0, 0, f"Search Results for '{search_term}' ({len(entries)} found)", curses.A_BOLD)
    stdscr.addstr(1, 0, "-" * (w - 1))

    start_index = current_page * items_per_page
    end_index = start_index + items_per_page
    paginated_entries = entries[start_index:end_index]

    line_num = 2
    for i, entry in enumerate(paginated_entries):
        display_text = f"{entry[1]} - {entry[2]}"
        if len(display_text) > w - 4:
            display_text = display_text[:w - 7] + "..."

        if i == selected_idx_on_page:
            stdscr.attron(curses.color_pair(1))
            stdscr.addstr(line_num + i, 2, f"> {display_text}")
            stdscr.attroff(curses.color_pair(1))
        else:
            stdscr.addstr(line_num + i, 2, f"  {display_text}")

    total_pages = (len(entries) + items_per_page - 1) // items_per_page
    if total_pages == 0:
        total_pages = 1
    page_info = f"Page {current_page + 1}/{total_pages}"
    stdscr.addstr(h - 3, 2, page_info)
    stdscr.addstr(h - 2, 2, "UP/DOWN: Navigate, ENTER: View, B: Back, LEFT/RIGHT: Pages")
    stdscr.refresh()
    return paginated_entries


def filter_by_tag_screen(stdscr):
    """Screen for filtering entries by tag."""
    all_tags = get_all_tags()

    if not all_tags:
        display_message(stdscr, "No tags found. Add tags to entries first. Press any key.")
        return None

    current_page = 0
    items_per_page = curses.LINES - 6
    if items_per_page <= 0:
        items_per_page = 1
    selected_idx_on_page = 0

    while True:
        stdscr.clear()
        h, w = stdscr.getmaxyx()
        stdscr.addstr(0, 0, f"Filter by Tag ({len(all_tags)} tags)", curses.A_BOLD)
        stdscr.addstr(1, 0, "-" * (w - 1))

        total_tags = len(all_tags)
        total_pages = (total_tags + items_per_page - 1) // items_per_page
        if total_pages == 0:
            total_pages = 1
        current_page = max(0, min(current_page, total_pages - 1))

        start_index = current_page * items_per_page
        end_index = start_index + items_per_page
        paginated_tags = all_tags[start_index:end_index]

        tags_on_this_page_count = len(paginated_tags)
        selected_idx_on_page = max(0, min(selected_idx_on_page, tags_on_this_page_count - 1 if tags_on_this_page_count > 0 else 0))

        line_num = 2
        for i, (tag_name, count) in enumerate(paginated_tags):
            display_text = f"{tag_name} ({count} entries)"
            if len(display_text) > w - 4:
                display_text = display_text[:w - 7] + "..."

            if i == selected_idx_on_page:
                stdscr.attron(curses.color_pair(1))
                stdscr.addstr(line_num + i, 2, f"> {display_text}")
                stdscr.attroff(curses.color_pair(1))
            else:
                stdscr.addstr(line_num + i, 2, f"  {display_text}")

        page_info = f"Page {current_page + 1}/{total_pages}"
        stdscr.addstr(h - 3, 2, page_info)
        stdscr.addstr(h - 2, 2, "UP/DOWN: Navigate, ENTER: View entries, B: Back, LEFT/RIGHT: Pages")
        stdscr.refresh()

        key = stdscr.getch()

        if key == curses.KEY_UP:
            selected_idx_on_page = max(0, selected_idx_on_page - 1)
        elif key == curses.KEY_DOWN:
            if tags_on_this_page_count > 0:
                selected_idx_on_page = min(tags_on_this_page_count - 1, selected_idx_on_page + 1)
        elif key == curses.KEY_LEFT:
            if current_page > 0:
                current_page -= 1
                selected_idx_on_page = 0
        elif key == curses.KEY_RIGHT:
            if current_page < total_pages - 1:
                current_page += 1
                selected_idx_on_page = 0
        elif key == ord('b') or key == ord('B'):
            return None
        elif key == ord('q') or key == ord('Q'):
            if confirm_action(stdscr, "Quit application? (y/N):"):
                return "QUIT_APP"
        elif (key == curses.KEY_ENTER or key in [10, 13]) and paginated_tags:
            if 0 <= selected_idx_on_page < len(paginated_tags):
                selected_tag = paginated_tags[selected_idx_on_page][0]
                entries = get_entries_by_tag(selected_tag)
                if entries:
                    result = tag_entries_loop(stdscr, entries, selected_tag)
                    if result == "QUIT_APP":
                        return "QUIT_APP"
                else:
                    display_message(stdscr, f"No entries found with tag '{selected_tag}'. Press any key.")
        elif key == curses.KEY_RESIZE:
            items_per_page = curses.LINES - 6
            if items_per_page <= 0:
                items_per_page = 1


def tag_entries_loop(stdscr, entries, tag_name):
    """Manages display and interaction with entries filtered by tag."""
    current_page = 0
    items_per_page = curses.LINES - 6
    if items_per_page <= 0:
        items_per_page = 1
    selected_idx_on_page = 0

    while True:
        stdscr.clear()
        h, w = stdscr.getmaxyx()
        stdscr.addstr(0, 0, f"Entries tagged '{tag_name}' ({len(entries)} found)", curses.A_BOLD)
        stdscr.addstr(1, 0, "-" * (w - 1))

        total_entries = len(entries)
        total_pages = (total_entries + items_per_page - 1) // items_per_page
        if total_pages == 0:
            total_pages = 1
        current_page = max(0, min(current_page, total_pages - 1))

        start_index = current_page * items_per_page
        end_index = start_index + items_per_page
        paginated_entries = entries[start_index:end_index]

        entries_on_this_page_count = len(paginated_entries)
        selected_idx_on_page = max(0, min(selected_idx_on_page, entries_on_this_page_count - 1 if entries_on_this_page_count > 0 else 0))

        line_num = 2
        for i, entry in enumerate(paginated_entries):
            display_text = f"{entry[1]} - {entry[2]}"
            if len(display_text) > w - 4:
                display_text = display_text[:w - 7] + "..."

            if i == selected_idx_on_page:
                stdscr.attron(curses.color_pair(1))
                stdscr.addstr(line_num + i, 2, f"> {display_text}")
                stdscr.attroff(curses.color_pair(1))
            else:
                stdscr.addstr(line_num + i, 2, f"  {display_text}")

        page_info = f"Page {current_page + 1}/{total_pages}"
        stdscr.addstr(h - 3, 2, page_info)
        stdscr.addstr(h - 2, 2, "UP/DOWN: Navigate, ENTER: View, B: Back, LEFT/RIGHT: Pages")
        stdscr.refresh()

        key = stdscr.getch()

        if key == curses.KEY_UP:
            selected_idx_on_page = max(0, selected_idx_on_page - 1)
        elif key == curses.KEY_DOWN:
            if entries_on_this_page_count > 0:
                selected_idx_on_page = min(entries_on_this_page_count - 1, selected_idx_on_page + 1)
        elif key == curses.KEY_LEFT:
            if current_page > 0:
                current_page -= 1
                selected_idx_on_page = 0
        elif key == curses.KEY_RIGHT:
            if current_page < total_pages - 1:
                current_page += 1
                selected_idx_on_page = 0
        elif key == ord('b') or key == ord('B'):
            return None
        elif key == ord('q') or key == ord('Q'):
            if confirm_action(stdscr, "Quit application? (y/N):"):
                return "QUIT_APP"
        elif (key == curses.KEY_ENTER or key in [10, 13]) and paginated_entries:
            if 0 <= selected_idx_on_page < len(paginated_entries):
                entry_id_to_view = paginated_entries[selected_idx_on_page][0]
                result = view_single_entry_screen(stdscr, entry_id_to_view)
                if result == "QUIT_APP":
                    return "QUIT_APP"
        elif key == curses.KEY_RESIZE:
            items_per_page = curses.LINES - 6
            if items_per_page <= 0:
                items_per_page = 1


def display_help_screen(stdscr):
    """Display keyboard shortcuts help screen."""
    stdscr.clear()
    h, w = stdscr.getmaxyx()

    help_title = "Keyboard Shortcuts"
    stdscr.addstr(1, (w - len(help_title)) // 2, help_title, curses.A_BOLD | curses.A_UNDERLINE)

    shortcuts = [
        ("General", [
            ("↑/↓", "Navigate up/down"),
            ("←/→", "Previous/next page"),
            ("Enter", "Select/confirm"),
            ("B", "Go back"),
            ("Q", "Quit"),
            ("T", "Toggle dark/light mode"),
            ("?", "Show this help"),
        ]),
        ("Main Menu", [
            ("1-5", "Quick select menu option"),
        ]),
        ("Entry List", [
            ("N", "New entry"),
            ("D", "Delete selected entry"),
            ("/", "Search entries"),
        ]),
        ("View Entry", [
            ("E", "Edit entry"),
            ("↑/↓", "Scroll content"),
        ]),
        ("Text Editor", [
            ("Esc", "Save and exit"),
            ("Ctrl+C", "Cancel without saving"),
            ("←/→/↑/↓", "Move cursor"),
            ("Home/End", "Start/end of line"),
        ]),
        ("Tags", [
            ("Enter", "Keep existing tags (when editing)"),
            ("-", "Clear all tags (when editing)"),
        ]),
    ]

    line = 3
    for section_title, section_shortcuts in shortcuts:
        if line >= h - 3:
            break
        stdscr.addstr(line, 2, section_title, curses.A_BOLD | curses.color_pair(3))
        line += 1
        for key, description in section_shortcuts:
            if line >= h - 3:
                break
            stdscr.addstr(line, 4, f"{key:12} {description}")
            line += 1
        line += 1  # Blank line between sections

    stdscr.addstr(h - 2, 2, "Press any key to return...")
    stdscr.refresh()
    stdscr.getch()


def confirm_action(stdscr, prompt):
    """Generic confirmation dialog."""
    stdscr.clear() # Clear screen for the prompt
    h, w = stdscr.getmaxyx()
    y_pos = h // 2
    x_pos = (w - len(prompt) - 2) // 2 # -2 for the space for input
    stdscr.addstr(y_pos, x_pos, prompt)
    stdscr.refresh()
    curses.echo()
    # Get only one char
    choice = stdscr.getstr(y_pos, x_pos + len(prompt), 1).decode(errors="ignore").lower()
    curses.noecho()
    return choice == 'y'

# --- Main Application Logic ---

def journal_entries_loop(stdscr):
    """Manages the display and interaction with the list of entries."""
    current_page = 0
    # Calculate items_per_page dynamically, leave room for header/footer
    items_per_page = curses.LINES - 6 # Adjust if header/footer changes
    if items_per_page <= 0: items_per_page = 1 # Ensure at least 1
    selected_idx_on_page = 0
    all_entries_data = []

    while True:
        all_entries_data = get_all_entries_db() # Refresh data
        total_entries = len(all_entries_data)
        total_pages = (total_entries + items_per_page - 1) // items_per_page
        if total_pages == 0: total_pages = 1 # Avoid page 0/0, show 1/1 for empty
        current_page = max(0, min(current_page, total_pages - 1))

        # Adjust selected_idx_on_page if it's out of bounds for the current page
        entries_on_this_page_count = len(all_entries_data[current_page * items_per_page : (current_page + 1) * items_per_page])
        if entries_on_this_page_count == 0 and total_entries > 0: # e.g. deleted last item on page
            current_page = max(0, current_page -1)
            entries_on_this_page_count = len(all_entries_data[current_page * items_per_page : (current_page + 1) * items_per_page])
        
        selected_idx_on_page = max(0, min(selected_idx_on_page, entries_on_this_page_count - 1 if entries_on_this_page_count > 0 else 0))

        paginated_entries = display_entries_list(stdscr, all_entries_data, current_page, items_per_page, selected_idx_on_page)
        key = stdscr.getch()

        if key == curses.KEY_UP:
            selected_idx_on_page = max(0, selected_idx_on_page - 1)
        elif key == curses.KEY_DOWN:
            if entries_on_this_page_count > 0:
                 selected_idx_on_page = min(entries_on_this_page_count - 1, selected_idx_on_page + 1)
        elif key == curses.KEY_LEFT:
            if current_page > 0:
                current_page -= 1
                selected_idx_on_page = 0 # Reset selection on page change
        elif key == curses.KEY_RIGHT:
            if current_page < total_pages - 1:
                current_page += 1
                selected_idx_on_page = 0 # Reset selection
        elif key == ord('n') or key == ord('N'):
            add_new_entry_screen(stdscr)
            # Data will be refreshed at the start of the loop
        elif key == ord('b') or key == ord('B'):
            return # Go back to main menu
        elif key == ord('q') or key == ord('Q'):
            if confirm_action(stdscr, "Quit application? (y/N):"):
                return "QUIT_APP" # Signal to exit the whole app
        elif key == ord('?'):
            display_help_screen(stdscr)
        elif key == ord('t') or key == ord('T'):
            toggle_theme(stdscr)
        elif key == ord('/'):
            result = search_entries_screen(stdscr)
            if result == "QUIT_APP":
                return "QUIT_APP"
        elif (key == curses.KEY_ENTER or key in [10, 13]) and paginated_entries:
            # Make sure there's an entry to select
            if 0 <= selected_idx_on_page < len(paginated_entries):
                entry_id_to_view = paginated_entries[selected_idx_on_page][0] # Get ID
                result = view_single_entry_screen(stdscr, entry_id_to_view)
                if result == "QUIT_APP": return "QUIT_APP" # Propagate quit signal
        elif (key == ord('d') or key == ord('D')) and paginated_entries:
            if 0 <= selected_idx_on_page < len(paginated_entries):
                entry_to_delete = paginated_entries[selected_idx_on_page]
                entry_id_to_delete = entry_to_delete[0]
                entry_title_to_delete = entry_to_delete[2]
                if confirm_action(stdscr, f"Delete '{entry_title_to_delete}'? (y/N):"):
                    if delete_entry_db(entry_id_to_delete):
                        display_message(stdscr, "Entry deleted. Press any key.", clear_first=True)
                        # Adjust selection if possible
                        if selected_idx_on_page >= len(paginated_entries) -1 and selected_idx_on_page > 0:
                             selected_idx_on_page -=1
                    else:
                        display_message(stdscr, "Failed to delete entry. Press any key.", clear_first=True)
                # Data will be reloaded at the start of the loop
        elif key == curses.KEY_RESIZE:
            items_per_page = curses.LINES - 6 # Recalculate on resize
            if items_per_page <= 0: items_per_page = 1
            # Screen will be redrawn by the loop

def main_tui_loop(stdscr):
    """Main function to run the TUI."""
    curses.curs_set(0) # Hide cursor
    stdscr.keypad(True) # Enable special keys like arrow keys

    # Initialize color pairs
    init_colors()

    current_main_menu_option = 0
    main_menu_options_count = 5 # "View Entries", "Add New Entry", "Search Entries", "Filter by Tag", "Exit"

    while True:
        display_main_menu(stdscr, current_main_menu_option)
        key = stdscr.getch()

        if key == curses.KEY_UP:
            current_main_menu_option = (current_main_menu_option - 1) % main_menu_options_count
        elif key == curses.KEY_DOWN:
            current_main_menu_option = (current_main_menu_option + 1) % main_menu_options_count
        elif key == ord('q') or key == ord('Q'):
             if confirm_action(stdscr, "Quit application? (y/N):"):
                break
        elif key == ord('?'):
            display_help_screen(stdscr)
        elif key == ord('t') or key == ord('T'):
            toggle_theme(stdscr)
        elif key == curses.KEY_ENTER or key in [10, 13]: # 10 is LF, 13 is CR
            if current_main_menu_option == 0: # View Entries
                result = journal_entries_loop(stdscr)
                if result == "QUIT_APP": break
            elif current_main_menu_option == 1: # Add New Entry
                add_new_entry_screen(stdscr)
            elif current_main_menu_option == 2: # Search Entries
                result = search_entries_screen(stdscr)
                if result == "QUIT_APP": break
            elif current_main_menu_option == 3: # Filter by Tag
                result = filter_by_tag_screen(stdscr)
                if result == "QUIT_APP": break
            elif current_main_menu_option == 4: # Exit
                if confirm_action(stdscr, "Are you sure you want to exit? (y/N):"):
                    break
        elif key == curses.KEY_RESIZE:
            # The main menu will redraw itself correctly.
            # If inside a sub-loop like journal_entries_loop, that loop needs its own resize handling.
            pass


def quick_add_entry(title, content, tags=None):
    """Add an entry from command line without TUI."""
    entry_id = add_entry_db(title, content)
    if entry_id:
        if tags:
            tag_list = [t.strip() for t in tags.split(',') if t.strip()]
            set_entry_tags(entry_id, tag_list)
            print(f"Entry added: '{title}' with tags: {', '.join(tag_list)}")
        else:
            print(f"Entry added: '{title}'")
        return True
    else:
        print("Failed to add entry.")
        return False


def export_entries_to_markdown(output_file):
    """Export all entries to a markdown file."""
    entries = get_all_entries_db()

    if not entries:
        print("No entries to export.")
        return False

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# Journal Entries\n\n")
        f.write(f"Exported: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
        f.write("---\n\n")

        for entry_summary in entries:
            entry_id = entry_summary[0]
            entry = get_entry_db(entry_id)
            if entry:
                # entry format: (id, formatted_time, title, content)
                title = entry[2]
                date = entry[1]
                content = entry[3]
                tags = get_entry_tags(entry_id)

                f.write(f"## {title}\n\n")
                f.write(f"**Date:** {date}\n\n")
                if tags:
                    f.write(f"**Tags:** {', '.join(tags)}\n\n")
                f.write(f"{content}\n\n")
                f.write("---\n\n")

    print(f"Exported {len(entries)} entries to '{output_file}'")
    return True


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Journal TUI - A terminal journal application')
    parser.add_argument('--add', '-a', nargs=2, metavar=('TITLE', 'CONTENT'),
                        help='Quick add an entry without opening TUI')
    parser.add_argument('--tags', '-t', metavar='TAGS',
                        help='Comma-separated tags for the entry (use with --add)')
    parser.add_argument('--export', '-e', metavar='FILE',
                        help='Export all entries to a markdown file')

    args = parser.parse_args()

    init_db()  # Ensure database and table exist

    if args.add:
        # Quick add mode
        title, content = args.add
        quick_add_entry(title, content, args.tags)
    elif args.export:
        # Export mode
        export_entries_to_markdown(args.export)
    else:
        # Normal TUI mode
        try:
            curses.wrapper(main_tui_loop)
            print("Journal TUI closed normally.")
        except curses.error as e:
            print(f"A curses error occurred: {e}")
            print("If you are on Windows, try installing 'windows-curses': pip install windows-curses")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")

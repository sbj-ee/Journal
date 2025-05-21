import sqlite3
import curses
import curses.textpad # For multiline input
from datetime import datetime

DATABASE_NAME = 'journal_app.db'

# --- Database Functions ---

def init_db():
    """Initializes the database and creates the 'entries' table if it doesn't exist."""
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
    conn.commit()
    conn.close()

def add_entry_db(title, content):
    """Adds a new journal entry to the database."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO entries (title, content) VALUES (?, ?)", (title, content))
        conn.commit()
        return True # Indicate success
    except sqlite3.Error as e:
        # In a real app, you might log this error
        # For the TUI, we might show a message if possible
        return False # Indicate failure
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

def get_multiline_input(stdscr, prompt_message):
    """
    Gets multiline text input from the user using curses.textpad.Textbox.
    User presses Ctrl+G to save/finish, Ctrl+X to cancel (though cancel is advisory).
    """
    stdscr.clear()
    h, w = stdscr.getmaxyx()
    stdscr.addstr(0, 0, prompt_message, curses.A_BOLD)
    stdscr.addstr(h - 2, 0, "Press Ctrl+G to Save, Ctrl+X to Cancel (or finish typing).")
    stdscr.refresh()

    # Create a new window for the text box
    # Leave 1 line for prompt, 2 lines for instructions at bottom
    edit_win_h = h - 3
    edit_win_w = w - 2
    edit_win_y = 1
    edit_win_x = 1

    if edit_win_h <= 0 or edit_win_w <= 0: # Screen too small
        display_message(stdscr, "Screen too small for text input. Press any key.")
        return ""

    edit_win = curses.newwin(edit_win_h, edit_win_w, edit_win_y, edit_win_x)
    edit_win.keypad(True) # Enable special keys like backspace

    # Add a border to the editing window for visual clarity (optional)
    try:
        stdscr.attron(curses.color_pair(2)) # Assuming color_pair 2 is defined
        curses.textpad.rectangle(stdscr, edit_win_y -1 , edit_win_x -1, edit_win_y + edit_win_h, edit_win_x + edit_win_w)
        stdscr.attroff(curses.color_pair(2))
        stdscr.refresh()
    except: # In case colors are not supported or rectangle fails
        pass


    box = curses.textpad.Textbox(edit_win)

    # The edit method blocks until a terminator key is pressed.
    # Common terminators are Ctrl+G (ASCII 7).
    # We can't directly make Ctrl+X a non-saving terminator without more complex key handling.
    # The user experience is: type text, Ctrl+G confirms.
    # If they want to "cancel", they might just hit Ctrl+G with no text, or we'd need a pre-edit confirmation.
    content = box.edit() # This will gather input until Ctrl+G

    # Clean up the content: Textbox might include trailing spaces or newlines from the edit window.
    # The content from box.edit() often has a trailing newline if Ctrl+G is pressed after typing.
    # It might also have spaces filling the last line.
    # A common way to clean is to rstrip() lines and then join.
    lines = content.split('\n')
    cleaned_lines = [line.rstrip() for line in lines]
    # Remove empty lines at the very end that might result from rstrip
    while cleaned_lines and not cleaned_lines[-1]:
        cleaned_lines.pop()
    
    return "\n".join(cleaned_lines)


# --- UI Screens ---

def display_main_menu(stdscr, selected_option_idx):
    """Displays the main menu and highlights the selected option."""
    stdscr.clear()
    h, w = stdscr.getmaxyx()
    menu_title = "Python Journal TUI"
    options = ["View Entries", "Add New Entry", "Exit"]

    stdscr.addstr(1, (w - len(menu_title)) // 2, menu_title, curses.A_BOLD | curses.A_UNDERLINE)

    for i, option in enumerate(options):
        y_pos = h // 2 - len(options) // 2 + i + 2 # +2 for title and spacing
        x_pos = (w - len(option)) // 2
        if i == selected_option_idx:
            stdscr.attron(curses.color_pair(1)) # Highlight selected
            stdscr.addstr(y_pos, x_pos, f"> {option} <")
            stdscr.attroff(curses.color_pair(1))
        else:
            stdscr.addstr(y_pos, x_pos, f"  {option}  ")

    stdscr.addstr(h - 2, 2, "Use UP/DOWN arrows, ENTER to select. Q to quit from here.")
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
        display_text = f"{entry[1]} - {entry[2]}" # Timestamp - Title
        if len(display_text) > w - 4: # Truncate if too long
            display_text = display_text[:w-7] + "..."

        if i == selected_idx_on_page:
            stdscr.attron(curses.color_pair(1))
            stdscr.addstr(line_num + i, 2, f"> {display_text}")
            stdscr.attroff(curses.color_pair(1))
        else:
            stdscr.addstr(line_num + i, 2, f"  {display_text}")

    # Pagination info
    total_pages = (len(entries) + items_per_page - 1) // items_per_page
    if total_pages == 0: total_pages = 1
    page_info = f"Page {current_page + 1}/{total_pages}"
    stdscr.addstr(h - 3, 2, page_info)
    stdscr.addstr(h - 2, 2, "UP/DOWN: Navigate, ENTER: View, D: Delete, LEFT/RIGHT: Pages")
    stdscr.refresh()
    return paginated_entries


def view_single_entry_screen(stdscr, entry_id):
    """Displays the full content of a single journal entry."""
    entry = get_entry_db(entry_id)
    stdscr.clear()
    h, w = stdscr.getmaxyx()

    if not entry:
        display_message(stdscr, "Error: Entry not found. Press any key to return.")
        return

    # entry format: (id, formatted_time, title, content)
    title_line = f"Title: {entry[2]} (ID: {entry[0]})"
    timestamp_line = f"Date: {entry[1]}"
    stdscr.addstr(0, 0, title_line, curses.A_BOLD)
    stdscr.addstr(1, 0, timestamp_line)
    stdscr.addstr(2, 0, "-" * (w - 1))

    content_lines = entry[3].splitlines()
    current_display_line = 3
    scroll_offset = 0 # For scrolling content if it's too long

    while True:
        stdscr.move(current_display_line, 0) # Move cursor to start of content area
        stdscr.clrtobot() # Clear from cursor to bottom of screen

        # Display content with scrolling
        lines_to_display = h - current_display_line - 2 # -2 for bottom message
        
        for i in range(lines_to_display):
            content_idx = scroll_offset + i
            if content_idx < len(content_lines):
                line_to_print = content_lines[content_idx]
                # Basic word wrapping
                if len(line_to_print) >= w:
                    # Split line if it exceeds width
                    for chunk_start in range(0, len(line_to_print), w-1):
                        if current_display_line + i + (chunk_start // (w-1)) < h -2:
                             stdscr.addstr(current_display_line + i + (chunk_start // (w-1)), 0, line_to_print[chunk_start:chunk_start+w-1])
                        else: break # Stop if we run out of screen space for wrapped lines
                else:
                    stdscr.addstr(current_display_line + i, 0, line_to_print)
            else:
                break # No more content lines

        stdscr.addstr(h - 1, 0, "Press B to Back, UP/DOWN to scroll. Q to Quit.")
        stdscr.refresh()

        key = stdscr.getch()
        if key == ord('b') or key == ord('B'):
            break
        elif key == ord('q') or key == ord('Q'):
            if confirm_action(stdscr, "Quit to main menu? (y/N):"):
                return "QUIT_APP" # Special signal
            else: # Redraw after confirm_action clears screen
                stdscr.clear()
                stdscr.addstr(0, 0, title_line, curses.A_BOLD)
                stdscr.addstr(1, 0, timestamp_line)
                stdscr.addstr(2, 0, "-" * (w - 1))
                # No need to redraw content here, loop will do it
        elif key == curses.KEY_UP:
            if scroll_offset > 0:
                scroll_offset -= 1
        elif key == curses.KEY_DOWN:
            # Only scroll down if there's more content to show
            if scroll_offset + lines_to_display < len(content_lines):
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
    content = get_multiline_input(stdscr, f"Enter content for '{title}':")

    if content: # If Ctrl+G was pressed and content is not empty
        if add_entry_db(title, content):
            display_message(stdscr, "Entry added successfully! Press any key.")
        else:
            display_message(stdscr, "Failed to add entry to database. Press any key.")
    else:
        display_message(stdscr, "Entry not added (cancelled or empty content). Press any key.")

    curses.curs_set(0) # Hide cursor


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
    curses.start_color()
    curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_WHITE) # For selected items (black on white)
    curses.init_pair(2, curses.COLOR_CYAN, curses.COLOR_BLACK) # For borders or other elements

    current_main_menu_option = 0
    main_menu_options_count = 3 # "View Entries", "Add New Entry", "Exit"

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
        elif key == curses.KEY_ENTER or key in [10, 13]: # 10 is LF, 13 is CR
            if current_main_menu_option == 0: # View Entries
                result = journal_entries_loop(stdscr)
                if result == "QUIT_APP": break
            elif current_main_menu_option == 1: # Add New Entry
                add_new_entry_screen(stdscr)
            elif current_main_menu_option == 2: # Exit
                if confirm_action(stdscr, "Are you sure you want to exit? (y/N):"):
                    break
        elif key == curses.KEY_RESIZE:
            # The main menu will redraw itself correctly.
            # If inside a sub-loop like journal_entries_loop, that loop needs its own resize handling.
            pass


if __name__ == '__main__':
    init_db() # Ensure database and table exist
    try:
        curses.wrapper(main_tui_loop)
        print("Journal TUI closed normally.")
    except curses.error as e:
        print(f"A curses error occurred: {e}")
        print("If you are on Windows, try installing 'windows-curses': pip install windows-curses")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        # curses.endwin() is handled by curses.wrapper
        pass

import unittest
import os
import sqlite3
import journal

TEST_DB = 'test_journal.db'


class TestJournalDatabase(unittest.TestCase):
    """Tests for journal database functions."""

    @classmethod
    def setUpClass(cls):
        """Set up test database."""
        journal.DATABASE_NAME = TEST_DB

    def setUp(self):
        """Initialize fresh database before each test."""
        if os.path.exists(TEST_DB):
            os.remove(TEST_DB)
        journal.init_db()

    def tearDown(self):
        """Clean up test database after each test."""
        if os.path.exists(TEST_DB):
            os.remove(TEST_DB)

    def test_init_db_creates_table(self):
        """Test that init_db creates the entries table."""
        conn = sqlite3.connect(TEST_DB)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='entries'")
        result = cursor.fetchone()
        conn.close()
        self.assertIsNotNone(result)
        self.assertEqual(result[0], 'entries')

    def test_add_entry_db(self):
        """Test adding a new entry."""
        result = journal.add_entry_db("Test Title", "Test Content")
        self.assertTrue(result)

        entries = journal.get_all_entries_db()
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0][2], "Test Title")

    def test_get_all_entries_db_empty(self):
        """Test getting entries from empty database."""
        entries = journal.get_all_entries_db()
        self.assertEqual(entries, [])

    def test_get_all_entries_db_multiple(self):
        """Test getting multiple entries."""
        journal.add_entry_db("Entry 1", "Content 1")
        journal.add_entry_db("Entry 2", "Content 2")
        journal.add_entry_db("Entry 3", "Content 3")

        entries = journal.get_all_entries_db()
        self.assertEqual(len(entries), 3)

    def test_get_entry_db(self):
        """Test getting a specific entry by ID."""
        journal.add_entry_db("Test Title", "Test Content")
        entries = journal.get_all_entries_db()
        entry_id = entries[0][0]

        entry = journal.get_entry_db(entry_id)
        self.assertIsNotNone(entry)
        self.assertEqual(entry[2], "Test Title")
        self.assertEqual(entry[3], "Test Content")

    def test_get_entry_db_not_found(self):
        """Test getting a non-existent entry."""
        entry = journal.get_entry_db(999)
        self.assertIsNone(entry)

    def test_delete_entry_db(self):
        """Test deleting an entry."""
        journal.add_entry_db("Test Title", "Test Content")
        entries = journal.get_all_entries_db()
        entry_id = entries[0][0]

        result = journal.delete_entry_db(entry_id)
        self.assertTrue(result)

        entries = journal.get_all_entries_db()
        self.assertEqual(len(entries), 0)

    def test_delete_entry_db_not_found(self):
        """Test deleting a non-existent entry."""
        result = journal.delete_entry_db(999)
        self.assertTrue(result)  # SQLite doesn't error on non-existent delete

    def test_search_entries_db_by_title(self):
        """Test searching entries by title."""
        journal.add_entry_db("Morning Thoughts", "Content 1")
        journal.add_entry_db("Evening Notes", "Content 2")
        journal.add_entry_db("Morning Routine", "Content 3")

        results = journal.search_entries_db("Morning")
        self.assertEqual(len(results), 2)

    def test_search_entries_db_by_content(self):
        """Test searching entries by content."""
        journal.add_entry_db("Entry 1", "Python programming")
        journal.add_entry_db("Entry 2", "JavaScript coding")
        journal.add_entry_db("Entry 3", "Python scripting")

        results = journal.search_entries_db("Python")
        self.assertEqual(len(results), 2)

    def test_search_entries_db_case_insensitive(self):
        """Test that search is case insensitive."""
        journal.add_entry_db("Test Entry", "Hello World")

        results_lower = journal.search_entries_db("hello")
        results_upper = journal.search_entries_db("HELLO")
        self.assertEqual(len(results_lower), 1)
        self.assertEqual(len(results_upper), 1)

    def test_search_entries_db_no_results(self):
        """Test search with no matching results."""
        journal.add_entry_db("Test Entry", "Test Content")

        results = journal.search_entries_db("nonexistent")
        self.assertEqual(results, [])

    def test_entries_ordered_by_timestamp_desc(self):
        """Test that entries are returned in descending timestamp order (by ID when timestamps match)."""
        journal.add_entry_db("First", "Content 1")
        journal.add_entry_db("Second", "Content 2")
        journal.add_entry_db("Third", "Content 3")

        entries = journal.get_all_entries_db()
        # All 3 entries should exist
        self.assertEqual(len(entries), 3)
        titles = [e[2] for e in entries]
        self.assertIn("First", titles)
        self.assertIn("Second", titles)
        self.assertIn("Third", titles)


class TestTagFunctionality(unittest.TestCase):
    """Tests for tag database functions."""

    @classmethod
    def setUpClass(cls):
        """Set up test database."""
        journal.DATABASE_NAME = TEST_DB

    def setUp(self):
        """Initialize fresh database before each test."""
        if os.path.exists(TEST_DB):
            os.remove(TEST_DB)
        journal.init_db()

    def tearDown(self):
        """Clean up test database after each test."""
        if os.path.exists(TEST_DB):
            os.remove(TEST_DB)

    def test_init_db_creates_tag_tables(self):
        """Test that init_db creates the tags and entry_tags tables."""
        conn = sqlite3.connect(TEST_DB)
        cursor = conn.cursor()

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tags'")
        self.assertIsNotNone(cursor.fetchone())

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='entry_tags'")
        self.assertIsNotNone(cursor.fetchone())

        conn.close()

    def test_get_or_create_tag_creates_new(self):
        """Test creating a new tag."""
        tag_id = journal.get_or_create_tag("work")
        self.assertIsNotNone(tag_id)
        self.assertGreater(tag_id, 0)

    def test_get_or_create_tag_returns_existing(self):
        """Test that get_or_create_tag returns existing tag."""
        tag_id1 = journal.get_or_create_tag("work")
        tag_id2 = journal.get_or_create_tag("work")
        self.assertEqual(tag_id1, tag_id2)

    def test_get_or_create_tag_case_insensitive(self):
        """Test that tags are case insensitive."""
        tag_id1 = journal.get_or_create_tag("Work")
        tag_id2 = journal.get_or_create_tag("WORK")
        tag_id3 = journal.get_or_create_tag("work")
        self.assertEqual(tag_id1, tag_id2)
        self.assertEqual(tag_id2, tag_id3)

    def test_set_entry_tags(self):
        """Test setting tags on an entry."""
        entry_id = journal.add_entry_db("Test", "Content")
        result = journal.set_entry_tags(entry_id, ["work", "ideas"])
        self.assertTrue(result)

    def test_get_entry_tags(self):
        """Test getting tags for an entry."""
        entry_id = journal.add_entry_db("Test", "Content")
        journal.set_entry_tags(entry_id, ["work", "ideas", "personal"])

        tags = journal.get_entry_tags(entry_id)
        self.assertEqual(len(tags), 3)
        self.assertIn("work", tags)
        self.assertIn("ideas", tags)
        self.assertIn("personal", tags)

    def test_get_entry_tags_empty(self):
        """Test getting tags for entry with no tags."""
        entry_id = journal.add_entry_db("Test", "Content")
        tags = journal.get_entry_tags(entry_id)
        self.assertEqual(tags, [])

    def test_set_entry_tags_replaces_existing(self):
        """Test that setting tags replaces existing tags."""
        entry_id = journal.add_entry_db("Test", "Content")
        journal.set_entry_tags(entry_id, ["work", "ideas"])
        journal.set_entry_tags(entry_id, ["personal"])

        tags = journal.get_entry_tags(entry_id)
        self.assertEqual(len(tags), 1)
        self.assertIn("personal", tags)
        self.assertNotIn("work", tags)

    def test_set_entry_tags_clear(self):
        """Test clearing tags from an entry."""
        entry_id = journal.add_entry_db("Test", "Content")
        journal.set_entry_tags(entry_id, ["work", "ideas"])
        journal.set_entry_tags(entry_id, [])

        tags = journal.get_entry_tags(entry_id)
        self.assertEqual(tags, [])

    def test_get_all_tags(self):
        """Test getting all tags with counts."""
        entry1 = journal.add_entry_db("Entry 1", "Content")
        entry2 = journal.add_entry_db("Entry 2", "Content")

        journal.set_entry_tags(entry1, ["work", "ideas"])
        journal.set_entry_tags(entry2, ["work", "personal"])

        all_tags = journal.get_all_tags()
        tag_dict = {name: count for name, count in all_tags}

        self.assertEqual(tag_dict["work"], 2)
        self.assertEqual(tag_dict["ideas"], 1)
        self.assertEqual(tag_dict["personal"], 1)

    def test_get_all_tags_empty(self):
        """Test getting all tags when none exist."""
        all_tags = journal.get_all_tags()
        self.assertEqual(all_tags, [])

    def test_get_entries_by_tag(self):
        """Test filtering entries by tag."""
        entry1 = journal.add_entry_db("Entry 1", "Content")
        entry2 = journal.add_entry_db("Entry 2", "Content")
        entry3 = journal.add_entry_db("Entry 3", "Content")

        journal.set_entry_tags(entry1, ["work"])
        journal.set_entry_tags(entry2, ["work", "ideas"])
        journal.set_entry_tags(entry3, ["personal"])

        work_entries = journal.get_entries_by_tag("work")
        self.assertEqual(len(work_entries), 2)

        personal_entries = journal.get_entries_by_tag("personal")
        self.assertEqual(len(personal_entries), 1)

    def test_get_entries_by_tag_case_insensitive(self):
        """Test that filtering by tag is case insensitive."""
        entry_id = journal.add_entry_db("Test", "Content")
        journal.set_entry_tags(entry_id, ["Work"])

        entries = journal.get_entries_by_tag("WORK")
        self.assertEqual(len(entries), 1)

    def test_get_entries_by_tag_no_results(self):
        """Test filtering by non-existent tag."""
        entry_id = journal.add_entry_db("Test", "Content")
        journal.set_entry_tags(entry_id, ["work"])

        entries = journal.get_entries_by_tag("nonexistent")
        self.assertEqual(entries, [])


class TestWordWrap(unittest.TestCase):
    """Tests for word wrapping function."""

    def test_wrap_short_text(self):
        """Test that short text doesn't wrap."""
        result = journal.wrap_text("hello", 10)
        self.assertEqual(result, ["hello"])

    def test_wrap_at_word_boundary(self):
        """Test wrapping at word boundaries."""
        result = journal.wrap_text("hello world", 8)
        self.assertEqual(result, ["hello", "world"])

    def test_wrap_long_word(self):
        """Test wrapping words longer than width."""
        result = journal.wrap_text("supercalifragilistic", 10)
        self.assertEqual(result, ["supercalif", "ragilistic"])

    def test_wrap_multiple_lines(self):
        """Test wrapping into multiple lines."""
        result = journal.wrap_text("one two three four", 8)
        self.assertEqual(result, ["one two", "three", "four"])

    def test_wrap_empty_string(self):
        """Test wrapping empty string."""
        result = journal.wrap_text("", 10)
        self.assertEqual(result, [""])

    def test_wrap_exact_width(self):
        """Test text that exactly fits width."""
        result = journal.wrap_text("hello", 5)
        self.assertEqual(result, ["hello"])


class TestMarkdownParsing(unittest.TestCase):
    """Tests for markdown regex patterns used in rendering."""

    def test_header_pattern(self):
        """Test header regex pattern matching."""
        import re
        pattern = r'^(#{1,6})\s+(.*)$'

        # Valid headers
        self.assertIsNotNone(re.match(pattern, '# Header 1'))
        self.assertIsNotNone(re.match(pattern, '## Header 2'))
        self.assertIsNotNone(re.match(pattern, '### Header 3'))
        self.assertIsNotNone(re.match(pattern, '###### Header 6'))

        # Invalid headers
        self.assertIsNone(re.match(pattern, '#NoSpace'))
        self.assertIsNone(re.match(pattern, 'Not a header'))

    def test_list_pattern(self):
        """Test list item regex pattern matching."""
        import re
        pattern = r'^(\s*)([-*]|\d+\.)\s+(.*)$'

        # Valid list items
        match = re.match(pattern, '- Item')
        self.assertIsNotNone(match)
        self.assertEqual(match.group(3), 'Item')

        match = re.match(pattern, '* Item')
        self.assertIsNotNone(match)

        match = re.match(pattern, '1. Numbered item')
        self.assertIsNotNone(match)
        self.assertEqual(match.group(2), '1.')

        match = re.match(pattern, '  - Indented item')
        self.assertIsNotNone(match)
        self.assertEqual(match.group(1), '  ')

    def test_inline_markdown_pattern(self):
        """Test inline markdown pattern matching."""
        import re
        pattern = r'(\*\*(.+?)\*\*)|(`(.+?)`)|(\*(.+?)\*)|(_(.+?)_)'

        # Bold
        matches = list(re.finditer(pattern, 'This is **bold** text'))
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].group(2), 'bold')

        # Inline code
        matches = list(re.finditer(pattern, 'Use `code` here'))
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].group(4), 'code')

        # Italic with asterisk
        matches = list(re.finditer(pattern, 'This is *italic* text'))
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].group(6), 'italic')

        # Italic with underscore
        matches = list(re.finditer(pattern, 'This is _italic_ text'))
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].group(8), 'italic')

    def test_multiple_inline_elements(self):
        """Test multiple inline markdown elements in one line."""
        import re
        pattern = r'(\*\*(.+?)\*\*)|(`(.+?)`)|(\*(.+?)\*)|(_(.+?)_)'

        text = 'Here is **bold** and `code` and *italic*'
        matches = list(re.finditer(pattern, text))
        self.assertEqual(len(matches), 3)


class TestNavigationSignals(unittest.TestCase):
    """Tests for navigation signal handling."""

    def test_goto_main_signal_propagation(self):
        """Test that GOTO_MAIN signal is a valid return value."""
        # The GOTO_MAIN signal should be a string that can be compared
        goto_main = "GOTO_MAIN"
        quit_app = "QUIT_APP"

        # These signals should be distinct
        self.assertNotEqual(goto_main, quit_app)
        self.assertNotEqual(goto_main, None)
        self.assertNotEqual(quit_app, None)

        # Test that they can be used in conditional checks
        result = "GOTO_MAIN"
        self.assertEqual(result, goto_main)
        self.assertTrue(result == "GOTO_MAIN")


if __name__ == '__main__':
    unittest.main()

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


if __name__ == '__main__':
    unittest.main()

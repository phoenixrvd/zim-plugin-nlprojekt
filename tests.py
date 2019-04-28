import unittest
import os
from unittest.mock import MagicMock

from . import *


class TestProjectEntry(unittest.TestCase):

    entry = None

    def setUp(self):
        entry = ProjectEntry()
        entry.head_line = '[[Statik:Intern:0589 interner Support]]'
        entry.content.append('\n\n[*] Ubutu auf Altem laptop zurückgesetztz')
        entry.content.append('\t\t[*] Mount-Verzeichnisse repariert')
        entry.content.append('\n\n')
        entry.time_entry = '[*] @zp 2,5 [ 1,5 [ Hier interne Notiz\n'
        self.entry = entry

    def test_parse_journal_day(self):
        dirname = os.path.dirname(__file__)
        fixture_path = os.path.join(dirname, 'tests_fixtures/journal_day.txt')
        with open(fixture_path, 'r') as f:
            content_lines = f.readlines()
            project_entries = ProjectsList.parse_journal_day(content_lines) # type: ProjectsList
        self.assertEqual(2, len(project_entries))
        self.assertEqual(3.5, project_entries.time_total())

    def test_number(self):
        self.assertEqual(589, self.entry.number())

    def test_description(self):
        self.assertEqual('[*] Ubutu auf Altem laptop zurückgesetztz\n\t\t[*] Mount-Verzeichnisse repariert', self.entry.details())

    def test_time_total(self):
        self.entry.time_entry = '[*] @zp 2,5 [ 1,5 [ Hier interne Notiz\n'
        self.assertEqual(2.5, self.entry.time_total())

        self.entry.time_entry = '[*] @zp 2 [ 1,5 [ Hier interne Notiz\n'
        self.assertEqual(2, self.entry.time_total())

    def test_time_client(self):
        self.entry.time_entry = '[*] @zp 2,5 [ 1,5 [ Hier interne Notiz\n'
        self.assertEqual(1.5, self.entry.time_client())

        self.entry.time_entry = '[*] @zp 2,5 [Hier interne Notiz\n'
        self.assertEqual(2.5, self.entry.time_client())

        self.entry.time_entry = '[*] @zp 0 [Hier interne Notiz\n'
        self.assertEqual(0, self.entry.time_client())

        self.entry.time_entry = '[*] @zp 4 [Hier interne Notiz\n'
        self.assertEqual(4, self.entry.time_client())

    def test_internal_comment(self):
        self.entry.time_entry = '[*] @zp 2,5 [ 1,5 [c Hier interne Notiz  \n'
        self.assertEqual('Hier interne Notiz', self.entry.internal_comment())

        self.entry.time_entry = '[*] @zp 2,5 '
        self.assertEqual('', self.entry.internal_comment())

        self.entry.time_entry = '[*] @zp 2,5 [c \n'
        self.assertEqual('', self.entry.internal_comment())

    def test_is_new(self):
        self.entry.time_entry = '[*] @zp 2,5 [ 1,5 [c Hier interne Notiz  \n'
        self.assertFalse(self.entry.is_new())

        self.entry.time_entry = '[ ] @zp 2,5 [ 1,5 [c Hier interne Notiz  \n'
        self.assertTrue(self.entry.is_new())

    def test_check_description(self):
        self.entry.time_entry = '[ ] @zp 1 [c Bemerkung'
        self.entry.content = ['test']
        self.entry.head_line = 'test:1234 foobar'
        expected = '\n'.join([
            'test:1234 foobar',
            '',
            'ID: 1234\n'
            '===========================',
            'Beschreibung:',
            'test',
            '===========================',
            'Interne Bemerkung: Bemerkung',
            '===========================',
            'Zeitaufwand (Gesamt): 1.0',
            'Zeitaufwand (Für Kunden): 1.0'
        ])
        current = self.entry.check_description()
        self.assertEqual(expected, current)


class TestRpc(unittest.TestCase):

    def test_addVorgang(self):
        rpc = self.rpc(server_response=3.0)
        rpc.addVorgang(1234, '2019-04-31', 3.2, 'TestVorgang\n Mehrzeilig')
        rpc.send_request.assert_called_once_with('addVorgang', [1234, '2019-04-31', 3.2, 'TestVorgang\n Mehrzeilig'])

    def rpc(self, server_response):
        rpc = Rpc('http://localhost:1420')
        rpc.send_request = MagicMock(return_value = server_response)
        return rpc


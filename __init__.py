import inspect
import re
import sys
from typing import List

from zim.actions import action
from zim.config import ConfigDict
from zim.formats import CHECKED_BOX, get_dumper
from zim.gui.pageview import PageViewExtension, TextBuffer
from zim.gui.widgets import Dialog, ErrorDialog
from zim.plugins import PluginClass

try:
    import requests
except ImportError:
    requests = None

try:
    import json
except ImportError:
    json = None


class NlProjectPlugin(PluginClass):
    plugin_info = {
        'name': _('NL-Projekt'),  # T: plugin name
        'description': _('Integration in NL-Projekt.'),  # T: plugin description
        'author': 'Viacheslav Wolf',
        'help': 'Plugins:NL-Projekt',
    }

    plugin_preferences = (
        ('url', 'string', _('JSON-RPC-Socket'), 'http://localhost:1420'),  # T: Label for plugin preference
    )

    @classmethod
    def check_dependencies(cls):
        sys_python_version = sys.version_info[0] >= 3
        return (sys_python_version and requests and json), [
            ('python3', sys_python_version, True),
            ('requests', requests, True),
            ('json', json, True),
        ]


class NlProjectPageViewExtension(PageViewExtension):

    @action(_('_Zeiten nach NL-Projekt übertragen'), accelerator='<Control><Shift>K', menuhints='tools')  # T: Menu item
    def on_submit_time_for_all_projects(self):
        lines = get_dumper('wiki').dump(self.pageview.get_parsetree())
        entries = ProjectsList.parse_journal_day(lines)

        cursor_position = self.pageview.get_cursor_pos()

        self.pageview.set_cursor_pos(0)
        self.pageview.find('@zp')

        for entry in entries:
            if entry.is_new():
                CheckEntryDialog(self, entry, entries).run()
            self.pageview.find_next()

        self.pageview.set_cursor_pos(cursor_position)
        self.pageview.hide_find()
        pass


# Allem RPC-Methoden innerhalb des Objektes werden IMPLIZIT deklariert. D.h. Mit allen Attributen, Typen und
# Rückgabe, Zweck: Man muss wissen was übergeben werden kann und was zurückgegeben wird
class Rpc:

    def __init__(self, url: str):
        self.url = url

    # TODO: Bug-Report → NL-Projekt muss auch nicht abrechenbare Zeit + Interne kommentare erlauben!
    def addVorgang(self, projekt_nummer: int, datum: str, zeit: float, message: str) -> float:
        return self.proxy_method(projekt_nummer, datum, zeit, message)

    def proxy_method(self, *args):
        method_args = list(args)
        method_name = inspect.stack()[1].function
        return self.send_request(method_name, method_args)

    def send_request(self, method_name: str, method_args:  list):
        headers = {'content-type': 'application/json'}
        payload = {
            'method': method_name,
            'params': method_args,
            'jsonrpc': '2.0',
            'id': 0,
        }
        response = requests.post(self.url, data=json.dumps(payload), headers=headers).json()
        assert response['jsonrpc']
        return response['result']

class ProjectEntry:

    def __init__(self):
        self.time_entry = ''
        self.head_line = ''
        self.content = []

    def number(self):
        return int(re.search(r':(\d{4}) ', self.head_line).group(1))

    def details(self):
        return '\n'.join(self.content).strip()

    def time_total(self):
        return self.time_format(re.search(r'@zp (\d+(,\d+)?)', self.time_entry).group(1))

    def time_client(self):
        matches = re.search(r'(\d+).*\[.*(\d+(,\d+))', self.time_entry)

        if matches is None:
            return self.time_total()

        return self.time_format(matches.group(2))

    @staticmethod
    def time_format(value):
        return float(value.replace(',', '.'))

    def internal_comment(self):
        matches = re.search(r'\[c ?(.*)', self.time_entry)

        if matches is None:
            return ''

        return matches.group(1).strip()

    def is_new(self):
        return re.search(r'^\[ \] @', self.time_entry) is not None

    def check_description(self):
        description = '\n'.join([
            self.head_line.strip(']['),
            '',
            'ID: ' + str(self.number()),
            '===========================',
            'Beschreibung:',
            self.details(),
            '===========================',
            'Interne Bemerkung: ' + self.internal_comment(),
            '===========================',
            'Zeitaufwand (Gesamt): ' + str(self.time_total()),
            'Zeitaufwand (Für Kunden): ' + str(self.time_client())
        ])
        return description


class ProjectsList(List):

    def __init__(self):
        super().__init__()
        self.__time_total = 0.0

    def append(self, entry: ProjectEntry) -> None:
        self.__time_total += entry.time_total()
        return super().append(entry)

    def time_total(self) -> float:
        return self.__time_total

    @staticmethod
    def parse_journal_day(content_lines) -> List:
        projects = ProjectsList()
        project_entry = None

        for line in content_lines:

            if re.match(r'^\[\[.+:\d{4}.+', line) and project_entry is None:
                project_entry = ProjectEntry()
                project_entry.head_line = line.strip()
                continue

            if re.match(r'.*(@zp)', line):
                project_entry.time_entry = line.strip()
                projects.append(project_entry)
                project_entry = None
                continue

            if project_entry:
                project_entry.content.append(line.strip())
                continue

        return projects


class CheckEntryDialog(Dialog):

    def __init__(self, parent: PageViewExtension,  entry: ProjectEntry, projects_list: ProjectsList):
        self.textview = parent.pageview.textview
        self.date = '-'.join(parent.pageview.get_page().source_file.pathnames[-3:]).rstrip('.txt')
        self.entry = entry

        preferences = parent.plugin.preferences  # type: ConfigDict
        rpc_server_socket = preferences.get('url')
        self.rpc = Rpc(rpc_server_socket)

        Dialog.__init__(
            self,
            parent,
            title=_('Bitte den Eintrag überprüfen (Stunden: {0:.2f} von {1:.2f})').format(
                entry.time_total(),
                projects_list.time_total(),
            ),
            button=_('Alles korrekt. Jetzt Speichern')
        )  # T: Dialog button
        self.add_form([entry.check_description()], {})

    def do_response_ok(self) -> bool:
        try:
            entry = self.entry
            self.rpc.addVorgang(entry.number(), self.date, entry.time_total(), entry.details())
            buffer = self.textview.get_buffer()  # type: TextBuffer
            buffer.toggle_checkbox_for_cursor_or_selection(CHECKED_BOX, True)
            return True
        except Exception as error:
            ErrorDialog(self, str(error)).run()

        return False

"""
Preview dialog — shown immediately when a magnet link is opened.

Flow:
  1. Opens with a spinner while MetadataFetcher talks to the torrent subprocess.
  2. Once metadata arrives the file tree, name, and size are shown.
  3. User picks a save folder and clicks Download, or closes the dialog to cancel.
"""
import os
import urllib.parse
from pathlib import Path

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTreeWidget, QTreeWidgetItem, QLineEdit, QFileDialog,
    QFrame, QWidget, QStackedWidget,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor

from ui.widgets import Spinner
from core.settings import load as load_settings, save as save_settings
from utils.format import format_size


class PreviewDialog(QDialog):
    """
    Shows torrent metadata and lets the user confirm / choose save location.
    Emits download_requested(magnet_uri, save_path, torrent_name) on confirm.
    """
    download_requested = pyqtSignal(str, str, str)  # (magnet_uri, save_path, name)

    def __init__(self, session, magnet_uri: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Magnet Fisher')
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setMinimumWidth(540)
        self.setMaximumWidth(720)

        self._magnet_uri   = magnet_uri
        self._session      = session
        self._worker       = None
        self._torrent_name = ''

        self._build_ui()
        self._fetch_metadata()

    # ── UI ─────────────────────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(22, 18, 22, 22)
        root.setSpacing(14)

        # Stacked widget: page 0 = spinner, page 1 = metadata
        self._stack = QStackedWidget()
        root.addWidget(self._stack)

        # ── Page 0: spinner ──────────────────────────────────────────
        spinner_page = QWidget()
        sp = QVBoxLayout(spinner_page)
        sp.setContentsMargins(0, 20, 0, 20)
        self._spinner = Spinner('Connecting to peers…')
        self._spinner.setMinimumHeight(72)
        sp.addWidget(self._spinner)
        self._stack.addWidget(spinner_page)

        # ── Page 1: metadata ─────────────────────────────────────────
        meta_page = QWidget()
        mp = QVBoxLayout(meta_page)
        mp.setContentsMargins(0, 0, 0, 0)
        mp.setSpacing(8)

        self._name_lbl = QLabel()
        self._name_lbl.setObjectName('heading')
        self._name_lbl.setWordWrap(True)
        f = self._name_lbl.font()
        f.setPointSize(12)
        f.setWeight(QFont.Weight.DemiBold)
        self._name_lbl.setFont(f)
        mp.addWidget(self._name_lbl)

        self._meta_lbl = QLabel()
        self._meta_lbl.setObjectName('muted')
        mp.addWidget(self._meta_lbl)

        self._tree = QTreeWidget()
        self._tree.setHeaderLabels(['  Name', 'Size'])
        self._tree.setColumnWidth(0, 360)
        self._tree.setColumnWidth(1, 90)
        self._tree.header().setStretchLastSection(False)
        self._tree.setMinimumHeight(160)
        self._tree.setMaximumHeight(300)
        self._tree.setIndentation(16)
        mp.addWidget(self._tree)

        self._stack.addWidget(meta_page)

        # Divider
        div = QFrame()
        div.setFrameShape(QFrame.Shape.HLine)
        root.addWidget(div)

        # Save-path row
        path_row = QHBoxLayout()
        path_row.setSpacing(8)

        save_lbl = QLabel('Save to')
        save_lbl.setObjectName('muted')
        save_lbl.setFixedWidth(50)
        path_row.addWidget(save_lbl)

        settings = load_settings()
        default_path = settings.get('save_path', str(Path.home() / 'Downloads'))
        self._path_input = QLineEdit(default_path)
        self._path_input.setPlaceholderText('Choose download folder…')
        path_row.addWidget(self._path_input)

        browse_btn = QPushButton('…')
        browse_btn.setObjectName('ghost')
        browse_btn.setFixedWidth(34)
        browse_btn.setToolTip('Browse')
        browse_btn.clicked.connect(self._browse)
        path_row.addWidget(browse_btn)
        root.addLayout(path_row)

        # Buttons row
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        btn_row.addStretch()

        self._cancel_btn = QPushButton('Cancel')
        self._cancel_btn.setObjectName('ghost')
        self._cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(self._cancel_btn)

        self._start_btn = QPushButton('  Download  ▶  ')
        self._start_btn.setObjectName('primary')
        self._start_btn.setEnabled(False)
        self._start_btn.clicked.connect(self._on_start)
        btn_row.addWidget(self._start_btn)
        root.addLayout(btn_row)

    # ── Metadata fetch ─────────────────────────────────────────────────

    def _fetch_metadata(self):
        # Show the display name from dn= immediately so the user sees
        # something meaningful while DHT/trackers are contacted.
        dn = self._display_name_from_magnet(self._magnet_uri)
        if dn:
            self._spinner.set_message(f'Fetching file list for "{dn}"…')
            self.setWindowTitle(f'Magnet Fisher — {dn}')

        self._worker = self._session.fetch_metadata(self._magnet_uri)
        self._worker.ready.connect(self._on_metadata)
        self._worker.failed.connect(self._on_error)
        self._worker.start()

    @staticmethod
    def _display_name_from_magnet(uri: str) -> str:
        """Extract and decode the dn= display-name from a magnet URI, or ''."""
        try:
            qs = urllib.parse.urlparse(uri).query
            dn = urllib.parse.parse_qs(qs).get('dn', [''])[0]
            return urllib.parse.unquote_plus(dn).replace('.', ' ').strip()
        except Exception:
            return ''

    def _on_metadata(self, meta: dict, magnet_uri: str):
        self._worker = None  # fetch is done; nothing to cancel

        name      = meta.get('name', 'Unknown')
        total     = meta.get('size', 0)
        files     = meta.get('files', [])
        num_files = len(files)

        self._torrent_name = name
        self._name_lbl.setText(name)
        self.setWindowTitle(f'Magnet Fisher — {name}')

        plural = 's' if num_files != 1 else ''
        self._meta_lbl.setText(
            f'{format_size(total)}   •   {num_files} file{plural}'
        )

        self._populate_tree(files)
        self._spinner.stop()
        self._stack.setCurrentIndex(1)
        self._start_btn.setEnabled(True)
        self.adjustSize()

    def _on_error(self, msg: str):
        self._worker = None
        self._spinner.setText(f'⚠   {msg}')   # stops animation, shows error

    # ── File tree ──────────────────────────────────────────────────────

    def _populate_tree(self, files: list):
        """Build a nested tree from a flat list of {"path": str, "size": int} dicts."""
        root_node: dict = {}
        for f in files:
            parts = [p for p in f['path'].split('/') if p]
            if not parts:
                continue
            node = root_node
            for part in parts[:-1]:
                node = node.setdefault(part, {})
            node[parts[-1]] = f['size']

        _fill_tree_widget(self._tree, root_node)
        self._tree.expandAll()

    # ── Actions ────────────────────────────────────────────────────────

    def _browse(self):
        path = QFileDialog.getExistingDirectory(
            self, 'Choose download folder', self._path_input.text()
        )
        if path:
            self._path_input.setText(path)

    def _on_start(self):
        save_path = self._path_input.text().strip()
        if not save_path:
            return

        os.makedirs(save_path, exist_ok=True)

        s = load_settings()
        s['save_path'] = save_path
        save_settings(s)

        self.download_requested.emit(self._magnet_uri, save_path, self._torrent_name)
        self.accept()

    # ── Cleanup ────────────────────────────────────────────────────────

    def closeEvent(self, event):
        # Cancel any in-progress metadata fetch so the subprocess doesn't
        # keep working for a dialog the user already dismissed.
        if self._worker is not None:
            self._worker.cancel()
            self._worker = None
        super().closeEvent(event)


# ── Helpers ────────────────────────────────────────────────────────────

def _fill_tree_widget(parent, node: dict):
    muted = QColor('#888888')
    dirs  = sorted((k, v) for k, v in node.items() if isinstance(v, dict))
    files = sorted((k, v) for k, v in node.items() if isinstance(v, int))

    for name, children in dirs:
        item = QTreeWidgetItem(parent)
        item.setText(0, f'   📁   {name}')
        item.setText(1, format_size(_tree_size(children)))
        item.setForeground(1, muted)
        _fill_tree_widget(item, children)

    for name, size in files:
        item = QTreeWidgetItem(parent)
        item.setText(0, f'   📄   {name}')
        item.setText(1, format_size(size))
        item.setForeground(1, muted)


def _tree_size(node: dict) -> int:
    total = 0
    for v in node.values():
        total += _tree_size(v) if isinstance(v, dict) else v
    return total

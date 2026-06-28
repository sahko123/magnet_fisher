import threading

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView,
)
from PyQt6.QtCore import Qt, QObject, pyqtSignal

from utils import jackett
from utils.format import format_size
from core import settings as app_settings


class _NumericItem(QTableWidgetItem):
    """QTableWidgetItem that sorts by a numeric UserRole value."""
    def __lt__(self, other: QTableWidgetItem) -> bool:
        try:
            return (self.data(Qt.ItemDataRole.UserRole) or 0) < (other.data(Qt.ItemDataRole.UserRole) or 0)
        except TypeError:
            return super().__lt__(other)


class _Relay(QObject):
    results = pyqtSignal(list)
    error   = pyqtSignal(str)


class SearchWindow(QWidget):
    def __init__(self, open_preview, parent=None):
        super().__init__(parent)
        self._open_preview = open_preview
        self._relay = _Relay()
        self._relay.results.connect(self._on_results)
        self._relay.error.connect(self._on_error)
        self._settings = app_settings.load()

        self.setWindowTitle('Search — Magnet Fisher')
        self.setMinimumSize(820, 500)
        self.resize(980, 620)
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        # ── Jackett config ─────────────────────────────────────────────
        cfg = QHBoxLayout()
        cfg.setSpacing(8)
        cfg.addWidget(QLabel('Jackett URL'))

        self._url_input = QLineEdit()
        self._url_input.setPlaceholderText('http://localhost:9117')
        self._url_input.setText(self._settings.get('jackett_url', ''))
        self._url_input.setFixedWidth(220)
        cfg.addWidget(self._url_input)

        cfg.addWidget(QLabel('API Key'))

        self._key_input = QLineEdit()
        self._key_input.setPlaceholderText('your api key')
        self._key_input.setText(self._settings.get('jackett_api_key', ''))
        self._key_input.setFixedWidth(280)
        cfg.addWidget(self._key_input)
        cfg.addStretch()
        root.addLayout(cfg)

        # ── Search bar ─────────────────────────────────────────────────
        bar = QHBoxLayout()
        bar.setSpacing(8)

        self._query = QLineEdit()
        self._query.setPlaceholderText('Search torrents…')
        self._query.returnPressed.connect(self._do_search)
        bar.addWidget(self._query)

        self._btn = QPushButton('Search')
        self._btn.setObjectName('primary')
        self._btn.setFixedWidth(90)
        self._btn.clicked.connect(self._do_search)
        bar.addWidget(self._btn)
        root.addLayout(bar)

        # ── Results table ──────────────────────────────────────────────
        self._table = QTableWidget(0, 6)
        self._table.setHorizontalHeaderLabels(['Name', 'Size', 'Seeds', 'Leechers', 'Indexer', ''])
        hdr = self._table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for col in (1, 2, 3, 4, 5):
            hdr.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setAlternatingRowColors(True)
        self._table.setSortingEnabled(True)
        self._table.horizontalHeader().setSortIndicator(2, Qt.SortOrder.DescendingOrder)
        root.addWidget(self._table)

        # ── Status ─────────────────────────────────────────────────────
        self._status = QLabel('')
        self._status.setObjectName('muted')
        root.addWidget(self._status)

    # ── Search ─────────────────────────────────────────────────────────

    def _do_search(self):
        url   = self._url_input.text().strip()
        key   = self._key_input.text().strip()
        query = self._query.text().strip()

        if not url or not key:
            self._status.setText('Enter Jackett URL and API key above.')
            return
        if not query:
            return

        self._settings['jackett_url']     = url
        self._settings['jackett_api_key'] = key
        app_settings.save(self._settings)

        self._table.setRowCount(0)
        self._btn.setEnabled(False)
        self._status.setText('Searching…')

        relay = self._relay
        def _run():
            try:
                relay.results.emit(jackett.search(url, key, query))
            except Exception as exc:
                relay.error.emit(str(exc))

        threading.Thread(target=_run, daemon=True).start()

    def _on_results(self, results: list):
        self._btn.setEnabled(True)
        self._table.setSortingEnabled(False)
        self._table.setRowCount(len(results))

        for row, r in enumerate(results):
            name_item = QTableWidgetItem(r['title'])
            name_item.setToolTip(r['title'])
            self._table.setItem(row, 0, name_item)

            size_item = _NumericItem(format_size(r['size']))
            size_item.setData(Qt.ItemDataRole.UserRole, r['size'])
            size_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self._table.setItem(row, 1, size_item)

            seeds_item = _NumericItem(str(r['seeders']))
            seeds_item.setData(Qt.ItemDataRole.UserRole, r['seeders'])
            seeds_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self._table.setItem(row, 2, seeds_item)

            leech_item = _NumericItem(str(r['leechers']))
            leech_item.setData(Qt.ItemDataRole.UserRole, r['leechers'])
            leech_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self._table.setItem(row, 3, leech_item)

            self._table.setItem(row, 4, QTableWidgetItem(r['indexer']))

            magnet = r['magnet']
            btn = QPushButton('Download')
            btn.setObjectName('ghost')
            btn.clicked.connect(lambda _checked, m=magnet: self._open_preview(m))
            self._table.setCellWidget(row, 5, btn)

        self._table.setSortingEnabled(True)
        n = len(results)
        self._status.setText(f'Found {n} result{"s" if n != 1 else ""}.')

    def _on_error(self, msg: str):
        self._btn.setEnabled(True)
        self._status.setText(f'Error: {msg}')

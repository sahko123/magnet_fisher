"""
Main download window — shows active download cards.
Lives in the system tray; left-click tray icon toggles visibility.
Closing the window (X) quits the application cleanly.
Right-click tray icon → Show / Quit.
"""
import os
import sys

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QProgressBar, QFrame, QScrollArea,
    QSystemTrayIcon, QMenu, QSizePolicy,
)
from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QFont, QIcon, QPixmap, QPainter, QColor, QPen

from core.session import TorrentSession
from utils.format import format_rate, format_size


# ── Stat card ──────────────────────────────────────────────────────────

class StatCard(QFrame):
    def __init__(self, label: str, parent=None):
        super().__init__(parent)
        self.setObjectName('stat-card')
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(2)

        self._val = QLabel('—')
        self._val.setObjectName('stat-value')
        f = QFont()
        f.setFamily('Cascadia Code')
        f.setPointSize(13)
        self._val.setFont(f)
        layout.addWidget(self._val)

        lbl = QLabel(label)
        lbl.setObjectName('stat-label')
        layout.addWidget(lbl)

    def set_value(self, text: str):
        self._val.setText(text)


# ── Download card ──────────────────────────────────────────────────────

class DownloadCard(QFrame):
    """One card per active download."""
    removed = pyqtSignal()  # emitted just before the card destroys itself

    def __init__(
        self,
        name: str,
        magnet_uri: str,
        session: TorrentSession,
        save_path: str,
        parent=None,
    ):
        super().__init__(parent)
        self.setObjectName('card')
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self._magnet_uri = magnet_uri
        self._session    = session
        self._save_path  = save_path
        self._worker     = None
        self._paused     = False

        self._build_ui(name)
        self._begin_download()

    def _build_ui(self, name: str):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)

        # Torrent name
        self._name_lbl = QLabel(name)
        self._name_lbl.setObjectName('subheading')
        f = self._name_lbl.font()
        f.setPointSize(11)
        f.setWeight(QFont.Weight.DemiBold)
        self._name_lbl.setFont(f)
        self._name_lbl.setWordWrap(True)
        layout.addWidget(self._name_lbl)

        # Progress bar + percentage label
        prog_row = QHBoxLayout()
        prog_row.setSpacing(10)

        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setTextVisible(False)
        prog_row.addWidget(self._progress)

        self._pct_lbl = QLabel('0%')
        self._pct_lbl.setObjectName('muted')
        self._pct_lbl.setFixedWidth(40)
        self._pct_lbl.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        prog_row.addWidget(self._pct_lbl)
        layout.addLayout(prog_row)

        # Stat tiles: down / write / up / seeds / peers
        stats_row = QHBoxLayout()
        stats_row.setSpacing(8)
        self._down_card  = StatCard('Download')
        self._write_card = StatCard('Write')
        self._up_card    = StatCard('Upload')
        self._seeds_card = StatCard('Seeds')
        self._peers_card = StatCard('Peers')
        for card in (self._down_card, self._write_card, self._up_card,
                     self._seeds_card, self._peers_card):
            stats_row.addWidget(card)
        layout.addLayout(stats_row)

        # One-line status string
        self._status_lbl = QLabel('Connecting…')
        self._status_lbl.setObjectName('status-text')
        layout.addWidget(self._status_lbl)

        # Divider
        div = QFrame()
        div.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(div)

        # Action buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self._pause_btn = QPushButton('⏸   Pause')
        self._pause_btn.setObjectName('ghost')
        self._pause_btn.clicked.connect(self._toggle_pause)
        btn_row.addWidget(self._pause_btn)

        self._remove_btn = QPushButton('✕   Remove')
        self._remove_btn.setObjectName('danger')
        self._remove_btn.clicked.connect(self._remove)
        btn_row.addWidget(self._remove_btn)

        self._folder_btn = QPushButton('📁   Open Folder')
        self._folder_btn.setObjectName('ghost')
        self._folder_btn.clicked.connect(self._open_folder)
        btn_row.addWidget(self._folder_btn)

        btn_row.addStretch()
        layout.addLayout(btn_row)

    # ── Download control ───────────────────────────────────────────────

    def _begin_download(self):
        self._worker = self._session.start_download(self._magnet_uri, self._save_path)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.errored.connect(self._on_error)
        self._worker.start()

    @pyqtSlot(dict)
    def _on_progress(self, stats: dict):
        pct = stats.get('progress', 0.0)
        self._progress.setValue(round(pct))
        self._pct_lbl.setText(f'{pct:.1f}%')

        self._down_card.set_value(format_rate(stats.get('down_rate', 0)))
        self._write_card.set_value(format_rate(stats.get('write_rate', 0)))
        self._up_card.set_value(format_rate(stats.get('up_rate', 0)))
        self._seeds_card.set_value(str(stats.get('seeds', 0)))
        self._peers_card.set_value(str(stats.get('peers', 0)))

        state    = stats.get('state', '')
        eta      = stats.get('eta', '—')
        done     = stats.get('downloaded', 0)
        total    = stats.get('total', 0)
        seeds    = stats.get('seeds', 0)
        peers    = stats.get('peers', 0)
        pct_val  = stats.get('progress', 0.0)

        parts = []
        if state == 'Fetching metadata':
            if seeds + peers == 0:
                parts.append('Fetching metadata — searching for peers…')
            else:
                parts.append(f'Fetching metadata — {seeds} seed{"s" if seeds != 1 else ""}, {peers} peer{"s" if peers != 1 else ""}')
        elif state == 'Checking files':
            parts.append(f'Checking files — {pct_val:.1f}%')
        elif state:
            parts.append(state)

        if total > 0:
            parts.append(f'{format_size(done)} / {format_size(total)}')
        if eta != '—':
            parts.append(f'ETA {eta}')
        self._status_lbl.setText('   •   '.join(parts) if parts else '')

    @pyqtSlot()
    def _on_finished(self):
        self._worker = None
        self._progress.setValue(100)
        self._pct_lbl.setText('100%')
        self._status_lbl.setText('Complete ✓')
        self._pause_btn.setEnabled(False)
        self._down_card.set_value('—')

    @pyqtSlot(str)
    def _on_error(self, msg: str):
        self._worker = None
        self._status_lbl.setText(f'Error: {msg}')

    def _toggle_pause(self):
        if self._worker is None:
            return
        if self._paused:
            self._worker.resume()
            self._pause_btn.setText('⏸   Pause')
        else:
            self._worker.pause()
            self._pause_btn.setText('▶   Resume')
        self._paused = not self._paused

    def _remove(self):
        if self._worker is not None:
            self._worker.stop()
            self._worker = None
        self.removed.emit()
        self.deleteLater()

    def _open_folder(self):
        if os.path.isdir(self._save_path):
            os.startfile(self._save_path)


# ── Main window ────────────────────────────────────────────────────────

class DownloadWindow(QMainWindow):
    def __init__(self, session: TorrentSession):
        super().__init__()
        self._session    = session
        self._icon       = _make_icon()
        self._card_count = 0

        self.setWindowTitle('Magnet Fisher')
        self.setWindowIcon(self._icon)
        self.setMinimumSize(580, 240)
        self.resize(660, 500)

        self._build_ui()
        self._setup_tray()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        root.addWidget(scroll)

        self._cards_widget = QWidget()
        self._cards_layout = QVBoxLayout(self._cards_widget)
        self._cards_layout.setContentsMargins(16, 16, 16, 16)
        self._cards_layout.setSpacing(12)

        self._empty_lbl = QLabel(
            'No active downloads.\n\nClick a magnet link to get started.'
        )
        self._empty_lbl.setObjectName('muted')
        self._empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_lbl.setMinimumHeight(160)
        self._cards_layout.addWidget(self._empty_lbl)
        self._cards_layout.addStretch()   # pushes cards to the top

        scroll.setWidget(self._cards_widget)

    def _setup_tray(self):
        self._tray = QSystemTrayIcon(self._icon, self)
        self._tray.setToolTip('Magnet Fisher')

        menu = QMenu()
        menu.addAction('Show', self.show_window)
        menu.addSeparator()
        menu.addAction('Quit', self._quit)
        self._tray.setContextMenu(menu)
        self._tray.activated.connect(self._on_tray_click)
        self._tray.show()

    # ── Public API ─────────────────────────────────────────────────────

    def add_download(self, name: str, magnet_uri: str, save_path: str):
        if self._empty_lbl.isVisible():
            self._empty_lbl.hide()
        self._card_count += 1

        card = DownloadCard(name or 'Unknown torrent', magnet_uri, self._session, save_path)
        card.removed.connect(self._on_card_removed)
        # Insert before the trailing stretch (last item in layout)
        self._cards_layout.insertWidget(self._cards_layout.count() - 1, card)
        self.show_window()

    def show_window(self):
        self.show()
        self.raise_()
        self.activateWindow()

    # ── Slots ──────────────────────────────────────────────────────────

    def _on_card_removed(self):
        self._card_count -= 1
        if self._card_count <= 0:
            self._card_count = 0
            self._empty_lbl.show()

    def _on_tray_click(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            if self.isVisible():
                self.hide()
            else:
                self.show_window()

    def closeEvent(self, event):
        event.accept()
        self._quit()

    def _quit(self):
        self._tray.hide()
        self._session.shutdown()
        sys.exit(0)


# ── Icon ───────────────────────────────────────────────────────────────

def _make_icon(size: int = 48) -> QIcon:
    px = QPixmap(size, size)
    px.fill(Qt.GlobalColor.transparent)
    p = QPainter(px)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setBrush(QColor('#2a2a2a'))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawEllipse(0, 0, size, size)
    p.setPen(QPen(QColor('#a8c8e8')))
    f = QFont('Segoe UI', int(size * 0.42), QFont.Weight.Bold)
    p.setFont(f)
    p.drawText(px.rect(), Qt.AlignmentFlag.AlignCenter, 'M')
    p.end()
    return QIcon(px)

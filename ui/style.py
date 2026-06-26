"""
Global QSS stylesheet — soft paper light-mode aesthetic.
Colour palette derived from HouseholdMD light theme.
"""

QSS = """
/* ─────────────────────────────────────────────────────
   Global
───────────────────────────────────────────────────── */
QWidget {
    background-color: #f5f5f5;
    color: #2a2a2a;
    font-family: "Segoe UI", -apple-system, BlinkMacSystemFont, sans-serif;
    font-size: 13px;
    selection-background-color: #a8c8e8;
    selection-color: #1a1a1a;
}

/* ─────────────────────────────────────────────────────
   Labels
───────────────────────────────────────────────────── */
QLabel#heading {
    font-size: 15px;
    font-weight: 600;
    color: #1a1a1a;
}

QLabel#subheading {
    font-size: 13px;
    font-weight: 600;
    color: #1a1a1a;
}

QLabel#muted {
    color: #888888;
    font-size: 12px;
}

QLabel#stat-value {
    font-family: "Cascadia Code", "Fira Code", "JetBrains Mono", "Consolas", monospace;
    font-size: 14px;
    font-weight: 500;
    color: #1a1a1a;
}

QLabel#stat-label {
    color: #888888;
    font-size: 11px;
    font-family: "Segoe UI", sans-serif;
}

QLabel#status-text {
    color: #888888;
    font-size: 12px;
}

/* ─────────────────────────────────────────────────────
   Buttons
───────────────────────────────────────────────────── */
QPushButton {
    border-radius: 4px;
    padding: 5px 14px;
    font-size: 13px;
    font-family: "Segoe UI", sans-serif;
    min-height: 28px;
}

/* Primary — dark fill */
QPushButton#primary {
    background-color: #2a2a2a;
    color: #f5f5f5;
    border: none;
    font-weight: 500;
}
QPushButton#primary:hover   { background-color: #1a1a1a; }
QPushButton#primary:pressed { background-color: #111111; }
QPushButton#primary:disabled {
    background-color: #d8d8d8;
    color: #aaaaaa;
}

/* Ghost — transparent with border */
QPushButton#ghost {
    background-color: transparent;
    color: #2a2a2a;
    border: 1px solid #d0d0d0;
}
QPushButton#ghost:hover    { background-color: #eaeaea; border-color: #b8b8b8; }
QPushButton#ghost:pressed  { background-color: #d8d8d8; }
QPushButton#ghost:disabled { color: #aaaaaa; border-color: #e0e0e0; }

/* Danger — ghost until hover */
QPushButton#danger {
    background-color: transparent;
    color: #2a2a2a;
    border: 1px solid #d0d0d0;
}
QPushButton#danger:hover {
    background-color: #c42b1c;
    color: #ffffff;
    border-color: #c42b1c;
}
QPushButton#danger:pressed {
    background-color: #a02318;
    border-color: #a02318;
    color: #ffffff;
}

/* ─────────────────────────────────────────────────────
   Progress Bar
───────────────────────────────────────────────────── */
QProgressBar {
    background-color: #e8e8e8;
    border: none;
    border-radius: 3px;
    min-height: 7px;
    max-height: 7px;
    text-align: center;
}
QProgressBar::chunk {
    background-color: #a8c8e8;
    border-radius: 3px;
}

/* ─────────────────────────────────────────────────────
   Inputs
───────────────────────────────────────────────────── */
QLineEdit {
    background-color: #eaeaea;
    border: 1px solid #d0d0d0;
    border-radius: 4px;
    padding: 4px 8px;
    color: #2a2a2a;
    font-size: 13px;
    min-height: 28px;
}
QLineEdit:focus   { border-color: #a8c8e8; }
QLineEdit:disabled { color: #aaaaaa; background-color: #f0f0f0; }

/* ─────────────────────────────────────────────────────
   Tree Widget (file preview)
───────────────────────────────────────────────────── */
QTreeWidget {
    background-color: #eaeaea;
    border: 1px solid #d0d0d0;
    border-radius: 4px;
    padding: 2px;
    outline: none;
    alternate-background-color: #e4e4e4;
}
QTreeWidget::item {
    padding: 3px 4px;
    border-radius: 3px;
}
QTreeWidget::item:hover    { background-color: #d8d8d8; }
QTreeWidget::item:selected { background-color: #a8c8e8; color: #1a1a1a; }
QTreeWidget::branch        { background: transparent; }
QHeaderView::section {
    background-color: #e2e2e2;
    border: none;
    border-bottom: 1px solid #d0d0d0;
    padding: 4px 8px;
    font-size: 11px;
    color: #888888;
    font-weight: normal;
}

/* ─────────────────────────────────────────────────────
   Scroll Bars
───────────────────────────────────────────────────── */
QScrollBar:vertical {
    background: transparent;
    width: 8px;
    margin: 0;
    border: none;
}
QScrollBar::handle:vertical {
    background: #d0d0d0;
    border-radius: 4px;
    min-height: 24px;
}
QScrollBar::handle:vertical:hover { background: #a8c8e8; }
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical  { height: 0; }
QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical  { background: none; }

QScrollBar:horizontal {
    background: transparent;
    height: 8px;
    margin: 0;
    border: none;
}
QScrollBar::handle:horizontal {
    background: #d0d0d0;
    border-radius: 4px;
    min-width: 24px;
}
QScrollBar::handle:horizontal:hover { background: #a8c8e8; }
QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal { width: 0; }

/* ─────────────────────────────────────────────────────
   Scroll Area
───────────────────────────────────────────────────── */
QScrollArea {
    border: none;
    background: transparent;
}

/* ─────────────────────────────────────────────────────
   Cards / Frames
───────────────────────────────────────────────────── */
QFrame#card {
    background-color: #ffffff;
    border: 1px solid #d8d8d8;
    border-radius: 6px;
}

QFrame#stat-card {
    background-color: #eaeaea;
    border-radius: 4px;
}

/* ─────────────────────────────────────────────────────
   Dividers (HLine / VLine frames)
───────────────────────────────────────────────────── */
QFrame[frameShape="4"],
QFrame[frameShape="5"] {
    color: #d0d0d0;
    border: none;
    max-height: 1px;
    background-color: #d0d0d0;
}

/* ─────────────────────────────────────────────────────
   Tooltips
───────────────────────────────────────────────────── */
QToolTip {
    background-color: #2a2a2a;
    color: #f5f5f5;
    border: none;
    padding: 4px 8px;
    border-radius: 3px;
    font-size: 12px;
}

/* ─────────────────────────────────────────────────────
   Menu (tray context menu)
───────────────────────────────────────────────────── */
QMenu {
    background-color: #f5f5f5;
    border: 1px solid #d0d0d0;
    border-radius: 4px;
    padding: 4px 0;
}
QMenu::item {
    padding: 5px 20px 5px 12px;
}
QMenu::item:selected {
    background-color: #eaeaea;
    color: #1a1a1a;
}
QMenu::separator {
    height: 1px;
    background: #d0d0d0;
    margin: 3px 8px;
}
"""

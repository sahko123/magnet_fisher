"""
Shared reusable widgets.
"""
from PyQt6.QtWidgets import QLabel
from PyQt6.QtCore import Qt, QTimer


class Spinner(QLabel):
    """
    Animated braille spinner for 'loading' states.
    Inherits QLabel so font/alignment etc. work normally.
    Call setText() to replace the animation with a static message (e.g. errors).
    """
    _FRAMES = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']

    def __init__(self, text: str = 'Loading…', parent=None):
        super().__init__(parent)
        self._msg   = text
        self._frame = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setObjectName('muted')
        font = self.font()
        font.setPointSize(13)
        self.setFont(font)
        self.start()

    def start(self):
        self._timer.start(80)
        self._tick()

    def stop(self):
        self._timer.stop()

    def set_message(self, text: str):
        """Update the spinning message without stopping the animation."""
        self._msg = text

    def setText(self, text: str):
        """Stop the animation and show a static message (e.g. an error)."""
        self.stop()
        super().setText(text)

    def _tick(self):
        frame = self._FRAMES[self._frame % len(self._FRAMES)]
        super().setText(f'{frame}   {self._msg}')
        self._frame = (self._frame + 1) % len(self._FRAMES)

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QLabel


class DropLabel(QLabel):
    fileDropped = Signal(str)

    def __init__(self) -> None:
        super().__init__(
            "여기에 동영상 파일을 드래그하세요\n또는 [파일 선택] 버튼을 사용하세요."
        )
        self.setObjectName("dropZone")
        self.setMinimumHeight(120)
        self.setAcceptDrops(True)
        self.setAlignment(Qt.AlignCenter)  # type: ignore[name-defined]
        self.setWordWrap(True)

    def dragEnterEvent(self, event) -> None:  # noqa: N802
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event) -> None:  # noqa: N802
        urls = event.mimeData().urls()
        if not urls:
            return
        local_path = urls[0].toLocalFile()
        if local_path:
            self.fileDropped.emit(local_path)

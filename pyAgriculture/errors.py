from PySide2.QtWidgets import QMessageBox


class MsgError:
    def __init__(self, text):
        box = QMessageBox(text=text)
        box.exec_()

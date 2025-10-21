from operator import xor
import re
import os
import sys
import xml.etree.ElementTree as ET

from PySide6.QtWidgets import (QMainWindow, QWidget, QLabel, QGridLayout, QListWidget, QListWidgetItem, QSpacerItem,
                               QFileDialog, QPushButton, QComboBox, QSizePolicy, QAbstractItemView, QApplication,
                               QMessageBox, QVBoxLayout, QHBoxLayout, QLineEdit, QFrame)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from pyAgriculture.errors import MsgError
THIS_DIR = os.path.dirname(__file__)


class MetaData(QMainWindow):
    def __init__(self, parent=None, meta_data_type: str = 'Farm', schema: dict = None):
        super(MetaData, self).__init__(parent)
        self.main_layout = QGridLayout()
        self.available_items_table_widget = QListWidget()
        self.current_sub_element = ET.Element('')
        self.update_item_name = False
        self.meta_data_type = meta_data_type
        self.schema = schema
        self.edit_item_push_button = QPushButton(self, text='Edit ->')
        self.edit_item_push_button.clicked.connect(self.edit_item)
        self.update_item_push_button = QPushButton(self, text='Update <-')
        self.update_item_push_button.clicked.connect(self.update_item)
        self.update_item_push_button.setEnabled(False)
        self.save_item_push_button = QPushButton(self, text='Save as new<-')
        self.save_item_push_button.clicked.connect(self.save_item)
        self.delete_item_push_button = QPushButton(self, text='Remove item')
        self.delete_item_push_button.clicked.connect(self.remove_item)
        self.type_widgets_layout = QVBoxLayout()
        self.type_widgets = QFrame(self)
        self.type_widgets.setLayout(self.type_widgets_layout)
        self.main_layout.addWidget(self.available_items_table_widget, 1, 0, 7, 1)
        self.main_layout.addWidget(self.edit_item_push_button, 2, 1, 1, 1)
        self.main_layout.addWidget(self.update_item_push_button, 3, 1, 1, 1)
        self.main_layout.addWidget(self.save_item_push_button, 4, 1, 1, 1)
        self.main_layout.addWidget(self.delete_item_push_button, 5, 1, 1, 1)
        self.main_layout.addWidget(self.type_widgets, 1, 2, 7, 1)
        self.set_type_items()
        if meta_data_type == 'Farm':
            self.tree_root = ET.parse(f'{THIS_DIR}\\..\\meta_data\\FRMs.xml').getroot()
            self.file_name = f'{THIS_DIR}\\..\\meta_data\\FRMs.xml'
        elif meta_data_type == 'Customer':
            self.tree_root = ET.parse(f'{THIS_DIR}\\..\\meta_data\\CTRs.xml').getroot()
            self.file_name = f'{THIS_DIR}\\..\\meta_data\\CTRs.xml'
        elif meta_data_type == 'Worker':
            self.tree_root = ET.parse(f'{THIS_DIR}\\..\\meta_data\\WRKs.xml').getroot()
            self.file_name = f'{THIS_DIR}\\..\\meta_data\\WRKs.xml'
        elif meta_data_type == 'Device':
            self.tree_root = ET.parse(f'{THIS_DIR}\\..\\meta_data\\DVCs.xml').getroot()
            self.file_name = f'{THIS_DIR}\\..\\meta_data\\DVCs.xml'
        else:
            MsgError('Unknown static data')
        self.fill_existing_table()
        self.central_widget = QWidget(self)
        self.fill_existing_table()
        self.central_widget.setLayout(self.main_layout)
        self.central_widget.adjustSize()

        self.setCentralWidget(self.central_widget)

        self.setGeometry(100, 100, 800, 800)
        self.setWindowTitle(f"PyAgriculture - Edit {meta_data_type}")

    def fill_existing_table(self):
        self.available_items_table_widget.clear()
        for child in self.tree_root:
            name = f'{child.tag} - {child.attrib["B"]}'
            item1 = QListWidgetItem(name)
            self.available_items_table_widget.addItem(item1)

    def remove_item(self):
        """Removes the selected schemas from the table: included_schemas_list"""
        if self.available_items_table_widget.selectedItems() is None:
            return
        for item in self.available_items_table_widget.selectedItems():
            xml_item = self.tree_root.findall(item.text().split(' - ')[0])
            self.tree_root.remove(xml_item[0])
            self.available_items_table_widget.removeItemWidget(item)
        self.save_tree()
        self.fill_existing_table()

    def edit_item(self):
        for item in self.available_items_table_widget.selectedItems():
            xml_item = self.tree_root.findall(item.text().split(' - ')[0])[0]
            for i in range(self.type_widgets_layout.count()):
                if type(self.type_widgets_layout.itemAt(i).widget()) == QFrame:
                    lay = self.type_widgets_layout.itemAt(i).widget().layout()
                    widget = lay.itemAt(1).widget()
                    if type(widget) == QLineEdit:
                        widget.setText(xml_item.attrib[widget.attr])
            self.update_item_push_button.setEnabled(True)
            self.current_sub_element = xml_item

    def clear_widgets(self):
        for i in range(self.type_widgets_layout.count()):
            row_lay = self.type_widgets_layout.itemAt(i).widget().layout()
            widget = row_lay.itemAt(1).widget()
            try:
                widget.clear()
            except:
                pass

    def set_type_items(self):
        for key, item in self.schema.items():
            if 'name' in key.lower() or 'includes' in key.lower():
                continue
            label = QLabel(self, text=f"{item['Attribute_name']}: ")
            if 'string' in item['Type']:
                widget = QLineEdit(self)
            elif 'xs:IDREF' in item['Type']:
                widget = self.get_ctr_widgets()
            else:
                widget = QLabel(self, text=item['Type'])
            widget.__setattr__('attr', key)
            lay = QHBoxLayout()
            lay.addWidget(label)
            lay.addWidget(widget)
            frame = QFrame()
            frame.setLayout(lay)
            self.type_widgets_layout.addWidget(frame)

    def get_ctr_widgets(self, schema: str = 'CTR') -> QComboBox:
        root = ET.parse(f'{THIS_DIR}\\..\\meta_data\\{schema}s.xml').getroot()
        widget = QComboBox(self)
        items = []
        for child in root:
            items.append(f'{child.tag} - {child.attrib["B"]}')
        widget.addItems(items)
        return widget

    def update_item(self):
        self.update_item_name = True
        self.save_item()
        self.update_item_push_button.setEnabled(False)
        self.current_sub_element = None
        self.update_item_name = False

    def get_xml_sub_schema(self) -> ET.SubElement:
        if self.current_sub_element is not None and self.update_item_name:
            return self.current_sub_element
        schema = self.tree_root.attrib['schema']
        max_number = 0
        for item in self.tree_root.iter("*"):
            try:
                number = int(item.tag.strip(schema))
                if number > max_number:
                    max_number = number
            except ValueError:
                pass
        name = schema + str(max_number + 1)
        sub = ET.SubElement(self.tree_root, name)
        return sub

    def save_item(self):
        sub = self.get_xml_sub_schema()
        for i in range(self.type_widgets_layout.count()):
            if type(self.type_widgets_layout.itemAt(i).widget()) == QFrame:
                lay = self.type_widgets_layout.itemAt(i).widget().layout()
                widget = lay.itemAt(1).widget()
                key = widget.attr
                if type(widget) == QLineEdit:
                    value = widget.text()
                elif type(widget) == QComboBox:
                    value = widget.currentText().split(' - ')[0]
                else:
                    value = ''
                sub.set(key, value)
        self.save_tree()
        self.fill_existing_table()

    def save_tree(self):
        ET.indent(self.tree_root, space='    ', level=0)
        with open(self.file_name, 'wb') as f:
            string = ET.tostring(self.tree_root, encoding='unicode')
            f.write(string.encode('utf-8'))
        self.clear_widgets()

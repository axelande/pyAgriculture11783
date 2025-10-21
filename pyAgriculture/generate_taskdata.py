import ast
import json
import os
import sys
import struct
import xml.etree.ElementTree as ET

import geopandas as gpd
import geopy
import geopy.distance
from PySide6.QtWidgets import (QLabel, QMainWindow, QPushButton, QVBoxLayout, QWidget, QApplication, QComboBox,
                               QLineEdit, QHBoxLayout, QCheckBox, QFrame, QMenu, QScrollArea, QFileDialog, QGridLayout,
                               QDoubleSpinBox, QSpinBox, QMessageBox)
from PySide6.QtCore import Qt
from PySide6 import QtGui

from pyAgriculture.create_recpie import CreateRecipe
from pyAgriculture.meta_data_widgets import MetaData
from pyAgriculture.sorting_utils import etree_to_dict
from pyAgriculture.errors import MsgError
__version__ = 0.1


def distance(p1, p2):
    x = p1.y, p1.x
    y = p2.y, p2.x
    return geopy.distance.geodesic(x, y).m


class GenerateTaskData(QMainWindow):
    def __init__(self):
        super(GenerateTaskData, self).__init__()
        # TODO: Add content to the Meta data tab
        self.schemas = {}
        self.load_schemas()
        self.added_rows = {}
        self.id_list = {}
        self.idref_widgets = {}
        self.save_temp = {}
        self.frame_stack = {}
        self._create_menu_bar()
        intro_text = QLabel(self, text='Welcome to GeoDataFarms Taskdata file generator')

        self.file_version_input = 2.1
        self.software_version = __version__
        self.software_manufacture = 'GeoDataFarm'
        self.data_transfer_origin = 1

        self.run_create_file = QPushButton('Create file')
        self.run_create_file.clicked.connect(self.store_data)

        self.middle_layout = QVBoxLayout()
        self.middle_frame = QFrame()
        self.middle_frame.setMaximumHeight(800)
        self.middle_frame.setLayout(self.middle_layout)
        # set the layout
        layout = QVBoxLayout()
        layout.addWidget(intro_text)
        layout.addWidget(self.middle_frame)
        layout.addWidget(self.run_create_file)


        # setup the central widget
        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget)
        self.central_widget.setLayout(layout)

        self.setGeometry(100, 50, 1000, 950)
        self.setWindowTitle("PyAgriculture - Create ISOXML")

    def _create_menu_bar(self):
        """Creates the menubar and connects the different buttons to the correct function."""
        menu_bar = self.menuBar()
        # File menu
        file_menu = QMenu("&File", self)
        menu_bar.addMenu(file_menu)

        new_action = file_menu.addAction("Create a new recipe")
        open_action = file_menu.addAction("Load a recipe")
        self.save_action = file_menu.addAction("Save current recipe")
        self.exit_action = file_menu.addAction("Exit")
        new_action.triggered.connect(self.create_new_recipe)
        open_action.triggered.connect(self.load_recipe)

        # Meta menu
        meta_menu = QMenu("&Meta data", self)
        menu_bar.addMenu(meta_menu)
        customer = meta_menu.addAction('Customer')
        customer.triggered.connect(self.create_customer)
        farms = meta_menu.addAction('Farms')
        farms.triggered.connect(self.create_farm)
        workers = meta_menu.addAction('Workers')
        workers.triggered.connect(self.create_worker)
        devices = meta_menu.addAction('Devices')
        devices.triggered.connect(self.create_device)

    def create_new_recipe(self):
        """Calls the class CreateRecipe and shows its widget"""
        create_recipe = CreateRecipe(self)
        create_recipe.show()

    def create_farm(self):
        """Calls the class MetaData with farm and shows its widget"""
        create_farm = MetaData(self, 'Farm', self.schemas['FRM'])
        create_farm.show()

    def create_customer(self):
        """Calls the class MetaData with customer and shows its widget"""
        create_customer = MetaData(self, 'Customer', self.schemas['CTR'])
        create_customer.show()

    def create_worker(self):
        """Calls the class MetaData with worker and shows its widget"""
        create_customer = MetaData(self, 'Worker', self.schemas['WKR'])
        create_customer.show()

    def create_device(self):
        """Calls the class MetaData with device and shows its widget"""
        create_customer = MetaData(self, 'Device', self.schemas['DVC'])
        create_customer.show()

    def load_schemas(self):
        """Store all schemas in the schemas folder as the self.schemas dict"""
        this_folder = os.path.dirname(os.path.abspath(__file__))
        schemas = os.listdir(this_folder + '/../schemas/')
        for schema in schemas:
            if '.schema' not in schema:
                continue
            self.schemas[schema.split('.')[0]] = json.load(open(this_folder + f'/../schemas/{schema}'))

    def reset_recipe(self):
        """Resets the recipe lists and remove the grid layout with the recipe items"""
        self.added_rows = {}
        self.id_list = {}
        self.idref_widgets = {}
        self.save_temp = {}
        item = self.middle_layout.itemAt(0)
        if item is not None:
            item.widget().close()
            self.middle_layout.removeItem(item)
            del item
        self.frame_stack = {}

    def load_recipe(self):
        """Loads recipes and sets items in the middle_layout"""
        file = QFileDialog.getOpenFileName(self, filter='Recipes (*.recipe)')[0]
        tree = ET.parse(file)
        parent_dict = etree_to_dict(tree.getroot())['ISO11783_TaskData']
        scroll_area = QScrollArea()
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setWidgetResizable(True)

        self.q_layout = QGridLayout()
        widget = QFrame()
        widget.setLayout(self.q_layout)
        self.reset_recipe()
        for key, item in parent_dict.items():
            self.walk_dict(item, key, self.q_layout, widget)

        scroll_area.setWidget(widget)
        scroll_area.show()
        self.middle_layout.addWidget(scroll_area)

        self.update_ref_ids()

    def walk_dict(self, d_in, key, parent_layout: QGridLayout, parent_frame: QFrame):
        """Creates a frame and layout for each key, then sets the key checkbox and attributes widgets, finally checks if
        there are any children then it calls this function again."""
        key_frame = QFrame()
        key_layout = QGridLayout()
        key_layout.__setattr__("key", key)
        key_frame.setLayout(key_layout)

        extra_id = self.find_extra_id(d_in, key)
        self.add_schema_checkbox(key, key_frame, parent_layout, parent_frame, key_layout, d_in, str(extra_id))
        if 'attr' in d_in.keys():
            height = self.set_widget(d_in, key, key_layout, extra_id)
        else:
            height = 50
        key_frame.setMinimumHeight(height)
        parent_layout.addWidget(key_frame, parent_layout.rowCount(), 0, rowSpan=3, columnSpan=1)
        self.frame_stack[key_frame] = {'parent_frame': parent_frame, 'height': height, 'key': key}
        key_frame.setMinimumHeight(height)
        key_frame.setMaximumHeight(height)

        for key_d in d_in.keys():
            if key_d == 'attr':
                continue
            else:
                self.walk_dict(d_in[key_d], key_d, key_layout, key_frame)

    def set_widget(self, d_in: dict, key: str, key_layout: QGridLayout, extra_id: int) -> int:
        """iterate over the content of the d_in dict and """
        size = 65  # Should include space for checkbox etc.
        if key in ['GRD']:
            self.add_file_input(key, d_in['attr'][6], 'G', key_layout, extra_id)
            size += 25
        for attr_name in d_in['attr']:
            item = self.schemas[key][attr_name]
            type_ = item["Type"].lower()
            name = ''.join(' ' + char if char.isupper() else char.strip() for char in item['Attribute_name']).strip()
            if type_ in ['xs:id', 'xs:ref_code_parent']:
                continue
            elif 'string' in type_ or 'hexbinary' in type_:
                widget = QLineEdit(self, toolTip=item['comment'], minimumHeight=20)
                self.add_input_widget(key, name, attr_name, layout=key_layout, widget=widget)
            elif 'long' in type_ or 'short' in type_ or 'byte' in type_:
                widget = QSpinBox(self, toolTip=item['comment'], minimumHeight=20, maximum=100000)
                self.add_input_widget(key, name, attr_name, layout=key_layout, widget=widget)
            elif 'decimal' in type_ or 'double' in type_:
                widget = QDoubleSpinBox(self, toolTip=item['comment'], decimals=6, minimumHeight=20)
                self.add_input_widget(key, name, attr_name, layout=key_layout, widget=widget)
            elif 'xs:idref' in type_ or 'xs:ref_code_child' in type_:
                if item['Ref_id'] == 'CTR':
                    md = MetaData()
                    widget = md.get_ctr_widgets(schema='CTR')
                else:
                    widget = QComboBox(self, minimumHeight=20)
                self.add_input_widget(key, name, attr_name, layout=key_layout, widget=widget)
                self.idref_widgets[widget] = item['Ref_id']
            elif 'xs:nmtoken' in type_:
                widget = QComboBox(self, minimumHeight=20)
                widget.addItems(item['nm_list'])
                self.add_input_widget(key, name, attr_name, layout=key_layout, widget=widget)
            else:
                print(item["Type"], key, attr_name)
            size += 25
        return size

    def find_extra_id(self, d_in, key) -> object:
        """Finds if there is any column with "id" in the schema, if so adds it to the id_list and returns the number of
        ids with that key"""
        extra_id = ''
        if 'attr' in d_in.keys():
            for attr_name in d_in['attr']:
                item = self.schemas[key][attr_name]
                if ('xs:id' in item["Type"].lower() and 'xs:idref' not in item["Type"].lower()) or item["Type"] == 'xs:ref_code_parent':
                    if key not in self.id_list.keys():
                        self.id_list[key] = []
                    self.id_list[key].append(len(self.id_list[key]))
                    extra_id = len(self.id_list[key])
        return extra_id

    def update_ref_ids(self):
        """Updates all widgets in idref_widgets with the items in id_list"""
        for widget, ref in self.idref_widgets.items():
            items = []
            widget.clear()
            for i in self.id_list[ref]:
                items.append(ref + str(i + 1))
            widget.addItems(items)
        for parent_frame in reversed(self.frame_stack.keys()):
            self.frame_stack[parent_frame]['children_height'] = 0
            for frame in self.frame_stack.keys():
                if self.frame_stack[frame]['parent_frame'] == parent_frame:
                    if 'children_height' not in self.frame_stack[frame]:
                        self.frame_stack[frame]['children_height'] = 0
                    self.frame_stack[parent_frame]['children_height'] += self.frame_stack[frame]['height'] + self.frame_stack[frame]['children_height']
            total_height = self.frame_stack[parent_frame]['height'] + self.frame_stack[parent_frame]['children_height']
            parent_frame.setMinimumHeight(total_height)
            parent_frame.setMaximumHeight(total_height)

    def add_schema_checkbox(self, name: str, frame: QFrame, layout, parent_frame: QFrame, key_layout, d_in: dict, extra_id: str = ''):
        """For each key adds a checkbox (to show/hide) and buttons for the possibility to duplicate/remove multiple
        items of each key type"""
        check_box = QCheckBox(text=name + extra_id)
        check_box.__setattr__("frame", frame)
        check_box.setCheckState(Qt.Checked)
        check_box.toggled.connect(self.show_frame)
        add_line_push_button = QPushButton(self, text='+')
        remove_line_push_button = QPushButton(self, text='-')
        add_line_push_button.__setattr__("layout", key_layout)
        add_line_push_button.__setattr__("parent_layout", layout)
        add_line_push_button.__setattr__("parent_frame", parent_frame)
        add_line_push_button.__setattr__("key", name)
        add_line_push_button.__setattr__("d_in", d_in)
        remove_line_push_button.__setattr__("parent_layout", layout)

        remove_line_push_button.clicked.connect(self.remove_extra_row)
        add_line_push_button.clicked.connect(self.add_extra_row)

        layout.addWidget(check_box, layout.rowCount(), 0, 1, 1)
        layout.addWidget(add_line_push_button, layout.rowCount() - 1, 1, 1, 1)
        layout.addWidget(remove_line_push_button, layout.rowCount() - 1, 2, 1, 1)

    def show_frame(self):
        """Shows/Hides the frame"""
        frame = self.sender().frame
        if frame.isHidden():
            frame.show()
        else:
            frame.hide()

    def add_input_widget(self, key, name, attr, layout: QGridLayout = None, widget=None):
        """Adds the widget to the layout in a separate QHBoxlayout with a label in front of it, it also adds the schema
        and the attr_name as special attributes to the widget."""
        field_name_label = QLabel(self, text=name + ': ')
        widget.__setattr__("schema", {key: attr})
        widget.__setattr__("attr_name", attr)
        field_name_layout = QHBoxLayout(self)
        field_name_layout.addWidget(field_name_label)
        field_name_layout.addWidget(widget)
        rows = layout.rowCount()
        layout.addLayout(field_name_layout, rows, 0, 1, 1)

    def add_file_input(self, key, item, attr_name, layout: QGridLayout, extra_id: int):
        """Adds the input widget to the layout (in a QHBoxLayout) and connect the push button for opening file to the
        correct function."""
        file_input_label = QLabel(self, text=f'{key}: ')
        file_input_button = QPushButton(text='Get files', minimumHeight=20)
        layout.__setattr__('id', extra_id)
        file_input_button.__setattr__("layout", layout)
        file_input_button.__setattr__("schema", {key: attr_name})
        if key == 'GRD':
            file_input_button.clicked.connect(self.generate_grid_file)
            file_input_button.__setattr__('value', f'GRD{extra_id:04d}')
        input_layout = QHBoxLayout(self)
        input_layout.addWidget(file_input_label)
        input_layout.addWidget(file_input_button)
        rows = layout.rowCount()
        layout.addLayout(input_layout, rows, 0, 1, 1)

    def get_grid_file(self) -> gpd.GeoDataFrame:
        """Open the dialog and returns the GeoDataFrame, checks that geometry is in the list and adds x, y for the
        centroids"""
        file = QFileDialog.getOpenFileName(self, filter='Shape files (*.shp)')[0]
        df = gpd.read_file(file)
        if 'geometry' not in df:
            raise MsgError('There must be a "geometry" column in the shapefile')
        df['x'] = df['geometry'].centroid.x
        df['y'] = df['geometry'].centroid.y
        return df

    def generate_grid_file(self):
        """Obtains a GeoDataFrame with the content of the user specified file, uses this content to update the widgets
        with the correct data based on the input shp."""
        layout = self.sender().layout
        df = self.get_grid_file()
        widgets = self.get_grid_widgets(layout)
        df.sort_values(['x', 'y'], inplace=True)
        p1, p2 = df['geometry'].centroid[:2]
        widgets['C'].setValue(distance(p1, p2))  # delta_y
        widgets['A'].setValue(p1.y - (p2.y - p1.y) / 2)  # y_min
        df.sort_values(['y', 'x'], inplace=True)
        p1, p2 = df['geometry'].centroid[:2]
        widgets['D'].setValue(distance(p1, p2))  # delta_x
        widgets['B'].setValue(p1.x - (p2.x - p1.x) / 2)  # x min
        widgets['F'].setValue(df['x'].value_counts(p1.x).__len__())
        widgets['E'].setValue(df['y'].value_counts(p1.y).__len__())
        df = df[df.columns.difference(['x', 'y', 'geometry'])]  # drops the x, y, geometry columns
        bytes_written = 0
        for _, _ in df.iterrows():
            for _ in df.columns:
                bytes_written += 4
        widgets['H'].setValue(bytes_written)
        if 'GRD' not in self.save_temp:
            self.save_temp['GRD'] = {}
        self.save_temp['GRD'][layout.id] = df

    def _save_temp_files(self, path):
        """Stores bin files (based on the GeoDataFrame content) in the correct folder"""
        for key in self.save_temp.keys():
            for id_ in self.save_temp[key]:
                df = self.save_temp[key][id_]
                with open(f'{path}/{key}{id_:04d}.bin', 'wb') as f:
                    for index, row in df.iterrows():
                        for col in df.columns:
                            f.write(struct.pack('L', row[col]))

    @staticmethod
    def get_grid_widgets(layout) -> dict:
        """Collects all widgets from the GRD layout and returns a dict with the attribute letter (A-H) and it's
        widget."""
        widgets = {}
        for row in range(layout.rowCount()):
            sub_layout = layout.itemAtPosition(row, 0)
            if sub_layout is not None:
                try:
                    widgets[sub_layout.itemAt(1).widget().schema['GRD']] = sub_layout.itemAt(1).widget()
                except Exception as e:
                    pass
        return widgets

    def add_extra_row(self):
        """Adds an extra row with the same attribute"""
        key = self.sender().key
        d_in = self.sender().d_in
        parent_layout = self.sender().parent_layout
        parent_frame = self.sender().parent_frame
        row_count_before = parent_layout.rowCount()
        self.walk_dict(d_in, key, parent_layout, parent_frame)
        if parent_layout not in self.added_rows.keys():
            self.added_rows[parent_layout] = []
        now_added = []
        for i in range(row_count_before, parent_layout.rowCount()):
            now_added.append(i)
        self.added_rows[parent_layout].append(now_added)
        self.update_ref_ids()

    def remove_extra_row(self):
        """Removes the last "row" added by the "+" button"""
        parent_layout: QGridLayout = self.sender().parent_layout
        if parent_layout not in self.added_rows.keys():
            return
        if len(self.added_rows[parent_layout]) == 0:
            return
        for i in reversed(self.added_rows[parent_layout][-1]):
            for column in range(parent_layout.columnCount()):
                try:
                    item = parent_layout.itemAtPosition(i, column)
                    if item is not None:
                        item.widget().close()
                        parent_layout.removeItem(item)
                        del item
                except Exception as e:
                    print(e)
                    pass
        self.added_rows[parent_layout] = self.added_rows[parent_layout][:-1]

    def store_data(self):
        #Todo: save tzn A
        """Creates an xml tree with the values from all widgets and store the data """
        path = QFileDialog.getSaveFileName(self, 'Save TaskData', filter='xml (*.xml)')[0]
        schemas_layout = self.q_layout
        et_parents = ET.Element('ISO11783_TaskData')
        et_parents.set("VersionMajor", "2")
        et_parents.set("VersionMinor", "0")
        et_parents.set("ManagementSoftwareManufacturer", "pyAgriculture11783")
        et_parents.set("ManagementSoftwareVersion", str(__version__))
        et_parents.set("TaskControllerManufacturer", "pyAgriculture11783" )
        et_parents.set("TaskControllerVersion", str(__version__))
        et_parents.set("DataTransferOrigin", "1")
        for row in range(schemas_layout.rowCount()):
            sub_layout = schemas_layout.itemAtPosition(row, 0)
            if sub_layout is None:
                continue
            if type(sub_layout.widget().layout()) == QGridLayout:
                inner_layout = sub_layout.widget().layout()
                key = sub_layout.widget().layout().key
                xml_sub = ET.SubElement(et_parents, key)
                for j in range(inner_layout.rowCount()):
                    if type(inner_layout.itemAtPosition(j, 0)) == QHBoxLayout:
                        attr = inner_layout.itemAtPosition(j, 0).itemAt(1).widget().schema[key]
                        value = self.get_value_from_widget(inner_layout.itemAtPosition(j, 0).itemAt(1).widget())
                        xml_sub.set(attr, str(value))
                    else:
                        if inner_layout.itemAtPosition(j, 0) is not None:
                            if type(inner_layout.itemAtPosition(j, 0).widget()) == QFrame:
                                self.set_xml_children(inner_layout.itemAtPosition(j, 0).widget().layout(), xml_sub)
        ET.indent(et_parents, space='    ', level=0)
        with open(path, 'w') as f:
            f.write(ET.tostring(et_parents, encoding='unicode'))
        self._save_temp_files(os.path.dirname(path))

    @staticmethod
    def get_value_from_widget(widget) -> str:
        if type(widget) in [QSpinBox, QDoubleSpinBox]:
            value = str(widget.value())
        elif type(widget) == QLineEdit:
            value = widget.text()
        elif type(widget) == QComboBox:
            value = widget.currentIndex()
        elif type(widget) == QPushButton:
            value = widget.value
        else:
            raise MsgError('Could not find the widget type')
        return value

    def set_xml_children(self, layout: QGridLayout, parent: ET.Element):
        """Iterates over the layout and finds QHBoxLayouts and adds them to the sub_xml tree and if ther is a QFrame
        it takes its widget and finds its xml_children.
        """
        key = layout.key
        xml_sub = ET.SubElement(parent, key)
        for i in range(layout.rowCount()):
            item = layout.itemAtPosition(i, 0)
            if item is not None:
                if type(item) == QHBoxLayout:
                    attr = item.itemAt(1).widget().schema[key]
                    value = self.get_value_from_widget(item.itemAt(1).widget())
                    xml_sub.set(attr, str(value))
                else:
                    if type(item.widget()) == QFrame:
                        self.set_xml_children(item.widget().layout(), xml_sub)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    gui = GenerateTaskData()
    gui.show()
    sys.exit(app.exec_())

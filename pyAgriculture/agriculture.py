# Author Axel Hörteborn
from datetime import datetime, timedelta
import json
import xml.etree.ElementTree as ET
import numpy as np
import pandas as pd
from pyAgriculture.sorting_utils import find_by_key


class PyAgriculture:
    def __init__(self, path):
        self.path = path
        self.tasks = []
        self.task_dicts = {}
        self.schemas = {'ASP': json.load(open('../schemas/ASP.schema')),
                        'DAN': json.load(open('../schemas/DAN.schema')),
                        'DET': json.load(open('../schemas/DET.schema')),
                        'DLT': json.load(open('../schemas/DLT.schema')),
                        'DOR': json.load(open('../schemas/DOR.schema')),
                        'DVC': json.load(open('../schemas/DVC.schema')),
                        'DVP': json.load(open('../schemas/DVP.schema')),
                        'PTN': json.load(open('../schemas/PTN.schema')),
                        'TIM': json.load(open('../schemas/TIM.schema')),
                        'TLG': json.load(open('../schemas/TLG.schema')),
                        'TSK': json.load(open('../schemas/TSK.schema')),
                        }
        self.start_date = datetime(year=1980, month=1, day=1)
        self.dt = np.dtype([('millisFromMidnight', np.dtype('uint32')),
                            ('days', np.dtype('uint16')),
                            ('pos north', np.dtype('int32')),
                            ('pos east', np.dtype('int32')),
                            ('pos up', np.dtype('int32')),
                            ('pos status', np.dtype('uint8')),
                            ('nr dlv', np.dtype('uint8'))
                            ])

    @staticmethod
    def _add_from_root_or_child(r_or_c, task_data_dict: dict) -> list:
        """
        :param r_or_c: Root or child object
        """
        if r_or_c.tag not in task_data_dict.keys():
            task_data_dict[r_or_c.tag] = {}
        found_children = False
        if r_or_c.attrib["A"] not in task_data_dict[r_or_c.tag].keys():
            found_children = True
            task_data_dict[r_or_c.tag][r_or_c.attrib["A"]] = r_or_c.attrib
            task_data_dict[r_or_c.tag][r_or_c.attrib["A"]]['parent_tag'] = r_or_c.tag
            try:
                task_data_dict[r_or_c.tag][r_or_c.attrib["A"]]['parent_id'] = r_or_c.attrib["A"]
            except:
                task_data_dict[r_or_c.tag][r_or_c.attrib["A"]]['parent_id'] = None
        return [task_data_dict, found_children]

    def add_children(self, task_data_dict, root):
        """Adds data from the xml schema to a dict, walking down the tags in the .xml file
        """
        if "A" in root.keys():
            task_data_dict, found_children = self._add_from_root_or_child(root, task_data_dict)
        for child in root:
            task_data_dict, found_children = self._add_from_root_or_child(child, task_data_dict)
            if found_children:
                for sub_c in child:
                    self.add_children(task_data_dict, sub_c)
        return task_data_dict

    def gather_data(self, most_important='Dry Yield'):
        tree = ET.parse(self.path + 'TASKDATA.xml')
        root = tree.getroot()
        task_data_dict = {}
        self.task_dicts = self.add_children(task_data_dict, root)
        if 'TLG' in self.task_dicts.keys():
            for tsk in self.task_dicts['TLG'].keys():
                tree = ET.parse(self.path + self.task_dicts['TLG'][tsk]['A'] + '.xml')
                tlg_root = tree.getroot()
                tlg_dict = self.add_children({}, tlg_root)
                tlg_dict = self.combine_task_tlg_data(tlg_dict, task_data_dict)
                columns = self.get_tlg_columns(tlg_dict)
                self.tasks.append(self.read_binaryfile(self.path + self.task_dicts['TLG'][tsk]['A'], columns,
                                                       most_important))

    @staticmethod
    def get_tlg_columns(tlg_dict):
        columns = ['Time_stamp', 'latitude', 'longitude', 'pos_up', 'position_status']
        for key in tlg_dict['DLV'].keys():
            if 'DPD' in tlg_dict['DLV'][key].keys():
                columns.append(tlg_dict['DLV'][key]['DPD']['E'])
        return columns

    @staticmethod
    def combine_task_tlg_data(tlg_dict, task_data_dict):
        for dlv_key in tlg_dict['DLV'].keys():
            tlg_dict['DLV'][dlv_key]['DET'] = task_data_dict['DET'][tlg_dict['DLV'][dlv_key]['C']]
            if tlg_dict['DLV'][dlv_key]['DET']['C'] == '1':
                tlg_dict['DLV'][dlv_key]['DLT'] = task_data_dict['DLT'][tlg_dict['DLV'][dlv_key]['A']]
            else:
                val1 = find_by_key(task_data_dict['DPD'], 'B', tlg_dict['DLV'][dlv_key]['A'])
                val = task_data_dict['DPD'][val1]
                tlg_dict['DLV'][dlv_key]['DPD'] = val
        return tlg_dict

    def _read_static_binary_data(self, data_row: list, read_point: int, binary_data: object) -> list:
        np_data = np.frombuffer(binary_data, self.dt, count=1, offset=read_point)
        millis_from_midnight = int(np_data[0][0])
        days = int(np_data[0][1])
        actual_time = self.start_date + timedelta(days=days, milliseconds=millis_from_midnight)
        data_row[0] = actual_time.strftime('%Y-%m-%dT%H:%M:%S')
        data_row[1] = np_data[0][2] * pow(10, -7)
        data_row[2] = np_data[0][3] * pow(10, -7)
        data_row[3] = np_data[0][4]
        data_row[4] = np_data[0][5]
        nr_dlvs = np_data[0][6]
        return [data_row, nr_dlvs]

    def read_binaryfile(self, file_path: str, df_columns: list, most_important: str):
        with open(file_path + '.bin', 'rb') as fin:
            binary_data = fin.read()
        read_point = 0
        nr_columns = len(df_columns)
        to_tlg_df = []
        data_row = [None] * nr_columns
        while read_point < len(binary_data):
            data_row, nr_dlvs = self._read_static_binary_data(data_row, read_point, binary_data)
            read_point += 20
            for nr, dlv in np.frombuffer(binary_data, [('DLVn', np.dtype('uint8')),
                                                       ('PDV', np.dtype('int32'))],
                                         count=nr_dlvs, offset=read_point):
                if nr >= len(data_row):
                    nr = len(data_row) - 1
                data_row[nr] = dlv
                read_point += 5
            if most_important is None:
                to_tlg_df.append(data_row)
            if data_row[df_columns.index(most_important)] is not None:
                to_tlg_df.append(data_row)
        return pd.DataFrame(to_tlg_df, columns=df_columns)


if __name__ == '__main__':
    py_agri = PyAgriculture('../TASKDATA/')
    py_agri.gather_data()
    print(len(py_agri.tasks))

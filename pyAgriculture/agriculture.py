# Author Axel Hörteborn
from datetime import datetime, timedelta
import json
import xml.etree.ElementTree as ET
import numpy as np
import pandas as pd
from tqdm import tqdm
from pyAgriculture.sorting_utils import find_by_key


class PyAgriculture:
    def __init__(self, path):
        self.path = path
        self.tasks = []
        self.task_dicts = {}
        self.task_infos = []
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
        self.dt = None
        self.static_bytes = 0

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
        else:
            for attribute in r_or_c.attrib.keys():
                pass
            a=1
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

    def gather_data(self, most_important='Dry yield'):
        tree = ET.parse(self.path + 'TASKDATA.xml')
        root = tree.getroot()
        task_data_dict = {}
        self.task_dicts = self.add_children(task_data_dict, root)
        if 'TLG' in self.task_dicts.keys():
            for tsk in tqdm(reversed(list(self.task_dicts['TLG'].keys()))):
                if len(self.tasks) > 2:
                    break
                tree = ET.parse(self.path + self.task_dicts['TLG'][tsk]['A'] + '.xml')
                tlg_root = tree.getroot()
                tlg_dict = self.add_children({}, tlg_root)
                self.get_ptn_data(tlg_dict)
                tlg_dict = self.combine_task_tlg_data(tlg_dict, task_data_dict)
                columns = self.get_tlg_columns(tlg_dict)
                self.task_infos.append(tlg_dict)
                self.tasks.append(self.read_binaryfile(self.path + self.task_dicts['TLG'][tsk]['A'], tlg_dict, columns,
                                                       most_important))

    def get_ptn_data(self, tlg_dict: dict) -> None:
        if 'PTN' not in tlg_dict.keys():
            raise BaseException('Point data does not exist in all TLG files..')
        dtypes = [('millisFromMidnight', np.dtype('uint32')),
                  ('days', np.dtype('uint16')),
                  ('pos north', np.dtype('int32')),
                  ('pos east', np.dtype('int32'))]
        static_bytes = 16
        if 'C' in tlg_dict['PTN'][''].keys():
            dtypes.append(('pos up', np.dtype('int32')))
            static_bytes += 4
        dtypes.append(('pos status', np.dtype('uint8')))
        if 'E' in tlg_dict['PTN'][''].keys():
            dtypes.append(('pdop', np.dtype('uint16')))
            static_bytes += 2
        if 'F' in tlg_dict['PTN'][''].keys():
            dtypes.append(('hdop', np.dtype('uint16')))
            static_bytes += 2
        if 'G' in tlg_dict['PTN'][''].keys():
            dtypes.append(('nr_sat', np.dtype('byte')))
            static_bytes += 1
        if 'H' in tlg_dict['PTN'][''].keys():
            dtypes.append(('GPS time', np.dtype('uint32')))
            static_bytes += 4
        if 'I' in tlg_dict['PTN'][''].keys():
            dtypes.append(('GPS date', np.dtype('uint16')))
            static_bytes += 2
        dtypes.append(('nr dlv', np.dtype('uint8')))
        self.dt = np.dtype(dtypes)
        self.static_bytes = static_bytes

    @staticmethod
    def get_tlg_columns(tlg_dict):
        columns = ['Time_stamp', 'latitude', 'longitude']
        if 'C' in tlg_dict['PTN'][''].keys():
            columns.append('pos_up')
        columns.append('position_status')
        if 'E' in tlg_dict['PTN'][''].keys():
            columns.append('pdop')
        if 'F' in tlg_dict['PTN'][''].keys():
            columns.append('hdop')
        if 'G' in tlg_dict['PTN'][''].keys():
            columns.append('nr_sat')
        if 'H' and 'I' in tlg_dict['PTN'][''].keys():
            columns.append('GPS time')

        for key in tlg_dict['DLV'].keys():
            if 'Name' in tlg_dict['DLV'][key].keys():
                columns.append(tlg_dict['DLV'][key]['Name'])
        return columns

    @staticmethod
    def combine_task_tlg_data(tlg_dict, task_data_dict):
        for dlv_key in tlg_dict['DLV'].keys():
            # Obtains the DeviceElementIdRef
            de_id = tlg_dict['DLV'][dlv_key]['C']
            # Obtains the ProcessDataDDI
            pd_id = tlg_dict['DLV'][dlv_key]['A']
            # Adding the DeviceElement to the tlg dict
            tlg_dict['DLV'][dlv_key]['DET'] = task_data_dict['DET'][de_id]
            if tlg_dict['DLV'][dlv_key]['DET']['C'] == '1':
                # Adding a device to the tlg dict
                found, dpd_key = find_by_key(task_data_dict['DPD'], 'B', pd_id)
                if found:
                    dpd = task_data_dict['DPD'][dpd_key]
                    tlg_dict['DLV'][dlv_key]['Name'] = dpd['E']
                    if 'F' in dpd.keys():
                        dvp = task_data_dict['DVP'][dpd['F']]
                        tlg_dict['DLV'][dlv_key]['DVP'] = {'nr_decimals': dvp['D'], 'scale': dvp['C'],
                                                           'offset': dvp['B']}
                        if 'E' in dvp.keys():
                            tlg_dict['DLV'][dlv_key]['DVP']['unit'] = dvp['E']
                #tlg_dict['DLV'][dlv_key]['DLT'] = task_data_dict['DLT'][pd_id]
                pass
            elif tlg_dict['DLV'][dlv_key]['DET']['C'] == '2':
                # Adding DeviceProcessData to the tlg dict
                found, dpd_key = find_by_key(task_data_dict['DPD'], 'B', pd_id)
                if found:
                    dpd = task_data_dict['DPD'][dpd_key]
                    tlg_dict['DLV'][dlv_key]['Name'] = dpd['E']
                    if 'F' in dpd.keys():
                        dvp = task_data_dict['DVP'][dpd['F']]
                        tlg_dict['DLV'][dlv_key]['DVP'] = {'nr_decimals': dvp['D'], 'scale': dvp['C'],
                                                           'offset': dvp['B']}
                        if 'E' in dvp.keys():
                            tlg_dict['DLV'][dlv_key]['DVP']['unit'] = dvp['E']
            else:
                print(tlg_dict['DLV'][dlv_key]['DET']['C'])
        return tlg_dict

    def _read_static_binary_data(self, data_row: list, read_point: int, binary_data: object, tlg_dict: dict) -> list:
        nr_d = 3
        np_data = np.frombuffer(binary_data, self.dt, count=1, offset=read_point)
        millis_from_midnight = int(np_data[0][0])
        days = int(np_data[0][1])
        actual_time = self.start_date + timedelta(days=days, milliseconds=millis_from_midnight)
        data_row[0] = actual_time.strftime('%Y-%m-%dT%H:%M:%S')
        data_row[1] = np_data[0][2] * pow(10, -7)
        data_row[2] = np_data[0][3] * pow(10, -7)
        for key in tlg_dict['PTN'][''].keys():
            if key in ['C', 'D', 'E', 'F', 'G']:
                data_row[nr_d] = np_data[0][nr_d + 1]
                nr_d += 1
        if 'H' and 'I' in tlg_dict['PTN'][''].keys():
            millis_from_midnight = int(np_data[0][nr_d + 1])
            days = int(np_data[0][nr_d + 2])
            actual_time = self.start_date + timedelta(days=days, milliseconds=millis_from_midnight)
            data_row[nr_d] = actual_time.strftime('%Y-%m-%dT%H:%M:%S')
            nr_d += 2
        nr_dlvs = np_data[0][nr_d + 1]
        return [data_row, nr_dlvs, nr_d - 1]

    def read_binaryfile(self, file_path: str, tlg_dict: dict, df_columns: list, most_important: str):
        with open(file_path + '.bin', 'rb') as fin:
            binary_data = fin.read()
        read_point = 0
        nr_columns = len(df_columns)
        to_tlg_df = []
        dlvs = list(tlg_dict['DLV'])
        data_row = [None] * nr_columns
        unit_row = [None] * nr_columns
        while read_point < len(binary_data):
            data_row, nr_dlvs, nr_static = self._read_static_binary_data(data_row, read_point, binary_data, tlg_dict)
            read_point += self.static_bytes
            for nr, dlv in np.frombuffer(binary_data, [('DLVn', np.dtype('uint8')),
                                                       ('PDV', np.dtype('int32'))],
                                         count=nr_dlvs, offset=read_point):
                if (nr + nr_static + 1) >= len(data_row):
                    # fail?
                    nr = len(data_row) - 1 -nr_static
                if nr >= len(dlvs):
                    dlv_key = dlvs[-1]
                else:
                    dlv_key = dlvs[nr]
                if 'DVP' in tlg_dict['DLV'][dlv_key].keys():
                    dvp = tlg_dict['DLV'][dlv_key]['DVP']
                    #dlv = (dlv + float(dvp['offset'])) * float(dvp['scale']) * pow(10, -int(dvp['nr_decimals']))
                    if unit_row[nr] is None:
                        if 'unit' in dvp.keys():
                            unit_row[nr] = dvp['unit']
                data_row[nr + nr_static] = dlv
                read_point += 5
            if most_important is None:
                to_tlg_df.append(data_row)
            if data_row[df_columns.index(most_important)] is not None:
                to_tlg_df.append(data_row)
                # data_row[df_columns.index(most_important)] = None
                data_row = [None] * nr_columns
        if len(to_tlg_df) == 0:
            return 0
        for idx, col_name in enumerate(df_columns):
            if idx > (nr_static - 1):
                try:
                    df_columns[idx] = col_name + f" ({tlg_dict['DLV'][dlvs[idx - nr_static]]['DVP']['unit']})"
                except IndexError and KeyError:
                    pass
        return pd.DataFrame(to_tlg_df, columns=df_columns)


if __name__ == '__main__':
    py_agri = PyAgriculture('../TASKDATA/')
    py_agri.gather_data()
    print(len(py_agri.tasks))

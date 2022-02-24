import json
import xml.etree.ElementTree as ET
import numpy as np
import pandas as pd
import fiona
import geopandas as gpd
from shapely.geometry import Polygon
from tqdm import tqdm
from pyAgriculture.sorting_utils import find_by_key
from pyAgriculture.agriculture import PyAgriculture
import os
from pathlib import Path


class Grid(PyAgriculture):
    def __init__(self, path):
        super().__init__(path)

    def read_indata(self) -> list:
        tree = ET.parse(self.path + 'TASKDATA.xml')
        task_data_dict = {}
        self.task_dicts = self.add_children(task_data_dict, tree.getroot())
        tasks = []
        for key in task_data_dict['GRD']:
            grd = task_data_dict['GRD'][key]
            gpd_ = self.read_grid_binary_file(self.path + grd['G'], float(grd['A']), float(grd['B']), float(grd['C']),
                                              float(grd['D']), int(grd['F']), int(grd['E']))
            tasks.append(gpd_)
        return tasks

    @staticmethod
    def read_grid_binary_file(file_path: str, n_start, e_start, n_delta, e_delta, nr_n_cols, nr_e_cols
                              ) -> gpd.GeoDataFrame:
        with open(file_path + '.bin', 'rb') as fin:
            binary_data = fin.read()
        read_point = 0
        east_count = 0
        north_count = 0
        cols = list(np.arange(e_start, e_start + e_delta * (nr_e_cols + 1), e_delta))
        rows = list(np.arange(n_start, n_start + n_delta * (nr_n_cols + 1), n_delta))
        polygons = []
        a_s = []
        while read_point < len(binary_data):
            for a in np.frombuffer(binary_data, [('AAA', np.dtype('int32'))],
                                   count=1, offset=read_point):
                a_s.append(a[0])
                read_point += 4
                if east_count >= nr_e_cols:
                    east_count = 0
                    north_count += 1
                x = cols[east_count]
                y = rows[north_count]
                polygons.append(Polygon([(x, y), (x + e_delta, y), (x + e_delta, y + n_delta), (x, y + n_delta)]))
                east_count += 1
        grid_ = gpd.GeoDataFrame({'geometry': polygons,
                                  'Val_a': a_s})
        return grid_


if __name__ == '__main__':
    g = Grid('c:/dev/program/pyAgriculture11783/lund2/')
    grid_list = g.read_indata()
    for grid in grid_list:
        grid.to_file("c:/dev/program/pyAgriculture11783/lund2.shp")

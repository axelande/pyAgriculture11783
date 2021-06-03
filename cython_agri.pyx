import numpy as np
from datetime import timedelta, datetime


cpdef list read_static_binary_data(data_row: list, read_point: int, binary_data: object, tlg_dict: dict, dt: np.dtype,
                                    start_date: datetime):
    """Function to obtain the position and time data """
    cdef int nr_d = 3
    cdef float ten_minus_seven = pow(10, -7)
    np_data = np.frombuffer(binary_data, dt, count=1, offset=read_point)
    cdef int millis_from_midnight = int(np_data[0][0])
    cdef int days = int(np_data[0][1])
    actual_time = start_date + timedelta(days=days, milliseconds=millis_from_midnight)
    data_row[0] = actual_time.strftime('%Y-%m-%dT%H:%M:%S')
    data_row[1] = np_data[0][2] * ten_minus_seven
    data_row[2] = np_data[0][3] * ten_minus_seven
    for key in tlg_dict['PTN'][''].keys():
        if key in ['C', 'D', 'E', 'F', 'G']:
            data_row[nr_d] = np_data[0][nr_d + 1]
            nr_d += 1
    if 'H' and 'I' in tlg_dict['PTN'][''].keys():
        millis_from_midnight2 = int(np_data[0][nr_d + 1])
        days = int(np_data[0][nr_d + 2])
        actual_time = start_date + timedelta(days=days, milliseconds=millis_from_midnight)
        data_row[nr_d] = actual_time.strftime('%Y-%m-%dT%H:%M:%S')
        nr_d += 2
    nr_dlvs = np_data[0][nr_d + 1]
    return [data_row, nr_dlvs, nr_d - 1]
def find_by_key(data_dict: dict, key_name: str, key_value: str):
    for key in data_dict.keys():
        if data_dict[key][key_name] == key_value:
            return key
    return key_value
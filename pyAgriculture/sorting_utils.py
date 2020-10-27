def find_by_key(data_dict: dict, key_name: str, key_value: str):
    """Returns a dict key where "key_name" equals the key_value """
    for key in data_dict.keys():
        if data_dict[key][key_name] == key_value:
            return True, key
    return False, key_value

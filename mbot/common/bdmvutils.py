import os

"""修复emby无法播放bdmv的bug"""


def fix_bdmv_files(path):
    for root, lists, files in os.walk(path):
        for file in files:
            file_path = os.path.join(root, file)
            if file == r'index.bdmv':
                replace_bytes(file_path, b'INDX0300', b'INDX0200')
                continue
            if file == r'MovieObject.bdmv':
                replace_bytes(file_path, b'MOBJ0300', b'MOBJ0200')
                continue
            if file.endswith(r'.clpi'):
                replace_bytes(file_path, b'HDMV0300', b'HDMV0200')
                continue
            if file.endswith(r'.mpls'):
                replace_bytes(file_path, b'MPLS0300', b'MPLS0200')
                continue


def find_max_m2ts(path):
    max_size = 0
    max_filepath = None
    for root, lists, files in os.walk(path):
        for file in files:
            file_path = os.path.join(root, file)
            if os.path.splitext(file)[-1].lower() != '.m2ts':
                continue
            size = os.path.getsize(file_path)
            if size > max_size:
                max_filepath = file_path
                max_size = size
    return max_filepath


def replace_bytes(path, old_byte, new_byte):
    file_obj = open(path, 'rb')
    content = file_obj.read()
    if old_byte in content:
        content = content.replace(old_byte, new_byte)
    with open(path, "wb") as output_file:
        output_file.write(content)

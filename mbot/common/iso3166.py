import os.path


class _Countries:
    """ISO3166国家码处理工具"""
    iso3166_mapping: dict = dict()

    def __init__(self):
        with open(os.path.join(os.path.split(os.path.realpath(__file__))[0], 'country_mapping.txt'), 'r') as f:
            for line in f:
                line = line.strip('\n')
                if line == '':
                    continue
                arr = line.split('=')
                self.iso3166_mapping[arr[0]] = arr[1]

    def get(self, code):
        code = str(code).upper()
        if code in self.iso3166_mapping.keys():
            return self.iso3166_mapping[code]
        else:
            if '其他' in self.iso3166_mapping:
                return self.iso3166_mapping['其他']
            else:
                return '其他'

    def get_cn_names(self):
        return self.iso3166_mapping.values()


Countries = _Countries()

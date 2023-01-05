import binascii
import logging
import random
import re
import string
import base64
import zlib
import emoji
import math
from jinja2 import Template
from lxml import etree
from pyDes import des, CBC, PAD_PKCS5
from pypinyin import Style, lazy_pinyin

_LOGGER = logging.getLogger(__name__)
DES_KEY = 'abc'
punctuation = """！？｡＂＃＄％＆＇（）＊＋－／：；＜＝＞＠［＼］＾＿｀｛｜｝～｟｠｢｣､、〃》「」『』【】〔〕〖〗〘〙〚〛〜〝〞〟〰〾〿–—‘’‛“”„‟…‧﹏"""
re_punctuation = "[{}]+".format(punctuation)


class StringUtils:
    """字符串操作工具"""

    @staticmethod
    def trim_emoji(text):
        """
        去掉字符串中的emoji表情
        :param text:
        :return:
        """
        return emoji.demojize(text)

    @staticmethod
    def noisestr(text):
        """
        把一个字符串中间替换成*号干扰字符
        :param text:
        :return:
        """
        if text is None or len(text) == 0:
            return text
        if len(text) > 2:
            s = 2
        else:
            s = 0
        e = s + math.ceil(len(text) / 2)
        if e == s:
            e += 1
        n = []
        i = 0
        while i < (e - s):
            n.append('*')
            i += 1
        return text.replace(text[s:e], ''.join(n))

    @staticmethod
    def trim_html(text):
        """
        去掉字符串中的html标签
        :param text:
        :return:
        """
        try:
            html = etree.HTML(text=text)
            return html.xpath('string(.)')
        except Exception as e:
            return text

    @staticmethod
    def replace_var(text, context):
        """
        替换字符串中的简单占位变量 格式 {var name}
        :param text:
        :param context:
        :return:
        """
        for m in re.findall(r'\$\{([^\}]+)\}', text):
            var_name = m
            text = text.replace('${%s}' % var_name,
                                str(context[var_name]) if var_name in context else '')
        return text

    @staticmethod
    def render_text(text, **context):
        """
        把模版语法渲染成最终字符串
        :param text:
        :param context:
        :return:
        """
        if not context or len(context) == 0:
            return text
        template = Template(text)
        try:
            return template.render(**context)
        except Exception as e:
            _LOGGER.error('渲染模版出错', exc_info=True)
            _LOGGER.info(text)
            _LOGGER.info(context)

    @staticmethod
    def is_en_text(text):
        """
        是否为一个全英文字符串
        :param text:
        :return:
        """
        if re.match(r'^[a-zA-Z\W_\d]+$', str(text)):
            return True
        else:
            return False

    @staticmethod
    def get_chinese_first_letter(text):
        """
        获取中文拼音首字母组合
        :param text:
        :return:
        """
        if not text:
            return text
        if not StringUtils.is_en_text(text):
            return ''.join(lazy_pinyin(text, style=Style.FIRST_LETTER))
        return text

    @staticmethod
    def get_word_first_letter(string: str):
        if not string:
            return
        w = string[0]
        if StringUtils.is_en_text(w):
            return w
        return ''.join(lazy_pinyin(w, style=Style.FIRST_LETTER))

    @staticmethod
    def replace_special_chars(value, rstring=''):
        if not value:
            return value
        value = str(value)
        """
        去除value中的所有非字母内容，包括标点符号、空格、换行、下划线等
        :param value: 需要处理的内容
        :return: 返回处理后的内容
        """
        # \W 表示匹配非数字字母下划线
        result = re.sub(r'\W+', rstring, value).replace("_", rstring)
        return result

    @staticmethod
    def is_chinese(text) -> bool:
        if not text:
            return text
        return bool(re.match('[^\x00-\xff]', str(text)))

    @staticmethod
    def has_chinese(text) -> bool:
        if not text:
            return text
        text = re.sub(re_punctuation, "", text)
        return bool(re.search('[^\x00-\xff]', str(text)))

    @staticmethod
    def encrypt_string(text: str):
        a = zlib.compress(text.encode())
        secret_key = DES_KEY
        iv = secret_key
        k = des(secret_key, CBC, iv, pad=None, padmode=PAD_PKCS5)
        en = k.encrypt(a, padmode=PAD_PKCS5)
        base64_bytes = base64.b64encode(en)
        base64_string = base64_bytes.decode("ascii")
        return base64_string

    @staticmethod
    def decrypt_text(text: str):
        secret_key = DES_KEY
        iv = secret_key
        k = des(secret_key, CBC, iv, pad=None, padmode=PAD_PKCS5)
        de = k.decrypt(base64.b64decode(text), padmode=PAD_PKCS5)
        return zlib.decompress(de).decode()

    @staticmethod
    def get_bool(string):
        if not string:
            return False
        if str(string).lower() == 'true' or str(string) == '1':
            return True
        else:
            return False

    @staticmethod
    def gen_random_string(slen=10):
        return ''.join(random.sample(string.ascii_letters + string.digits, slen))

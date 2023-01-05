import json

from flask import Response


def api_result(code=None, message=None, data=None, status_code: int = None):
    """
    flask http api的返回数据函数，对api返回结果做标准化的包装
    :param code: 错误码
    :param message: 消息
    :param data: 返回数据
    :param status_code: 返回的http status code
    :return:
    """
    result = {
        "code": code,
        "message": message,
        "data": data,
    }
    if data:
        if isinstance(data, list):
            if len(data) > 0 and 'to_json' in dir(data[0]):
                result['data'] = [i.to_json() for i in data]
        elif 'to_json' in dir(data):
            result['data'] = data.to_json()
    response = Response(json.dumps(result, ensure_ascii=False).encode('utf8'),
                        content_type="application/json; charset=utf-8")
    if status_code:
        response.status_code = status_code
    return response

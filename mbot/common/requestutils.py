import ssl
from http.cookies import SimpleCookie

import aiofiles
import aiohttp
import certifi
import httpx
from tenacity import retry, wait_fixed, stop_after_attempt


class RequestUtils:
    @staticmethod
    def cookie_str_to_simple_cookie(cookie_str: str):
        if not cookie_str:
            return
        cookie = SimpleCookie(cookie_str)
        cookies = {}
        for key, morsel in cookie.items():
            cookies[key] = morsel.value
        return cookies

    @staticmethod
    def get_etag(headers):
        if not headers:
            return
        etag = headers.get('etag')
        if not etag:
            return
        if etag.startswith('W/'):
            etag = etag[3:-1]
        return etag

    @staticmethod
    @retry(wait=wait_fixed(3), stop=stop_after_attempt(3), reraise=True)
    async def async_download_file(download_url, save_filepath):
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        conn = aiohttp.TCPConnector(ssl=ssl_context)
        async with aiohttp.ClientSession(connector=conn) as session:
            async with session.get(download_url) as resp:
                if resp.status == 200:
                    f = await aiofiles.open(save_filepath, mode='wb')
                    await f.write(await resp.read())
                    await f.close()

    @staticmethod
    def download_file(download_url, save_filepath):
        with httpx.stream('GET', download_url) as r:
            with open(save_filepath, "wb") as f:
                for chunk in r.iter_bytes():
                    if chunk:
                        f.write(chunk)

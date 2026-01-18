import unittest
import os
import zipfile
import urllib3.exceptions
import asyncio
import io
import tempfile

import httpx
from PIL import Image

from nhentai import constant
from nhentai.cmdline import load_config
from nhentai.downloader import Downloader, CompressedDownloader
from nhentai.parser import doujinshi_parser
from nhentai.doujinshi import Doujinshi
from nhentai.utils import generate_html

did = 440546


def has_jepg_file(path):
    with zipfile.ZipFile(path, 'r') as zf:
        return '01.jpg' in zf.namelist()


def is_zip_file(path):
    try:
        with zipfile.ZipFile(path, 'r') as _:
            return True
    except (zipfile.BadZipFile, FileNotFoundError):
        return False


class TestDownload(unittest.TestCase):
    def setUp(self) -> None:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        load_config()
        constant.CONFIG['cookie'] = os.getenv('NHENTAI_COOKIE')
        constant.CONFIG['useragent'] = os.getenv('NHENTAI_UA')

        self.info = Doujinshi(**doujinshi_parser(did), name_format='%i')

    def test_download(self):
        info = self.info
        info.downloader = Downloader(path='/tmp', threads=5)
        info.download()

        self.assertTrue(os.path.exists(f'/tmp/{did}/01.jpg'))

        generate_html('/tmp', info)
        self.assertTrue(os.path.exists(f'/tmp/{did}/index.html'))

    def test_zipfile_download(self):
        info = self.info
        info.downloader = CompressedDownloader(path='/tmp', threads=5)
        info.download()

        zipfile_path = f'/tmp/{did}.zip'
        self.assertTrue(os.path.exists(zipfile_path))
        self.assertTrue(is_zip_file(zipfile_path))
        self.assertTrue(has_jepg_file(zipfile_path))


class TestImageHandling(unittest.TestCase):
    def _make_image_bytes(self, fmt):
        image = Image.new('RGB', (1, 1), color='red')
        buffer = io.BytesIO()
        image.save(buffer, format=fmt)
        return buffer.getvalue()

    def test_extension_correction_from_header(self):
        jpeg_bytes = self._make_image_bytes('JPEG')
        response = httpx.Response(
            200,
            headers={'content-type': 'image/jpeg'},
            content=jpeg_bytes,
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            downloader = Downloader(path=tmpdir, webp=False)
            downloader.create_storage_object(tmpdir)
            asyncio.run(downloader.save('01.png', response))

            self.assertTrue(os.path.exists(os.path.join(tmpdir, '01.jpg')))

    def test_magic_fallback(self):
        png_bytes = self._make_image_bytes('PNG')
        response = httpx.Response(200, headers={}, content=png_bytes)
        with tempfile.TemporaryDirectory() as tmpdir:
            downloader = Downloader(path=tmpdir, webp=False)
            downloader.create_storage_object(tmpdir)
            asyncio.run(downloader.save('01.jpg', response))

            self.assertTrue(os.path.exists(os.path.join(tmpdir, '01.png')))

    def test_webp_conversion_for_zip(self):
        png_bytes = self._make_image_bytes('PNG')
        response = httpx.Response(200, headers={'content-type': 'image/png'}, content=png_bytes)
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_base = os.path.join(tmpdir, 'archive')
            downloader = CompressedDownloader(path=tmpdir, webp=True)
            downloader.create_storage_object(zip_base)
            asyncio.run(downloader.save('01.png', response))
            downloader.close()

            zip_path = f'{zip_base}.zip'
            with zipfile.ZipFile(zip_path, 'r') as zf:
                self.assertIn('01.webp', zf.namelist())
                data = zf.read('01.webp')[:12]
                self.assertTrue(data.startswith(b'RIFF') and data[8:12] == b'WEBP')


if __name__ == '__main__':
    unittest.main()

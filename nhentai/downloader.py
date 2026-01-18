# coding: utf-8

import os
import asyncio
import httpx
import urllib3.exceptions
import zipfile
import io
import aiofiles

from urllib.parse import urlparse
from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn
from nhentai import constant
from nhentai.logger import logger, console
from nhentai.utils import Singleton, async_request


urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
JPEG_SIGNATURE = b"\xff\xd8\xff"
RIFF_SIGNATURE = b"RIFF"
WEBP_SIGNATURE = b"WEBP"

CONTENT_TYPE_TO_FORMAT = {
    "image/png": "png",
    "image/jpeg": "jpeg",
    "image/jpg": "jpeg",
    "image/webp": "webp",
    "image/gif": "gif",
}

FORMAT_EXTENSIONS = {
    "png": {".png"},
    "jpeg": {".jpg", ".jpeg"},
    "webp": {".webp"},
    "gif": {".gif"},
}

DEFAULT_EXTENSION = {
    "png": ".png",
    "jpeg": ".jpg",
    "webp": ".webp",
    "gif": ".gif",
}


def detect_image_format(content_type, content):
    content_format = None
    if content_type:
        normalized_type = content_type.split(";")[0].strip().lower()
        content_format = CONTENT_TYPE_TO_FORMAT.get(normalized_type)

    magic_format = None
    if content:
        if content.startswith(PNG_SIGNATURE):
            magic_format = "png"
        elif content.startswith(JPEG_SIGNATURE):
            magic_format = "jpeg"
        elif (
            len(content) >= 12
            and content[:4] == RIFF_SIGNATURE
            and content[8:12] == WEBP_SIGNATURE
        ):
            magic_format = "webp"

    if content_format and magic_format and content_format != magic_format:
        return magic_format

    return content_format or magic_format


def normalize_filename_extension(filename, detected_format):
    if not detected_format:
        return filename

    base, extension = os.path.splitext(filename)
    extension = extension.lower()
    if extension in FORMAT_EXTENSIONS.get(detected_format, set()):
        return filename

    return f"{base}{DEFAULT_EXTENSION.get(detected_format, extension)}"


def convert_to_webp(image_bytes, quality):
    from PIL import Image

    with io.BytesIO(image_bytes) as input_buffer:
        with Image.open(input_buffer) as image:
            with io.BytesIO() as output:
                image.save(output, format="WEBP", quality=quality)
                return output.getvalue()


def prepare_image_payload(filename, response, webp):
    content = response.content if response is not None else b""
    detected_format = detect_image_format(response.headers.get("content-type") if response else None, content)
    filename = normalize_filename_extension(filename, detected_format)

    if webp and detected_format in {"png", "jpeg"} and content:
        quality = 100 if detected_format == "png" else 90
        try:
            content = convert_to_webp(content, quality=quality)
            base, _extension = os.path.splitext(filename)
            filename = f"{base}.webp"
        except Exception as exc:
            logger.error(f"WebP conversion failed for {filename}: {exc}")

    return filename, content


def download_callback(result):
    result, data = result
    if result == 0:
        logger.warning('fatal errors occurred, ignored')
    elif result == -1:
        logger.warning(f'url {data} return status code 404')
    elif result == -2:
        logger.warning('Ctrl-C pressed, exiting sub processes ...')
    elif result == -3:
        # workers won't be run, just pass
        pass
    else:
        logger.log(16, f'{data} downloaded successfully')


class Downloader(Singleton):
    def __init__(self, path='', threads=5, timeout=30, delay=0, exit_on_fail=False,
                 no_filename_padding=False, webp=False):
        self.threads = threads
        self.path = str(path)
        self.timeout = timeout
        self.delay = delay
        self.exit_on_fail = exit_on_fail
        self.folder = None
        self.semaphore = None  # Will be initialized in async context
        self.no_filename_padding = no_filename_padding
        self.webp = webp

    async def fiber(self, tasks):
        # Initialize semaphore in async context to use the current event loop
        if self.semaphore is None:
            self.semaphore = asyncio.Semaphore(self.threads)

        download_tasks = [asyncio.create_task(task) for task in tasks]
        with Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TextColumn("•"),
            TextColumn("[cyan]{task.completed}/{task.total}"),
            TextColumn("pages"),
            TimeRemainingColumn(),
            console=console,
            refresh_per_second=10,
            transient=False,
        ) as progress:
            download_task = progress.add_task("[green]Downloading", total=len(download_tasks))

            for completed_task in asyncio.as_completed(download_tasks):
                if constant.STOP_REQUESTED:
                    for task in download_tasks:
                        if not task.done():
                            task.cancel()
                    raise KeyboardInterrupt
                try:
                    result = await completed_task
                    if result[0] > 0:
                        progress.update(download_task, advance=1)
                    else:
                        progress.update(download_task, advance=1)
                        raise Exception(f'{result[1]} download failed, return value {result[0]}')
                except KeyboardInterrupt:
                    for task in download_tasks:
                        if not task.done():
                            task.cancel()
                    raise
                except Exception as e:
                    # Log errors using logger, rich will handle the display
                    progress.console.print(f'[red]Error:[/red] {e}')
                    if self.exit_on_fail:
                        raise Exception('User intends to exit on fail')

    async def _semaphore_download(self, *args, **kwargs):
        async with self.semaphore:
            return await self.download(*args, **kwargs)

    async def download(self, url, folder='', filename='', retried=0, proxy=None, length=0):
        # Suppress verbose logging during downloads - progress bar shows status
        if self.delay:
            await asyncio.sleep(self.delay)

        filename = filename if filename else os.path.basename(urlparse(url).path)
        base_filename, extension = os.path.splitext(filename)

        if not self.no_filename_padding:
            filename = base_filename.zfill(length) + extension
        else:
            filename = base_filename + extension

        try:
            response = await async_request('GET', url, timeout=self.timeout, proxy=proxy)

            if response.status_code != 200:
                path = urlparse(url).path
                for mirror in constant.IMAGE_URL_MIRRORS:
                    # Silently try mirrors - progress bar shows overall status
                    mirror_url = f'{mirror}{path}'
                    response = await async_request('GET', mirror_url, timeout=self.timeout, proxy=proxy)
                    if response.status_code == 200:
                        break
                else:
                    # If loop completes without break, all mirrors failed
                    logger.error(f'All mirrors failed for {filename}')
                    return -1, url

            # Validate response before saving
            if response.status_code != 200:
                logger.error(f'Failed to download {filename}: HTTP {response.status_code}')
                return -1, url

            if not await self.save(filename, response):
                logger.error(f'Failed to save {filename}')
                return -2, url

        except KeyboardInterrupt:
            logger.info('Download interrupted by user')
            if constant.STOP_REQUESTED:
                raise
            return -4, url

        except (httpx.HTTPStatusError, httpx.TimeoutException, httpx.ConnectError):
            if retried < constant.RETRY_TIMES:
                # Silently retry - progress bar shows overall status
                return await self.download(
                    url=url,
                    folder=folder,
                    filename=filename,
                    retried=retried + 1,
                    proxy=proxy,
                )
            else:
                # Only log when all retries exhausted
                logger.warning(f'Failed to download {filename} after {constant.RETRY_TIMES} retries')
                return -2, url

        except Exception as e:
            logger.error(f"Unexpected error: {type(e).__name__}: {e}")
            if os.getenv('DEBUG'):
                import traceback
                logger.debug(traceback.format_exc())
            return -9, url

        return 1, url

    async def save(self, filename, response) -> bool:
        if response is None:
            logger.error('Error: Response is None')
            return False
        filename, content = prepare_image_payload(filename, response, self.webp)
        save_file_path = os.path.join(self.folder, filename)
        async with aiofiles.open(save_file_path, 'wb') as f:
            await f.write(content)
        return True

    def create_storage_object(self, folder: str):
        if not os.path.exists(folder):
            try:
                os.makedirs(folder)
            except EnvironmentError as e:
                logger.critical(str(e))
        self.folder: str = folder
        self.close = lambda: None  # Only available in class CompressedDownloader

    def start_download(self, queue, folder='') -> bool:
        if not isinstance(folder, (str,)):
            folder = str(folder)

        if self.path:
            folder = os.path.join(self.path, folder)

        logger.log(16, f'Saving to: {folder}')
        self.create_storage_object(folder)

        # Fix for incomplete downloads
        self.semaphore = None
        if hasattr(self, 'zip_lock'):
            self.zip_lock = None

        if os.getenv('DEBUG', None) == 'NODOWNLOAD':
            # Assuming we want to continue with rest of process.
            return True

        digit_length = len(str(len(queue)))
        logger.log(16, f'Total pages: {len(queue)}')
        coroutines = [
            self._semaphore_download(url, filename=os.path.basename(urlparse(url).path), length=digit_length)
            for url in queue
        ]

        # Prevent coroutines infection
        asyncio.run(self.fiber(coroutines))

        self.close()

        return True


class CompressedDownloader(Downloader):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.zip_lock = None  # Will be initialized in async context

    def create_storage_object(self, folder):
        filename = f'{folder}.zip'
        logger.debug(f'Creating ZIP file: {filename}')
        self.zipfile = zipfile.ZipFile(filename, 'w')
        self.close = lambda: self.zipfile.close()

    async def save(self, filename, response) -> bool:
        if response is None:
            logger.error('Error: Response is None')
            return False

        # Initialize lock in async context if needed
        if self.zip_lock is None:
            self.zip_lock = asyncio.Lock()

        filename, content = prepare_image_payload(filename, response, self.webp)
        # Acquire lock before writing to zipfile to prevent race conditions
        async with self.zip_lock:
            self.zipfile.writestr(filename, content)

        return True

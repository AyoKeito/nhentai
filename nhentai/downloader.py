# coding: utf-8

import os
import asyncio
import httpx
import urllib3.exceptions
import zipfile
import io
import aiofiles

from urllib.parse import urlparse
from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn, DownloadColumn, TransferSpeedColumn
from nhentai import constant
from nhentai.logger import logger
from nhentai.utils import Singleton, async_request


urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

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
                 no_filename_padding=False):
        self.threads = threads
        self.path = str(path)
        self.timeout = timeout
        self.delay = delay
        self.exit_on_fail = exit_on_fail
        self.folder = None
        self.semaphore = asyncio.Semaphore(threads)
        self.no_filename_padding = no_filename_padding

    async def fiber(self, tasks):
        # Semaphore now initialized in __init__

        with Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TextColumn("•"),
            TextColumn("[cyan]{task.completed}/{task.total}"),
            TextColumn("pages"),
            TimeRemainingColumn(),
        ) as progress:
            download_task = progress.add_task("[green]Downloading", total=len(tasks))

            for completed_task in asyncio.as_completed(tasks):
                try:
                    result = await completed_task
                    if result[0] > 0:
                        progress.update(download_task, advance=1)
                    else:
                        progress.update(download_task, advance=1)
                        raise Exception(f'{result[1]} download failed, return value {result[0]}')
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
            return -4, url

        except (httpx.HTTPStatusError, httpx.TimeoutException, httpx.ConnectError) as e:
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
        save_file_path = os.path.join(self.folder, filename)
        async with aiofiles.open(save_file_path, 'wb') as f:
            if response is not None:
                length = response.headers.get('content-length')
                if length is None:
                    await f.write(response.content)
                else:
                    async for chunk in response.aiter_bytes(2048):
                        await f.write(chunk)
        return True

    def create_storage_object(self, folder:str):
        if not os.path.exists(folder):
            try:
                os.makedirs(folder)
            except EnvironmentError as e:
                logger.critical(str(e))
        self.folder:str = folder
        self.close = lambda: None # Only available in class CompressedDownloader

    def start_download(self, queue, folder='') -> bool:
        if not isinstance(folder, (str,)):
            folder = str(folder)

        if self.path:
            folder = os.path.join(self.path, folder)

        logger.log(16, f'Saving to: {folder}')
        self.create_storage_object(folder)

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
        self.zip_lock = asyncio.Lock()

    def create_storage_object(self, folder):
        filename = f'{folder}.zip'
        logger.debug(f'Creating ZIP file: {filename}')
        self.zipfile = zipfile.ZipFile(filename,'w')
        self.close = lambda: self.zipfile.close()

    async def save(self, filename, response) -> bool:
        if response is None:
            logger.error('Error: Response is None')
            return False

        image_data = io.BytesIO()
        length = response.headers.get('content-length')
        if length is None:
            content = await response.read()
            image_data.write(content)
        else:
            async for chunk in response.aiter_bytes(2048):
                image_data.write(chunk)

        image_data.seek(0)

        # Acquire lock before writing to zipfile to prevent race conditions
        async with self.zip_lock:
            self.zipfile.writestr(filename, image_data.read())

        return True

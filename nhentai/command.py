# coding: utf-8
import os
import shutil
import sys
import signal
import platform
import urllib3.exceptions
from enum import Enum

from nhentai import constant
from nhentai.cmdline import cmd_parser, banner, write_config
from nhentai.parser import doujinshi_parser, search_parser, legacy_search_parser, print_doujinshi, favorites_parser
from nhentai.doujinshi import Doujinshi
from nhentai.downloader import Downloader, CompressedDownloader
from nhentai.logger import logger
from nhentai.constant import BASE_URL
from nhentai.utils import generate_html, generate_doc, generate_main_html, generate_metadata, \
    paging, check_cookie, signal_handler, DB, move_to_folder


def configure_runtime(options):
    # CONFIG['proxy'] will be changed after cmd_parser()
    if constant.CONFIG['proxy']:
        if isinstance(constant.CONFIG['proxy'], dict):
            constant.CONFIG['proxy'] = constant.CONFIG['proxy'].get('http', '')
            logger.warning(f'Update proxy config to: {constant.CONFIG["proxy"]}')
            write_config()

        logger.info(f'Using proxy: {constant.CONFIG["proxy"]}')

    if not constant.CONFIG['template']:
        constant.CONFIG['template'] = 'default'

    logger.info(f'Using viewer template "{constant.CONFIG["template"]}"')

    # check your cookie
    check_cookie()


def resolve_doujinshi_ids(options):
    doujinshis = []
    doujinshi_ids = []

    page_list = paging(options.page)

    if options.favorites:
        if not options.is_download:
            logger.warning('You do not specify --download option')

        doujinshis = favorites_parser(page=page_list) if options.page else favorites_parser()

    elif options.keyword:
        if constant.CONFIG['language']:
            logger.info(f'Using default language: {constant.CONFIG["language"]}')
            options.keyword += f' language:{constant.CONFIG["language"]}'

        _search_parser = legacy_search_parser if options.legacy else search_parser
        doujinshis = _search_parser(options.keyword, sorting=options.sorting, page=page_list,
                                    is_page_all=options.page_all)

    elif options.artist:
        doujinshis = legacy_search_parser(options.artist, sorting=options.sorting, page=page_list,
                                          is_page_all=options.page_all, type_='ARTIST')

    elif not doujinshi_ids:
        doujinshi_ids = options.id

    print_doujinshi(doujinshis)
    if options.is_download and doujinshis:
        doujinshi_ids = [i['id'] for i in doujinshis]

    if options.is_save_download_history:
        with DB() as db:
            data = set(map(int, db.get_all()))

        doujinshi_ids = list(set(map(int, doujinshi_ids)) - set(data))
        logger.info(f'New doujinshis account: {len(doujinshi_ids)}')

    return doujinshi_ids


class DownloadStatus(Enum):
    SUCCESS = 'success'
    SKIPPED = 'skipped'
    FAILED = 'failed'


def validate_options(options):
    errors = []
    if options.move_to_folder and options.rm_origin_dir:
        errors.append('Cannot use --move-to-folder together with --rm-origin-dir.')
    if options.zip and options.is_nohtml:
        errors.append('Cannot use --zip together with --nohtml (zip already disables HTML).')

    if errors:
        for message in errors:
            logger.error(message)
        sys.exit(1)


def download_one(doujinshi_id, options, downloader):
    doujinshi_info = doujinshi_parser(doujinshi_id)
    if not doujinshi_info:
        return DownloadStatus.FAILED, f'Failed to get info for doujinshi {doujinshi_id}', None

    doujinshi = Doujinshi(name_format=options.name_format, **doujinshi_info)
    doujinshi.downloader = downloader

    if not doujinshi.check_if_need_download(options):
        return (
            DownloadStatus.SKIPPED,
            f'Skip download doujinshi because a PDF/CBZ file exists of doujinshi {doujinshi.name}',
            doujinshi,
        )

    try:
        result = doujinshi.download()
    except Exception as e:
        return DownloadStatus.FAILED, f'Exception during download: {e}', doujinshi

    if result is False or (isinstance(result, int) and result < 0):
        return DownloadStatus.FAILED, f'Download failed for {doujinshi.name}', doujinshi

    return DownloadStatus.SUCCESS, None, doujinshi


def run_downloads(options, doujinshi_ids):
    if options.zip:
        options.is_nohtml = True

    downloader = (CompressedDownloader if options.zip else Downloader)(path=options.output_dir, threads=options.threads,
                            timeout=options.timeout, delay=options.delay,
                            exit_on_fail=options.exit_on_fail,
                            no_filename_padding=options.no_filename_padding)

    failed_downloads = []

    for doujinshi_id in doujinshi_ids:
        status, message, doujinshi = download_one(doujinshi_id, options, downloader)
        if status is DownloadStatus.FAILED:
            logger.error(message)
            failed_downloads.append(doujinshi_id)
            if options.exit_on_fail:
                sys.exit(1)
            continue
        if status is DownloadStatus.SKIPPED and message:
            logger.info(message)

        if options.generate_metadata:
            generate_metadata(options.output_dir, doujinshi)

        if options.is_save_download_history:
            with DB() as db:
                db.add_one(doujinshi.id)

        if not options.is_nohtml:
            generate_html(options.output_dir, doujinshi, template=constant.CONFIG['template'])

        if options.is_cbz:
            generate_doc('cbz', options.output_dir, doujinshi, options.regenerate)

        if options.is_pdf:
            generate_doc('pdf', options.output_dir, doujinshi, options.regenerate)

        if options.move_to_folder:
            if options.is_cbz:
                move_to_folder(options.output_dir, doujinshi, 'cbz')
            if options.is_pdf:
                move_to_folder(options.output_dir, doujinshi, 'pdf')

        if options.rm_origin_dir:
            shutil.rmtree(os.path.join(options.output_dir, doujinshi.filename), ignore_errors=True)

    if options.main_viewer:
        generate_main_html(options.output_dir)

    # Print summary of failed downloads
    if failed_downloads:
        logger.error(f'Failed to download {len(failed_downloads)} doujinshi: {failed_downloads}')

    if not platform.system() == 'Windows':
        logger.log(16, '🍻 All done.')
    else:
        logger.log(16, 'All done.')


def show_doujinshi(options, doujinshi_ids):
    for doujinshi_id in doujinshi_ids:
        doujinshi_info = doujinshi_parser(doujinshi_id)
        if doujinshi_info:
            doujinshi = Doujinshi(name_format=options.name_format, **doujinshi_info)
        else:
            continue
        doujinshi.show()


def main():
    banner()

    if sys.version_info < (3, 0, 0):
        logger.error('nhentai now only support Python 3.x')
        sys.exit(1)

    options = cmd_parser()
    validate_options(options)
    logger.info(f'Using mirror: {BASE_URL}')

    if options.retry:
        constant.RETRY_TIMES = int(options.retry)

    configure_runtime(options)
    doujinshi_ids = resolve_doujinshi_ids(options)

    if options.is_show:
        show_doujinshi(options, doujinshi_ids)
    else:
        run_downloads(options, doujinshi_ids)


urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
signal.signal(signal.SIGINT, signal_handler)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(1)

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

nhentai is a CLI tool for downloading doujinshi from nhentai.net. The project is written in Python and uses asyncio for concurrent downloads, BeautifulSoup for HTML parsing, and supports multiple output formats (CBZ, PDF, ZIP).

## Development Commands

### Installation

```bash
# Install from source
pip install --no-cache-dir .

# Install with poetry
poetry install
```

### Running Tests

```bash
# Run all tests
python -m unittest discover tests

# Run specific test file
python -m unittest tests.test_download
python -m unittest tests.test_parser
python -m unittest tests.test_login

# Tests require environment variables for authentication:
# NHENTAI_COOKIE - Cookie from nhentai.net
# NHENTAI_UA - User agent string
```

### Running the Application

```bash
# After installation, use the nhentai command
nhentai --id 123855

# Or run directly from source
python -m nhentai.command

# Set debug mode
DEBUG=1 nhentai --id 123855

# Skip downloads during testing
DEBUG=NODOWNLOAD nhentai --id 123855
```

## Architecture

### Core Components

**command.py** - Main entry point. Orchestrates the download flow:
1. Parses command-line arguments via cmdline.py
2. Uses parser.py to fetch doujinshi metadata or search results
3. Creates Doujinshi objects from parsed data
4. Delegates downloading to downloader.py
5. Generates output formats (HTML, CBZ, PDF) via utils.py and serializer.py

**parser.py** - Handles all HTTP requests and HTML/JSON parsing:
- `doujinshi_parser()` - Fetches metadata for a single doujinshi by ID
- `search_parser()` - Modern JSON API search (default)
- `legacy_search_parser()` - Fallback HTML-based search
- `favorites_parser()` - Fetches user's favorites (requires authentication)
- Uses BeautifulSoup to extract: title, artists, tags, pages, image IDs

**doujinshi.py** - Data model representing a single doujinshi:
- Stores metadata (name, ID, tags, artists, etc.)
- Handles filename formatting using format strings (%i, %t, %a, etc.)
- `check_if_need_download()` - Determines if download should proceed
- `download()` - Constructs image URLs and delegates to downloader

**downloader.py** - Async download engine with two implementations:
- `Downloader` - Downloads to folder with individual image files
- `CompressedDownloader` - Downloads directly into a ZIP file
- Uses asyncio with semaphore for concurrent downloads (default: 5 threads)
- Implements retry logic and mirror fallback for failed downloads
- Image URLs follow pattern: `https://i1.nhentai.net/galleries/{img_id}/{page}.{ext}`

**constant.py** - Configuration and URL constants:
- Base URL can be overridden via `NHENTAI` environment variable for mirrors
- Config stored in `~/.nhentai/config.json` (Linux: `$XDG_DATA_HOME/nhentai`)
- Supports proxy, cookie, useragent, language, template settings
- Image mirrors (i2-i7) used as fallbacks when primary fails

**serializer.py** - Metadata export formats:
- `serialize_json()` - Simple JSON metadata
- `serialize_comic_xml()` - ComicInfo.xml for comic readers
- `serialize_info_txt()` - Human-readable text format
- `set_js_database()` - JavaScript viewer database

**utils.py** - Shared utilities:
- `request()` / `async_request()` - HTTP wrappers with auth headers
- `generate_html()` - Creates local HTML viewer from template
- `generate_doc()` - Generates CBZ/PDF files
- `DB()` - SQLite-based download history tracker
- `check_cookie()` - Validates authentication on startup

### Key Patterns

**Authentication**: Cookie and user-agent must be set to bypass Cloudflare:
- Set once: `nhentai --cookie="..." --useragent="..."`
- Stored in config.json and reused automatically
- Required for favorites and to avoid rate limiting

**Filename Formatting**: Uses placeholder system in `doujinshi.py:33-56`:
- %i = ID, %t = title, %s = subtitle, %a = artists, %g = groups
- %ag = artists or groups (fallback), %p = pretty name, %f = favorite count
- Windows requires double %% (%%i) due to cmd.exe escaping

**Download Flow** in `command.py:97-137`:
1. Parse doujinshi metadata to get img_id and page extensions
2. Construct image URLs: `{IMAGE_URL}/{img_id}/{page_num}.{ext}`
3. Downloader creates folder/ZIP and downloads with semaphore limiting
4. Generate metadata files if requested (--meta flag)
5. Generate HTML viewer unless --no-html specified
6. Optionally convert to CBZ/PDF and cleanup original files

**Search API**: Two methods (command.py:61-72):
- Modern: JSON API at `/api/galleries/search` (default, faster)
- Legacy: HTML scraping at `/search/` (fallback with --legacy flag)
- Both return list of {id, title} dicts passed to print_doujinshi()

**Extension Mapping** in `doujinshi.py:11-16`:
- API returns single-char extensions: 'j'=jpg, 'p'=png, 'g'=gif, 'w'=webp
- Each page can have different extension (stored in ext array)

**Error Handling**:
- Retry mechanism in downloader.py with RETRY_TIMES (default: 3)
- Mirror fallback if primary image server fails (i1 -> i2-i7)
- `--exit-on-fail` flag stops on first failure to prevent incomplete downloads

## Important Notes

- All download operations are async using asyncio (downloader.py uses async_request)
- Image URLs are constructed from img_id (gallery ID) not doujinshi ID
- Config persists across runs in ~/.nhentai/config.json
- Thread count limited to max 15 in cmdline.py:268-270
- Tests use doujinshi ID 440546 as reference (tests/test_download.py:13)

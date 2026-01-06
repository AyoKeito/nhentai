nhentai
=======

あなたも変態。 いいね?

|license| |python|

**🔧 FIXED FORK - CLOUDFLARE BYPASS**

This is a fixed fork of the original nhentai CLI tool with Cloudflare bypass functionality.

**Key Changes:**

- ✅ Bypasses Cloudflare protection using curl_cffi

- ✅ Works with current nhentai.net anti-bot measures

- ✅ Full authentication support with proper cookies

- ✅ All features functional (download, search, favorites)

**Note:** This fork must be installed from source - it is not available on PyPI.

nhentai is a CLI tool for downloading doujinshi from `nhentai.net <https://nhentai.net>`_

Original repository: `https://github.com/RicterZ/nhentai <https://github.com/RicterZ/nhentai>`_

============
Installation
============

**This fork must be built from source.**

From Github:

.. code-block:: bash

    git clone https://github.com/AyoKeito/nhentai
    cd nhentai
    pip install --no-cache-dir .

Using `uv <https://github.com/astral-sh/uv>`_ (recommended):


.. code-block:: bash

    git clone https://github.com/AyoKeito/nhentai
    cd nhentai
    uv venv
    source venv/Scripts/activate  # On Windows Git Bash
    # OR: venv\Scripts\activate.bat  # On Windows CMD
    # OR: source venv/bin/activate   # On Linux/Mac
    pip install -e .

Build Docker container:

.. code-block:: bash

    git clone https://github.com/AyoKeito/nhentai
    cd nhentai
    docker build -t nhentai:latest .
    docker run --rm -it -v ~/Downloads/doujinshi:/output -v ~/.nhentai/:/root/.nhentai nhentai --id 123855
    
=====
Usage
=====
**⚠️IMPORTANT - CLOUDFLARE BYPASS⚠️**: This fork bypasses Cloudflare automatically, but you still need to set your cookies and user-agent for full functionality.

.. code-block:: bash

    nhentai --useragent="USER AGENT of YOUR BROWSER"
    nhentai --cookie="YOUR COMPLETE COOKIE STRING FROM nhentai.net"

**COOKIE REQUIREMENTS:**

- **For basic downloads and search**: Only ``cf_clearance`` and ``useragent`` are needed
- **For accessing favorites**: You need ALL cookies: ``cf_clearance``, ``sessionid``, ``csrftoken``, and ``session-affinity``

The complete cookie format is:

.. code-block::

    "cf_clearance=VALUE;sessionid=VALUE;csrftoken=VALUE;session-affinity=VALUE"

**How to get ALL cookies:**

**Method 1: Storage/Application Tab (Recommended)**

1. Login to nhentai.net in your browser
2. Open Developer Tools (F12)
3. Go to Storage/Application tab:

   - **Firefox**: Storage tab → Cookies → https://nhentai.net
   - **Chrome**: Application tab → Storage → Cookies → https://nhentai.net

4. Copy ALL cookie values and format as: ``"cf_clearance=VALUE;sessionid=VALUE;csrftoken=VALUE;session-affinity=VALUE"``
5. Set it with: ``nhentai --cookie="YOUR_COOKIES_HERE"``

**Method 2: Network Tab (Alternative)**

1. Open Developer Tools (F12) → Network tab
2. Refresh the page (F5)
3. Click on the **main page request** (the first one to nhentai.net, NOT image requests)
4. Find the **Cookie** header in Request Headers
5. Copy the ENTIRE cookie value

**Note**: Image requests (to t4.nhentai.net, i1.nhentai.net, etc.) only show ``cf_clearance``. You need to check requests to the main nhentai.net domain or use the Storage tab.

See ``COOKIE_GUIDE.md`` for detailed instructions.


.. |hv| unicode:: U+2630 .. https://www.compart.com/en/unicode/U+2630
.. |ve| unicode:: U+22EE .. https://www.compart.com/en/unicode/U+22EE
.. |ld| unicode:: U+2014 .. https://www.compart.com/en/unicode/U+2014

.. image:: https://github.com/RicterZ/nhentai/raw/master/images/usage.png
    :alt: nhentai
    :align: center

*The default download folder will be the path where you run the command (%cd% or $PWD).*

Download specified doujinshi:

.. code-block:: bash

    nhentai --id 123855 123866 123877

Download doujinshi with ids specified in a file (doujinshi ids split by line):

.. code-block:: bash

    nhentai --file=doujinshi.txt

Set search default language

.. code-block:: bash

    nhentai --language=english

Search a keyword and download the first page:

.. code-block:: bash

    nhentai --search="tomori" --page=1 --download
    # you also can download by tags and multiple keywords
    nhentai --search="tag:lolicon, artist:henreader, tag:full color"
    nhentai --search="lolicon, henreader, full color"

Download your favorites with delay:

.. code-block:: bash

    nhentai --favorites --download --delay 1 --page 3-5,7

Format output doujinshi folder name:

.. code-block:: bash

    nhentai --id 261100 --format '[%i]%s'
    # for Windows
    nhentai --id 261100 --format "[%%i]%%s"

Supported doujinshi folder formatter:

- %i: Doujinshi id
- %f: Doujinshi favorite count
- %t: Doujinshi name
- %s: Doujinshi subtitle (translated name)
- %a: Doujinshi authors' name
- %g: Doujinshi groups name
- %p: Doujinshi pretty name
- %ag: Doujinshi authors name or groups name

Note: for Windows operation system, please use double "%", such as "%%i".

Other options:

.. code-block::

    Usage:
      nhentai --search [keyword] --download
      NHENTAI=https://nhentai-mirror-url/ nhentai --id [ID ...]
      nhentai --file [filename]

    Environment Variable:
      NHENTAI                 nhentai mirror url

    Options:
      -h, --help            show this help message and exit
      -D, --download        download doujinshi (for search results)
      -S, --show            just show the doujinshi information
      --id                  doujinshi ids set, e.g. 167680 167681 167682
      -s KEYWORD, --search=KEYWORD
                            search doujinshi by keyword
      -F, --favorites       list or download your favorites
      -a ARTIST, --artist=ARTIST
                            list doujinshi by artist name
      --page-all            all search results
      --page=PAGE, --page-range=PAGE
                            page number of search results. e.g. 1,2-5,14
      --sorting=SORTING, --sort=SORTING
                            sorting of doujinshi (recent / popular /
                            popular-[today|week])
      -o OUTPUT_DIR, --output=OUTPUT_DIR
                            output dir
      -t THREADS, --threads=THREADS
                            thread count for downloading doujinshi
      -T TIMEOUT, --timeout=TIMEOUT
                            timeout for downloading doujinshi
      -d DELAY, --delay=DELAY
                            slow down between downloading every doujinshi
      --retry=RETRY         retry times when downloading failed
      --exit-on-fail        exit on fail to prevent generating incomplete files
      --proxy=PROXY         store a proxy, for example: -p "http://127.0.0.1:1080"
      -f FILE, --file=FILE  read gallery IDs from file.
      --format=NAME_FORMAT  format the saved folder name
      --dry-run             Dry run, skip file download
      --html                generate a html viewer at current directory
      --no-html             don't generate HTML after downloading
      --gen-main            generate a main viewer contain all the doujin in the
                            folder
      -C, --cbz             generate Comic Book CBZ File
      -P, --pdf             generate PDF file
      --rm-origin-dir       remove downloaded doujinshi dir when generated CBZ or
                            PDF file
      --move-to-folder      remove files in doujinshi dir then move new file to
                            folder when generated CBZ or PDF file
      --meta                generate a metadata file in doujinshi format
      --regenerate          regenerate the cbz or pdf file if exists
      --cookie=COOKIE       set cookie of nhentai to bypass Cloudflare captcha
      --useragent=USERAGENT, --user-agent=USERAGENT
                            set useragent to bypass Cloudflare captcha
      --language=LANGUAGE   set default language to parse doujinshis
      --clean-language      set DEFAULT as language to parse doujinshis
      --save-download-history
                            save downloaded doujinshis, whose will be skipped if
                            you re-download them
      --clean-download-history
                            clean download history
      --template=VIEWER_TEMPLATE
                            set viewer template
      --legacy              use legacy searching method

==============
nHentai Mirror
==============
If you want to use a mirror, you should set up a reverse proxy of `nhentai.net` and `i.nhentai.net`.
For example:

.. code-block::

    i.h.loli.club -> i.nhentai.net
    i3.h.loli.club -> i3.nhentai.net
    i5.h.loli.club -> i5.nhentai.net
    i7.h.loli.club -> i7.nhentai.net
    h.loli.club -> nhentai.net

Set `NHENTAI` env var to your nhentai mirror.

.. code-block:: bash

    NHENTAI=https://h.loli.club nhentai --id 123456


.. image:: https://github.com/RicterZ/nhentai/raw/master/images/search.png
    :alt: nhentai
    :align: center
.. image:: https://github.com/RicterZ/nhentai/raw/master/images/download.png
    :alt: nhentai
    :align: center
.. image:: https://github.com/RicterZ/nhentai/raw/master/images/viewer.png
    :alt: nhentai
    :align: center


.. |travis| image:: https://travis-ci.org/RicterZ/nhentai.svg?branch=master
   :target: https://travis-ci.org/RicterZ/nhentai

.. |pypi| image:: https://img.shields.io/pypi/dm/nhentai.svg
   :target: https://pypi.org/project/nhentai/

.. |version| image:: https://img.shields.io/pypi/v/nhentai
   :target: https://pypi.org/project/nhentai/

.. |license| image:: https://img.shields.io/github/license/ricterz/nhentai.svg
   :target: https://github.com/RicterZ/nhentai/blob/master/LICENSE

.. |python| image:: https://img.shields.io/badge/python-3.9+-blue.svg
   :target: https://www.python.org/downloads/

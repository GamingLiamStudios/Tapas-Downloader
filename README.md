# Tapas Downloader

Based off [TilCreator&#39;s Project](https://github.com/TilCreator/Tapas-Comic-Downloader), a simple Tapas.io downloader to use in these dark times. Easily save your favorite series.

This program will not work for series you have not paid for. All outputs of this program are intended for personal use only.

## Usage

Only dependencies for this is Python and UV.

Simply run `uv run downloader.py [series-ids]` in the project root.

```
usage: downloader.py [-h] [-f] [-c [PATH]] [-o [PATH]] [-t] [-d DELAY] URL/name [URL/name ...]

Downloads Comics/Novels from 'https://tapas.io'.
If folder of downloaded comic is found, it will only update (can be disabled with -f/--force).

positional arguments:
  URL/name              URL or URL name to comic
                        Go to the comic you want to download (any page)
                        Rightclick on the comic name in the upper left corner and select "Copy linkaddress" (Or similar) or just use the name behind series in the url
                        Examples: https://tapas.io/series/Erma, RavenWolf, ...

options:
  -h, --help            show this help message and exit
  -f, --force           Disables updater.
  -c, --cookies [PATH]  Optional cookies.txt file to load, can be used to allow the script to "log in" and pass age verification.
  -o, --output-dir [PATH]
                        Output directory where comics should be placed.
                        If left blank, the script folder will be used.
  -t, --trim            Trim final panel in Episodes (Typically Tapas notice).
  -d, --delay DELAY     Time (in ms) that should be awaited after every image fetch (for rate-limiting purposes).
```

import os
from time import sleep
from tqdm.contrib import tenumerate
import tqdm
import tempfile

import cbz
import ebooklib
from ebooklib import epub

from pyquery import PyQuery as pq

import argparse
import re
import requests
import http.cookiejar

# parse input and settup help
parser = argparse.ArgumentParser(description='Downloads Comics from \'https://tapas.io\'.\nIf folder of downloaded comic is found, it will only update (can be disabled with -f/--force).', formatter_class=argparse.RawTextHelpFormatter)
parser.add_argument('url', metavar='URL/name', type=str, nargs='+',
                    help='URL or URL name to comic\nGo to the comic you want to download (any page)\nRightclick on the comic name in the upper left corner and select "Copy linkaddress" (Or similar) or just use the name behind series in the url\nExamples: https://tapas.io/series/Erma, RavenWolf, ...')
parser.add_argument('-f', '--force', action="store_true", help='Disables updater.')
parser.add_argument('-c', '--cookies', type=str, nargs='?', default="", dest='cookies', metavar='PATH',
                    help='Optional cookies.txt file to load, can be used to allow the script to "log in" and circumvent age verification.')
parser.add_argument('-o', '--output-dir', type=str, nargs='?', default="", dest='baseDir', metavar='PATH',
                    help='Output directory where comics should be placed.\nIf left blank, the script folder will be used.')
parser.add_argument('-t', '--trim', action="store_true",
                    help='Trim final panel in Episodes (Typically Tapas notice).')
parser.add_argument('-d', '--delay', default=800, help="Time (in ms) that should be awaited after every image fetch (for rate-limiting purposes).")

args = parser.parse_args()

s = requests.Session()
s.headers.update({'user-agent': 'tapas-dl'})
if args.cookies:
    s.cookies = http.cookiejar.MozillaCookieJar()
    s.cookies.load(args.cookies, ignore_discard=True, ignore_expires=True)
# FIXME Those cookies should be set, but no idea how...
#s.cookies.update({'birthDate': '1901-01-01'})
#s.cookies.update({'adjustedBirthDate': '1901-01-01'})

base_path = ""
if args.baseDir:
    base_path = args.baseDir

for urlCount, url in enumerate(args.url):
    # check url/name
    if re.match(r'^https://tapas\.io/series/.+$', url):
        url_name = url[url.rindex('/') + 1:]
    else:
        url_name = url

    print(f"Loading {url_name}...")

    # Grab series info
    series_info = s.get(f"https://tapas.io/series/{url_name}", headers={'Accept': 'application/json'}).json()
    if series_info['code'] != 200:
        print(f"Series '{url_name}' not found. Skipping")
        continue

    series_id = series_info['data']['id']
    series_name = series_info['data']['url']
    series_title = series_info['data']['title']
    series_title_escaped = series_info['data']['escape_title']
    series_genre = series_info['data']['genre']['name']

    series_is_book = series_info['data']['book'] and not series_info['data']['comic']

    # Download cover & fetch other series info
    info_page = pq(s.get(f"https://tapas.io/series/{series_name}/info").content)

    series_authors = []
    for author in info_page('.creator-section .creator-info a.name').items():
        series_authors.append(author.text())

    series_cover_url = info_page('.thumb.js-thumbnail > img').attr('src').replace("_z.jpg", ".jpg") # _z postfix returns lower resolution image

    series_about_blob = info_page('.description > span').html()

    data = {}
    pg_num = 1
    next_page = True

    total_episodes = 0
    while next_page:
        pg_data = s.get(f'https://tapas.io/series/{series_id}/episodes?page={pg_num}&sort=OLDEST&max_limit=20').json()['data']
        next_page = pg_data['pagination']['has_next']
        #next_page = False
        total_episodes = pg_data['pagination']['total']

        for episode in pg_data['episodes']:
            # Filter out episodes we don't have access to
            if not (episode['free'] or episode['unlocked']):
                continue

            # TODO: Add support for text entry between comic chapters (does this exist?)
            if episode['book'] and not series_is_book:
                print(f"Episode {episode['title']} is marked as 'book'. Ignoring")
                continue

            info = {
                'id': episode['id'],
                'title': episode['title'],
                'thumb_url': episode['thumb_url'],
                'date': episode['publish_date'],
            }

            if episode['has_bgm']:
                info['bgm_url'] = episode['bgm_url']
                info['bgm_title'] = episode['bgm_title']

            data[episode['scene']] = info

        pg_num += 1

    #print(data)

    ## TODO: Support novels
    #if series_is_book:
    #    print(f"Series '{series_title}' is novel. Skipping")
    #    continue

    if len(data) == 0:
        print(f"No episodes available [{total_episodes} total]. Skipping entry.")

    print(f"Grabbing {len(data)} episodes [{total_episodes} total]")

    if series_is_book:
        # TODO: Fix numbering in NAV; instead of listing every chapter in order it should list by chapter number
        # TODO: Possibly async this part

        book = epub.EpubBook()
        book.set_title(series_title)
        for author in series_authors:
            book.add_author(author)

        book.set_cover("cover.jpg", s.get(series_cover_url).content)
        book.set_identifier(series_name)

        book.toc = []
        book.spine = ['cover']

        about_chapter = epub.EpubHtml(title='about', file_name='about.xhtml')
        about_chapter.set_content(series_about_blob)

        book.add_item(about_chapter)
        book.spine += [about_chapter, 'nav']

        for ord_num, chapter in tqdm.tqdm(data.items(), desc="Downloading chapters"):
            page = pq(s.get(f"https://tapas.io/episode/{chapter['id']}").content)
            page_title = chapter['title']

            page_html = f"<h1>{page_title}</h1>"
            page_html += page('.viewer__body div.ep-epub-content').html()

            chapter_html = epub.EpubHtml(title=page_title, file_name=f"{chapter['id']}.xhtml")
            chapter_html.set_content(page_html)

            book.add_item(chapter_html)
            book.toc.append(epub.Link(href=f"{chapter['id']}.xhtml", title=page_title, uid=f"{chapter['id']}"))
            book.spine.append(chapter_html)

        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())

        style = ''
        nav_css = epub.EpubItem(uid="style_nav", file_name="style/nav.css", media_type="text/css", content=style)
        book.add_item(nav_css)

        epub.write_epub(os.path.join(base_path, f"{series_title_escaped}.epub"), book)
            
    else:
        # Create series folder
        save_path = os.path.join(base_path, series_title_escaped)
        if not os.path.exists(save_path):
            os.mkdir(save_path)
    
        # Obtain cover
        cover_path = os.path.join(save_path, "cover.jpg")
        if not os.path.exists(cover_path):
            with open(cover_path, mode='wb') as f:
                f.write(s.get(series_cover_url).content)

        # Download comic episodes
        for ord_num, episode in data.items():
            filename = f"{ord_num} - {episode['title']}"
            filepath = os.path.join(save_path, f"{filename}.cbz")
            if os.path.exists(filepath) and not args.force:
                print(f"Skipping '{filename}' as already exists")
                continue

            # Download images and store as cbz
            episode_page = pq(s.get(f"https://tapas.io/episode/{episode['id']}").content)
            images = episode_page("img.content__img.js-lazy")

            pages = []
            for image_num, image in tenumerate(images.items(), desc=f"Downloading '{filename}'", total=len(images)):
                image_url = image.attr("data-src")
                image_data = s.get(image_url).content
                pages.append(cbz.PageInfo.loads(image_data, type=cbz.PageType.STORY))
                sleep(args.delay / 1000)

            if args.trim:
                pages.pop()

            episode = cbz.ComicInfo.from_pages(
                pages,
                title=episode['title'],
                series=series_title,
                number=ord_num,
                format=cbz.Format.WEB_COMIC,
                black_white=cbz.YesNo.NO,
                manga=cbz.YesNo.NO,
                publisher="Tapas",
                released=episode['date']
            )

            episode.save(filepath)
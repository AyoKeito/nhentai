# coding: utf-8
import json
import os

from nhentai.constant import PATH_SEPARATOR, LANGUAGE_ISO
from xml.sax.saxutils import escape
from requests.structures import CaseInsensitiveDict


def serialize_json(doujinshi, output_dir: str):
    metadata = {'title': doujinshi.name,
                'subtitle': doujinshi.info.subtitle}
    if doujinshi.info.favorite_counts:
        metadata['favorite_counts'] = doujinshi.favorite_counts
    if doujinshi.info.date:
        metadata['upload_date'] = doujinshi.info.date
    if doujinshi.info.parodies:
        metadata['parody'] = [i.strip() for i in doujinshi.info.parodies.split(',')]
    if doujinshi.info.characters:
        metadata['character'] = [i.strip() for i in doujinshi.info.characters.split(',')]
    if doujinshi.info.tags:
        metadata['tag'] = [i.strip() for i in doujinshi.info.tags.split(',')]
    if doujinshi.info.artists:
        metadata['artist'] = [i.strip() for i in doujinshi.info.artists.split(',')]
    if doujinshi.info.groups:
        metadata['group'] = [i.strip() for i in doujinshi.info.groups.split(',')]
    if doujinshi.info.languages:
        metadata['language'] = [i.strip() for i in doujinshi.info.languages.split(',')]
    metadata['category'] = [i.strip() for i in doujinshi.info.categories.split(',')]
    metadata['URL'] = doujinshi.url
    metadata['Pages'] = doujinshi.pages

    with open(os.path.join(output_dir, 'metadata.json'), 'w') as f:
        json.dump(metadata, f, separators=(',', ':'))


def serialize_comic_xml(doujinshi, output_dir):
    from iso8601 import parse_date
    with open(os.path.join(output_dir, 'ComicInfo.xml'), 'w', encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="utf-8"?>\n')
        f.write('<ComicInfo xmlns:xsd="http://www.w3.org/2001/XMLSchema" '
                'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">\n')

        xml_write_simple_tag(f, 'Manga', 'Yes')

        xml_write_simple_tag(f, 'Title', doujinshi.name)
        xml_write_simple_tag(f, 'Summary', doujinshi.info.subtitle)
        xml_write_simple_tag(f, 'PageCount', doujinshi.pages)
        xml_write_simple_tag(f, 'URL', doujinshi.url)
        xml_write_simple_tag(f, 'NhentaiId', doujinshi.id)
        xml_write_simple_tag(f, 'Favorites', doujinshi.favorite_counts)
        xml_write_simple_tag(f, 'Genre', doujinshi.info.categories)

        xml_write_simple_tag(f, 'BlackAndWhite', 'No' if doujinshi.info.tags and
                             'full color' in doujinshi.info.tags else 'Yes')

        if doujinshi.info.date:
            dt = parse_date(doujinshi.info.date)
            xml_write_simple_tag(f, 'Year', dt.year)
            xml_write_simple_tag(f, 'Month', dt.month)
            xml_write_simple_tag(f, 'Day', dt.day)
        if doujinshi.info.parodies:
            xml_write_simple_tag(f, 'Series', doujinshi.info.parodies)
        if doujinshi.info.groups:
            xml_write_simple_tag(f, 'Groups', doujinshi.info.groups)
        if doujinshi.info.characters:
            xml_write_simple_tag(f, 'Characters', doujinshi.info.characters)
        if doujinshi.info.tags:
            xml_write_simple_tag(f, 'Tags', doujinshi.info.tags)
        if doujinshi.info.artists:
            xml_write_simple_tag(f, 'Writer', ' & '.join([i.strip() for i in
                                                          doujinshi.info.artists.split(',')]))

        if doujinshi.info.languages:
            languages = [i.strip() for i in doujinshi.info.languages.split(',')]
            xml_write_simple_tag(f, 'Translated', 'Yes' if 'translated' in languages else 'No')
            [xml_write_simple_tag(f, 'LanguageISO', LANGUAGE_ISO[i]) for i in languages
             if (i != 'translated' and i in LANGUAGE_ISO)]

        f.write('</ComicInfo>')


def serialize_info_txt(doujinshi, output_dir: str):
    info_txt_path = os.path.join(output_dir, 'info.txt')

    fields = ['TITLE', 'ORIGINAL TITLE', 'AUTHOR', 'ARTIST', 'GROUPS', 'CIRCLE', 'SCANLATOR',
              'TRANSLATOR', 'PUBLISHER', 'DESCRIPTION', 'STATUS', 'CHAPTERS', 'PAGES',
              'TAGS',  'FAVORITE COUNTS', 'TYPE', 'LANGUAGE', 'RELEASED', 'READING DIRECTION', 'CHARACTERS',
              'SERIES', 'PARODY', 'URL']

    temp_dict = CaseInsensitiveDict(dict(doujinshi.table))

    with open(info_txt_path, 'w', encoding='utf-8') as f:
        for i in fields:
            v = temp_dict.get(i)
            v = temp_dict.get(f'{i}s') if v is None else v
            v = doujinshi.info.get(i.lower(), None) if v is None else v
            v = doujinshi.info.get(f'{i.lower()}s', "Unknown") if v is None else v
            f.write(f'{i}: {v}\n')


def xml_write_simple_tag(f, name, val, indent=1):
    f.write(f'{" "*indent}<{name}>{escape(str(val))}</{name}>\n')


def merge_json():
    lst = []
    output_dir = f".{PATH_SEPARATOR}"
    # Use absolute path instead of changing working directory
    abs_output = os.path.abspath(output_dir)
    doujinshi_dirs = next(os.walk(abs_output))[1]
    for folder in doujinshi_dirs:
        folder_path = os.path.join(abs_output, folder)
        files = os.listdir(folder_path)
        if 'metadata.json' not in files:
            continue
        data_folder = os.path.join(abs_output, folder, 'metadata.json')
        try:
            with open(data_folder, 'r') as json_file:
                json_dict = json.load(json_file)
                json_dict['Folder'] = folder
                lst.append(json_dict)
        except (IOError, json.JSONDecodeError) as e:
            # Silently skip if file can't be read
            continue
    return lst


def serialize_unique(lst):
    dictionary = {}
    parody = []
    character = []
    tag = []
    artist = []
    group = []
    for dic in lst:
        if 'parody' in dic:
            parody.extend([i for i in dic['parody']])
        if 'character' in dic:
            character.extend([i for i in dic['character']])
        if 'tag' in dic:
            tag.extend([i for i in dic['tag']])
        if 'artist' in dic:
            artist.extend([i for i in dic['artist']])
        if 'group' in dic:
            group.extend([i for i in dic['group']])
    dictionary['parody'] = list(set(parody))
    dictionary['character'] = list(set(character))
    dictionary['tag'] = list(set(tag))
    dictionary['artist'] = list(set(artist))
    dictionary['group'] = list(set(group))
    return dictionary


def set_js_database():
    with open('data.js', 'w') as f:
        indexed_json = merge_json()
        unique_json = json.dumps(serialize_unique(indexed_json), separators=(',', ':'))
        indexed_json = json.dumps(indexed_json, separators=(',', ':'))
        f.write('var data = ' + indexed_json)
        f.write(';\nvar tags = ' + unique_json)


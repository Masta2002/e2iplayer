
import os
import urllib.parse
from urllib.request import urlopen

from .model import M3U8, Playlist
from .parser import parse, is_url

__all__ = 'M3U8', 'Playlist', 'loads', 'load', 'parse'


def _dir_base_uri(uri):
    '''
    Directory the playlist lives in, with a trailing slash, so relative
    child URIs resolve with a plain urljoin(). Query string is dropped.
    '''
    return urllib.parse.urljoin(uri, '.')


def inits(content, uri):
    '''
    Given a string with a m3u8 content and uri from which
    this content was downloaded returns a M3U8 object.
    Raises ValueError if invalid content
    '''
    base_uri = _dir_base_uri(uri) if uri else None
    return M3U8(content, base_uri=base_uri)


def loads(content):
    '''
    Given a string with a m3u8 content, returns a M3U8 object.
    Raises ValueError if invalid content
    '''
    return M3U8(content)


def load(uri):
    '''
    Retrieves the content from a given URI and returns a M3U8 object.
    Raises ValueError if invalid content or IOError if request fails.
    '''
    if is_url(uri):
        return _load_from_uri(uri)
    else:
        return _load_from_file(uri)


def _load_from_uri(uri):
    open = urlopen(uri)
    uri = open.geturl()
    content = open.read().strip()
    return M3U8(content, base_uri=_dir_base_uri(uri))


def _load_from_file(uri):
    with open(uri) as fileobj:
        raw_content = fileobj.read().strip()
    base_uri = os.path.dirname(uri)
    return M3U8(raw_content, base_uri=base_uri)

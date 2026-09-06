
from collections import namedtuple
import os
import errno
import math
import urllib.parse
import re

from . import parser


class M3U8(object):
    '''
    Represents a single M3U8 playlist. Should be instantiated with
    the content as string.

    Parameters:

     `content`
       the m3u8 content as string

     `base_path`
       all urls (key and segments url) will be updated with this base_path,
       ex.:
           base_path = "http://videoserver.com/hls"

            /foo/bar/key.bin           -->  http://videoserver.com/hls/key.bin
            http://vid.com/segment1.ts -->  http://videoserver.com/hls/segment1.ts

       can be passed as parameter or setted as an attribute to ``M3U8`` object.
     `base_uri`
      uri the playlist comes from. it is propagated to SegmentList and Key
      ex.: http://example.com/path/to

    Attributes:

     `key`
       it's a `Key` object, the EXT-X-KEY from m3u8. Or None

     `segments`
       a `SegmentList` object, represents the list of `Segment`s from this playlist

     `is_variant`
        Returns true if this M3U8 is a variant playlist, with links to
        other M3U8s with different bitrates.

        If true, `playlists` if a list of the playlists available.

     `is_endlist`
        Returns true if EXT-X-ENDLIST tag present in M3U8.
        http://tools.ietf.org/html/draft-pantos-http-live-streaming-07#section-3.3.8

      `playlists`
        If this is a variant playlist (`is_variant` is True), returns a list of
        Playlist objects

      `target_duration`
        Returns the EXT-X-TARGETDURATION as an integer
        http://tools.ietf.org/html/draft-pantos-http-live-streaming-07#section-3.3.2

      `media_sequence`
        Returns the EXT-X-MEDIA-SEQUENCE as an integer
        http://tools.ietf.org/html/draft-pantos-http-live-streaming-07#section-3.3.3

      `version`
        Return the EXT-X-VERSION as is

      `allow_cache`
        Return the EXT-X-ALLOW-CACHE as is

      `files`
        Returns an iterable with all files from playlist, in order. This includes
        segments and key uri, if present.

      `base_uri`
        It is a property (getter and setter) used by
        SegmentList and Key to have absolute URIs.

    '''

    simple_attributes = (
        # obj attribute      # parser attribute
        ('is_variant', 'is_variant'),
        ('is_endlist', 'is_endlist'),
        ('target_duration', 'targetduration'),
        ('media_sequence', 'media_sequence'),
        ('version', 'version'),
        ('allow_cache', 'allow_cache'),
        )

    def __init__(self, content=None, base_path=None, base_uri=None):
        if content is not None:
            self.data = parser.parse(content)
        else:
            self.data = {}
        self._base_uri = base_uri
        self._initialize_attributes()
        self.base_path = base_path

    def _initialize_attributes(self):
        self.key = Key(base_uri=self.base_uri, **self.data['key']) if 'key' in self.data else None
        self.segments = SegmentList([Segment(base_uri=self.base_uri, **params)
                                      for params in self.data.get('segments', [])])

        for attr, param in self.simple_attributes:
            setattr(self, attr, self.data.get(param))

        self.files = []
        if self.key:
            self.files.append(self.key.uri)
        self.files.extend(self.segments.uri)

        self.playlists = PlaylistList([Playlist(base_uri=self.base_uri, **playlist)
                                        for playlist in self.data.get('playlists', [])])

    def __unicode__(self):
        return self.dumps()

    @property
    def base_uri(self):
        return self._base_uri

    @base_uri.setter
    def base_uri(self, new_base_uri):
        self._base_uri = new_base_uri
        self.segments.base_uri = new_base_uri

    @property
    def base_path(self):
        return self._base_path

    @base_path.setter
    def base_path(self, newbase_path):
        self._base_path = newbase_path
        self._update_base_path()

    def _update_base_path(self):
        if self._base_path is None:
            return
        if self.key:
            self.key.base_path = self.base_path
        self.segments.base_path = self.base_path
        self.playlists.base_path = self.base_path

    def add_playlist(self, playlist):
        self.is_variant = True
        self.playlists.append(playlist)

    def dumps(self):
        '''
        Returns the current m3u8 as a string.
        You could also use unicode(<this obj>) or str(<this obj>)
        '''
        output = ['#EXTM3U']
        if self.media_sequence:
            output.append('#EXT-X-MEDIA-SEQUENCE:' + str(self.media_sequence))
        if self.allow_cache:
            output.append('#EXT-X-ALLOW-CACHE:' + self.allow_cache.upper())
        if self.version:
            output.append('#EXT-X-VERSION:' + self.version)
        if self.key:
            output.append(str(self.key))
        if self.target_duration:
            output.append('#EXT-X-TARGETDURATION:' + int_or_float_to_string(self.target_duration))
        if self.is_variant:
            output.append(str(self.playlists))

        output.append(str(self.segments))

        if self.is_endlist:
            output.append('#EXT-X-ENDLIST')

        return '\n'.join(output)

    def dump(self, filename):
        '''
        Saves the current m3u8 to ``filename``
        '''
        self._create_sub_directories(filename)

        with open(filename, 'w') as fileobj:
            fileobj.write(self.dumps())

    def _create_sub_directories(self, filename):
        basename = os.path.dirname(filename)
        try:
            os.makedirs(basename)
        except OSError as error:
            if error.errno != errno.EEXIST:
                raise


class BasePathMixin(object):

    @property
    def absolute_uri(self):
        if self.uri is None:
            return None
        if parser.is_url(self.uri):
            uri = self.uri
        else:
            if self.base_uri is None:
                raise ValueError('There can not be `absolute_uri` with no `base_uri` set')
            # Plain RFC 3986 join. `base_uri` is expected to carry a trailing
            # slash (see `M3U8` / `inits`), so a relative playlist/segment path
            # resolves against the playlist directory. Unlike the old
            # os.path.normpath() approach this keeps query strings intact even
            # when a signed token contains slashes (e.g. `?hdnts=...~acl=/*~`).
            uri = urllib.parse.urljoin(self.base_uri, self.uri)

        # BBC web-proxy passthrough (config.plugins.iptvplayer.bbc_use_web_proxy):
        # if the playlist was fetched through the proxy, keep its children on it.
        proxyUri = 'englandproxy.co.uk'
        if self.base_uri and proxyUri in self.base_uri and proxyUri not in uri:
            try:
                uri = 'http://www.englandproxy.co.uk/' + uri[uri.find('://') + 3:]
            except Exception:
                pass
        return uri

    @property
    def base_path(self):
        return os.path.dirname(self.uri)

    @base_path.setter
    def base_path(self, newbase_path):
        if not self.base_path:
            self.uri = "%s/%s" % (newbase_path, self.uri)
        self.uri = self.uri.replace(self.base_path, newbase_path)


class GroupedBasePathMixin(object):

    def _set_base_uri(self, new_base_uri):
        for item in self:
            item.base_uri = new_base_uri

    base_uri = property(None, _set_base_uri)

    def _set_base_path(self, newbase_path):
        for item in self:
            item.base_path = newbase_path

    base_path = property(None, _set_base_path)


class Segment(BasePathMixin):
    '''
    A video segment from a M3U8 playlist

    `uri`
      a string with the segment uri

    `title`
      title attribute from EXTINF parameter

    `duration`
      duration attribute from EXTINF paramter

    `date`
      program date from EXT-X-PROGRAM-DATE-TIME paramter

    `base_uri`
      uri the key comes from in URI hierarchy. ex.: http://example.com/path/to
    '''

    def __init__(self, uri, base_uri, duration=None, title=None, program_date_time=None):
        self.uri = uri
        self.program_date_time = program_date_time
        self.duration = duration
        self.title = title
        self.base_uri = base_uri

    def __str__(self):
        output = ['#EXTINF:%s,' % int_or_float_to_string(self.duration)]
        if self.title:
            output.append(quoted(self.title))
        if self.program_date_time:
            output.extend(['\n#EXT-X-PROGRAM-DATE-TIME:%s' % self.program_date_time])

        output.append('\n')
        output.append(self.uri)

        return ''.join(output)


class SegmentList(list, GroupedBasePathMixin):

    def __str__(self):
        output = [str(segment) for segment in self]
        return '\n'.join(output)

    @property
    def uri(self):
        return [seg.uri for seg in self]


class Key(BasePathMixin):
    '''
    Key used to encrypt the segments in a m3u8 playlist (EXT-X-KEY)

    `method`
      is a string. ex.: "AES-128"

    `uri`
      is a string. ex:: "https://priv.example.com/key.php?r=52"

    `base_uri`
      uri the key comes from in URI hierarchy. ex.: http://example.com/path/to

    `iv`
      initialization vector. a string representing a hexadecimal number. ex.: 0X12A

    '''

    def __init__(self, method=None, uri=None, base_uri=None, iv=None, **kwargs):
        self.method = method
        self.uri = uri
        self.iv = iv
        self.base_uri = base_uri
        # KEYFORMAT / KEYFORMATVERSIONS and other modern EXT-X-KEY attributes
        # are kept but not acted on - swallowing them here keeps a media
        # playlist with e.g. Widevine/FairPlay keys from aborting the parse.
        self.extra_params = kwargs

    def __str__(self):
        output = [
            'METHOD=%s' % self.method,
            'URI="%s"' % self.uri,
            ]
        if self.iv:
            output.append('IV=%s' % self.iv)

        return '#EXT-X-KEY:' + ','.join(output)


class AudioStream(BasePathMixin):
    def __init__(self, uri, name, language, base_uri, channels=None, characteristics=None, default=None, forced=None):

        self.uri = uri
        self.base_uri = base_uri
        self.language = language
        self.name = name
        self.channels = channels
        self.characteristics = characteristics
        self.default = (default == 'YES')
        self.forced = (forced == 'YES')

    def __str__(self):
        # ToDO
        return ''


class SubtitleStream(BasePathMixin):
    '''
    An alternate SUBTITLES rendition referenced from a variant playlist
    (EXT-X-MEDIA:TYPE=SUBTITLES). `uri` points to the WebVTT media playlist.
    '''

    def __init__(self, uri, name, language, base_uri, forced=None, default=None, characteristics=None):

        self.uri = uri
        self.base_uri = base_uri
        self.language = language
        self.name = name
        self.characteristics = characteristics
        self.forced = (forced == 'YES')
        self.default = (default == 'YES')

    def __str__(self):
        return ''


class Playlist(BasePathMixin):
    '''
    Playlist object representing a link to a variant M3U8 with a specific bitrate.
    Each `stream_info` attribute has: `program_id`, `bandwidth`, `resolution` and `codecs`
    `resolution` is a tuple (h, v) of integers

    More info: http://tools.ietf.org/html/draft-pantos-http-live-streaming-07#section-3.3.10
    '''

    def __init__(self, uri, stream_info, alt_audio_streams=None, subtitle_streams=None, base_uri=None):

        self.uri = uri
        self.base_uri = base_uri

        resolution = stream_info.get('resolution')
        if resolution is not None:
            try:
                values = str(resolution).replace('"', '').split('x')
                resolution_pair = (int(values[0]), int(values[1]))
            except Exception:
                resolution_pair = None
        else:
            resolution_pair = None

        self.stream_info = StreamInfo(bandwidth=stream_info.get('bandwidth'),
                                      average_bandwidth=stream_info.get('average_bandwidth'),
                                      program_id=stream_info.get('program_id'),
                                      resolution=resolution_pair,
                                      codecs=stream_info.get('codecs'),
                                      frame_rate=stream_info.get('frame_rate'),
                                      video_range=stream_info.get('video_range'),
                                      audio=stream_info.get('audio'),
                                      subtitles=stream_info.get('subtitles'))
        self.alt_audio_streams = [AudioStream(base_uri=self.base_uri, uri=s.get('uri'), name=s.get('name'), language=s.get('language'),
                                              channels=s.get('channels'), characteristics=s.get('characteristics'),
                                              default=s.get('default'), forced=s.get('forced'))
                                    for s in (alt_audio_streams or [])]
        self.subtitle_streams = [SubtitleStream(base_uri=self.base_uri, uri=s.get('uri'), name=s.get('name'), language=s.get('language'),
                                                forced=s.get('forced'), default=s.get('default'), characteristics=s.get('characteristics'))
                                    for s in (subtitle_streams or [])]

    def __str__(self):
        stream_inf = []
        if self.stream_info.program_id:
            stream_inf.append('PROGRAM-ID=' + str(self.stream_info.program_id))
        if self.stream_info.bandwidth:
            stream_inf.append('BANDWIDTH=' + str(self.stream_info.bandwidth))
        if self.stream_info.resolution:
            res = str(self.stream_info.resolution[0]) + 'x' + str(self.stream_info.resolution[1])
            stream_inf.append('RESOLUTION=' + res)
        if self.stream_info.codecs:
            stream_inf.append('CODECS=' + quoted(self.stream_info.codecs))
        return '#EXT-X-STREAM-INF:' + ','.join(stream_inf) + '\n' + self.uri


StreamInfo = namedtuple('StreamInfo', ['bandwidth', 'average_bandwidth', 'program_id',
                                       'resolution', 'codecs', 'frame_rate', 'video_range',
                                       'audio', 'subtitles'])


class PlaylistList(list, GroupedBasePathMixin):

    def __str__(self):
        output = [str(playlist) for playlist in self]
        return '\n'.join(output)


def denormalize_attribute(attribute):
    return attribute.replace('_', '-').upper()


def quoted(string):
    return '"%s"' % string


def int_or_float_to_string(number):
    return str(int(number)) if number == math.floor(number) else str(number)

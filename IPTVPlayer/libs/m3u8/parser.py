'''
M3U8 parser.

'''
import re

ext_x_targetduration = '#EXT-X-TARGETDURATION'
ext_x_media_sequence = '#EXT-X-MEDIA-SEQUENCE'
ext_x_key = '#EXT-X-KEY'
ext_x_stream_inf = '#EXT-X-STREAM-INF'
ext_x_version = '#EXT-X-VERSION'
ext_x_allow_cache = '#EXT-X-ALLOW-CACHE'
ext_x_endlist = '#EXT-X-ENDLIST'
extinf = '#EXTINF'
ext_x_program_date_time = '#EXT-X-PROGRAM-DATE-TIME'
ext_x_media = '#EXT-X-MEDIA'

'''
http://tools.ietf.org/html/draft-pantos-http-live-streaming-08#section-3.2
http://stackoverflow.com/questions/2785755/how-to-split-but-ignore-separators-in-quoted-strings-in-python
'''
ATTRIBUTELISTPATTERN = re.compile(r'''((?:[^,"']|"[^"]*"|'[^']*')+)''')


def parse(content):
    '''
    Given a M3U8 playlist content returns a dictionary with all data found
    '''
    data = {
        'media_sequence': 0,
        'is_variant': False,
        'is_endlist': False,
        'playlists': [],
        'segments': [],
        'alt_media': {},
        'subtitle_media': {},
        }

    state = {
        'expect_segment': False,
        'expect_playlist': False,
        }

    for line in string_to_lines(content):
        line = line.strip()

        if line.startswith(ext_x_targetduration):
            _parse_simple_parameter(line, data, float)
        elif line.startswith(ext_x_media_sequence):
            _parse_simple_parameter(line, data, int)
        elif line.startswith(ext_x_version):
            _parse_simple_parameter(line, data)
        elif line.startswith(ext_x_allow_cache):
            _parse_simple_parameter(line, data)
        elif line.startswith(ext_x_media):
            _parse_alternate_media(line, data)
        elif line.startswith(ext_x_key):
            _parse_key(line, data)

        elif line.startswith(extinf):
            _parse_extinf(line, data, state)
            state['expect_segment'] = True

        elif line.startswith(ext_x_program_date_time):
            if state['expect_segment']:
                _parse_simple_parameter(line, state)

        elif line.startswith(ext_x_stream_inf):
            state['expect_playlist'] = True
            _parse_stream_inf(line, data, state)

        elif line.startswith(ext_x_endlist):
            data['is_endlist'] = True

        elif state['expect_segment']:
            _parse_ts_chunk(line, data, state)
            state['expect_segment'] = False

        elif state['expect_playlist']:
            _parse_variant_playlist(line, data, state)
            state['expect_playlist'] = False

    try:
        for playlist in data['playlists']:
            stream_info = playlist['stream_info']
            audio_group = stream_info.get('audio')
            if audio_group in data['alt_media']:
                playlist['alt_audio_streams'] = data['alt_media'][audio_group]
            subs_group = stream_info.get('subtitles')
            if subs_group in data['subtitle_media']:
                playlist['subtitle_streams'] = data['subtitle_media'][subs_group]
    except Exception:
        pass

    return data


def _parse_attribute_list(prefix, line, attribute_parser=None, default_parser=None):
    '''
    Parse an `NAME=VALUE,NAME=VALUE` attribute list (EXT-X-STREAM-INF,
    EXT-X-MEDIA, EXT-X-KEY ...) into a dict.

    Tolerant on purpose: a token without a `=` (bare flag or trailing comma)
    is skipped instead of blowing up the whole playlist parse, and a value
    that fails to cast is stored as None rather than raising.
    '''
    params = ATTRIBUTELISTPATTERN.split(line.replace(prefix + ':', ''))[1::2]

    attributes = {}
    for param in params:
        parts = param.split('=', 1)
        if len(parts) != 2:
            continue
        name, value = parts
        name = normalize_attribute(name)
        if attribute_parser and name in attribute_parser:
            try:
                value = attribute_parser[name](value)
            except Exception:
                value = None
        elif default_parser is not None:
            try:
                value = default_parser(value)
            except Exception:
                value = None
        attributes[name] = value

    return attributes


def _cast_bandwidth(value):
    # BANDWIDTH is spec'd as an integer, but some encoders emit floats or
    # scientific notation.
    return int(float(value))


def _parse_key(line, data):
    data['key'] = _parse_attribute_list(ext_x_key, line, default_parser=remove_quotes)


def _parse_extinf(line, data, state):
    val = line.replace(extinf + ':', '').split(',')
    if len(val) > 1:
        title = val[1]
    else:
        title = ""

    state['segment'] = {'duration': float(val[0]), 'title': remove_quotes(title)}


def _parse_ts_chunk(line, data, state):
    segment = state.pop('segment')
    segment['uri'] = line
    data['segments'].append(segment)


def _parse_stream_inf(line, data, state):
    attribute_parser = {
        'codecs': remove_quotes,
        'audio': remove_quotes,
        'video': remove_quotes,
        'subtitles': remove_quotes,
        'closed_captions': remove_quotes,
        'video_range': remove_quotes,
        'program_id': int,
        'bandwidth': _cast_bandwidth,
        'average_bandwidth': _cast_bandwidth,
        'frame_rate': float,
    }
    stream_info = _parse_attribute_list(ext_x_stream_inf, line, attribute_parser)

    data['is_variant'] = True
    state['stream_info'] = stream_info


def _parse_alternate_media(line, data):
    normalize_params = _parse_attribute_list(ext_x_media, line, default_parser=remove_quotes)

    media_type = (normalize_params.get('type') or '').upper()
    uri = normalize_params.get('uri')
    group = normalize_params.get('group_id')
    if not group:
        return

    if media_type == 'AUDIO':
        if not uri:
            return
        bucket = data['alt_media'].setdefault(group, [])
    elif media_type == 'SUBTITLES':
        if not uri:
            return
        bucket = data['subtitle_media'].setdefault(group, [])
    else:
        # CLOSED-CAPTIONS (no media playlist URI) and VIDEO renditions are
        # not consumed downstream.
        return

    if normalize_params.get('default') == 'YES':
        bucket.insert(0, normalize_params)
    else:
        bucket.append(normalize_params)


def _parse_variant_playlist(line, data, state):
    stream_info = state.pop('stream_info')
    playlist = {'uri': line,
                'stream_info': stream_info,
                'alt_audio_streams': [],
                'subtitle_streams': []}
    data['playlists'].append(playlist)


def _parse_simple_parameter(line, data, cast_to=str):
    param, value = line.split(':', 1)
    param = normalize_attribute(param.replace('#EXT-X-', ''))
    value = normalize_attribute(value)
    data[param] = cast_to(value)


def string_to_lines(string):
    return string.strip().replace('\r\n', '\n').replace('\r', '\n').split('\n')


def remove_quotes(string):
    '''
    Remove quotes from string.

    Ex.:
      "foo" -> foo
      'foo' -> foo
      'foo  -> 'foo

    '''
    quotes = ('"', "'")
    if string and string[0] in quotes and string[-1] in quotes:
        return string[1:-1]
    return string


def normalize_attribute(attribute):
    return attribute.replace('-', '_').lower().strip()


def is_url(uri):
    return re.match(r'https?://', uri) is not None

# -*- coding: utf-8 -*-
# Added: 24.10.2026 - automatic link choice of the "Select link" list
#
# "Preferred video quality": the height a link name carries ("720p", "1280x720", "4K") and the link of a
# quality list closest to the wish. "Select link automatically": the order the mirrors are tried in (the
# preferred quality first, mirrors that already failed left out). The list side lives in
# components/iptvplayerwidget.py; these functions have no enigma2 / host access (tests/test_linkpicker.py).
###################################################
# FOREIGN import
###################################################
import re
###################################################

_RE_WXH = re.compile(r'(?<!\d)\d{3,4}\s*[xX×]\s*(\d{3,4})(?!\d)')
_RE_P = re.compile(r'(?<!\d)(\d{3,4})[pPiI](?![a-zA-Z])')
_RE_4K = re.compile(r'(?<![a-zA-Z0-9])(4k|uhd)(?![a-zA-Z0-9])', re.I)
_RE_FHD = re.compile(r'(?<![a-zA-Z0-9])fhd(?![a-zA-Z0-9])', re.I)


def linkHeight(name):
    # video height a link name carries, 0 = none (or an audio only stream)
    name = name or ''
    if 'audio only' in name.lower():
        return 0
    for regex in (_RE_WXH, _RE_P):
        for match in regex.finditer(name):
            height = int(match.group(1))
            if 144 <= height <= 4320:
                return height
    if _RE_4K.search(name):
        return 2160
    if _RE_FHD.search(name):
        return 1080
    return 0


def _targetHeight(heights, preferred):
    # preferred: '' (ask), 'max' or a height as text ('720'); the highest height not above the wish,
    # the lowest one when all are above it
    heights = [h for h in heights if h > 0]
    if not heights or not preferred:
        return 0
    if preferred == 'max':
        return max(heights)
    try:
        wish = int(preferred)
    except ValueError:
        return 0
    below = [h for h in heights if h <= wish]
    return max(below) if below else min(heights)


def pickByQuality(links, preferred):
    # a list of qualities (every video link names its height): the link closest to the wish, else None
    heights = [linkHeight(link.name) for link in links]
    video = [h for link, h in zip(links, heights) if 'audio only' not in (link.name or '').lower()]
    if len(links) < 2 or not video or 0 in video:
        return None
    target = _targetHeight(heights, preferred)
    for link, height in zip(links, heights):
        if target and height == target:
            return link
    return None


def autoOrder(links, preferred, isFailed):
    # the order "Select link automatically" tries the links in: the preferred quality first, then the host's
    # order; links that failed already are left out unless all of them failed
    candidates = [link for link in links if not isFailed(link)] or list(links)
    target = _targetHeight([linkHeight(link.name) for link in candidates], preferred)
    if not target:
        return candidates
    return sorted(candidates, key=lambda link: 0 if linkHeight(link.name) == target else 1)

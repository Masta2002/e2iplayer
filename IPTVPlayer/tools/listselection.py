# -*- coding: utf-8 -*-
# Added: 10.10.2026 - list selection + playlist functions of the host list (BLUE menu)
#
# The bookkeeping behind "Shuffle / Reverse the playlist" (toggles that can be undone) and the selection mode
# (OK marks rows; play / download / add to the favourites the marked rows). The list side lives in
# components/iptvplayerwidget.py; these functions have no enigma2 / host access (tests/test_listselection.py).
# 11.10.2026: the playlist the movie player shows during a run of the sequencer (buildPlaylist: "Playlist 3/10"
# in its infobar, "Show playlist" in its MENU; an entry chosen there comes back as a ('zap_to', ...) answer).
###################################################
# FOREIGN import
###################################################
from random import shuffle as random_shuffle
###################################################

# attribute of a CDisplayListItem that is marked in the selection mode (drawn by components/iptvlist.py)
MARK_ATTR = 'selectMarked'


def isMarked(row):
    return bool(getattr(row, MARK_ATTR, False))


def setMarked(row, marked):
    setattr(row, MARK_ATTR, bool(marked))


def clearMarks(rows):
    # a host can hand the same row objects out again (a cached list): a new list starts without marks
    for row in rows:
        if isMarked(row):
            setMarked(row, False)


def newShuffleOrder(count, shuffle=random_shuffle):
    # a random order of count movable rows: positions into the movable rows of the original list
    order = list(range(count))
    shuffle(order)
    return order


def arrangeRows(original, isMovable, shuffleOrder=None, reverse=False):
    # original: the rows in the order the host gave them. The movable (playable) rows change their places
    # among each other - first shuffled (shuffleOrder, see newShuffleOrder), then reversed -, every other row
    # keeps its place. No shuffleOrder and no reverse: the original order.
    movable = [row for row in original if isMovable(row)]
    if shuffleOrder is not None and len(shuffleOrder) == len(movable):
        movable = [movable[idx] for idx in shuffleOrder]
    if reverse:
        movable.reverse()
    nextMovable = iter(movable)
    return [next(nextMovable) if isMovable(row) else row for row in original]


def removeRow(original, row, isMovable, shuffleOrder=None):
    # a row deleted from the list that the host drops from its own list as well (a removed favourite):
    # (original without the row, shuffleOrder without its place). The row leaves original in place - the list
    # is the host's own one (the favourites keep it as cachedRet for markItemAsViewed / getCurrentList), so it
    # must lose the row as well. The rows behind it in the host list move up by one, so their itemIdx (index in
    # the host list) is lowered.
    if shuffleOrder is not None and isMovable(row):
        movable = [item for item in original if isMovable(item)]
        for pos, item in enumerate(movable):
            if item is row:
                shuffleOrder = [idx - 1 if idx > pos else idx for idx in shuffleOrder if idx != pos]
                break
    for pos, item in enumerate(original):
        if item is row:
            del original[pos]
            break
    hostIdx = getattr(row, 'itemIdx', -1)
    if -1 < hostIdx:
        for item in original:
            if hostIdx < getattr(item, 'itemIdx', -1):
                item.itemIdx -= 1
    return original, shuffleOrder


def nextPlayRow(rows, start, canPlay, markedOnly=False):
    # index of the first row from start on (inclusive) the autoplay sequencer plays, -1 when there is none.
    # markedOnly ("Play marked items"): only marked rows, so the run ends after the last marked one.
    idx = max(start, 0)
    while idx < len(rows):
        row = rows[idx]
        if canPlay(row) and (not markedOnly or isMarked(row)):
            return idx
        idx += 1
    return -1


def playOrder(rows, canPlay, markedOnly=False):
    # indexes of the rows the sequencer plays, in the order it plays them (the same nextPlayRow() steps)
    order = []
    idx = nextPlayRow(rows, 0, canPlay, markedOnly)
    while -1 != idx:
        order.append(idx)
        idx = nextPlayRow(rows, idx + 1, canPlay, markedOnly)
    return order


# answer of the movie player when an entry of its playlist overlay is chosen: (ZAP_TO, row index, row key)
ZAP_TO = 'zap_to'


def buildPlaylist(rows, current, canPlay, key, markedOnly=False, shuffled=False, reverse=False, playedKeys=()):
    # what the movie player shows of a run of the sequencer (info line + playlist overlay): the rows it plays in
    # play order, the one playing now (current: its index in rows) and the ones already played in this run
    # (playedKeys: key(row) of them). None: current is not one of the rows the sequencer plays.
    order = playOrder(rows, canPlay, markedOnly)
    if current not in order:
        return None
    entries = []
    for idx in order:
        row = rows[idx]
        rowKey = key(row)
        entries.append({'title': getattr(row, 'name', ''), 'type': getattr(row, 'type', None), 'row': idx, 'key': rowKey, 'played': idx != current and rowKey in playedKeys})
    return {'entries': entries, 'current': order.index(current), 'marked_only': bool(markedOnly), 'shuffled': bool(shuffled), 'reversed': bool(reverse)}


def playlistInfoText(playlist, title, markedText, shuffledText, reversedText):
    # the line in the player's infobar, e.g. "Playlist 3/10 (marked, shuffled)"; empty without a playlist
    if not playlist or not playlist.get('entries'):
        return ''
    text = '%s %d/%d' % (title, playlist['current'] + 1, len(playlist['entries']))
    labels = []
    if playlist.get('marked_only'):
        labels.append(markedText)
    if playlist.get('shuffled'):
        labels.append(shuffledText)
    if playlist.get('reversed'):
        labels.append(reversedText)
    if labels:
        text += ' (%s)' % ', '.join(labels)
    return text


def zapToAnswer(entry):
    return (ZAP_TO, entry['row'], entry['key'])


def isZapToAnswer(answer):
    return isinstance(answer, tuple) and 3 == len(answer) and ZAP_TO == answer[0]


def findZapToRow(rows, answer, key):
    # index in rows of the row a zap_to answer names: at its index when the row there is still the same one,
    # else where the row with that key is now; -1 when it is gone
    rowIdx, rowKey = answer[1], answer[2]
    if 0 <= rowIdx < len(rows) and key(rows[rowIdx]) == rowKey:
        return rowIdx
    for idx, row in enumerate(rows):
        if key(row) == rowKey:
            return idx
    return -1


def carryMarks(oldRows, newRows, key):
    # the list was loaded again with the same rows (a refresh in the middle of a run of the sequencer): the
    # marks go over to the new rows with the same key. The key must tell the rows apart by what they are (e.g.
    # index in the host list + type + title), not only by their place - else a list of other rows with the
    # same length would take the marks. False: not the same rows, the new rows are left without marks.
    marked = set(key(row) for row in oldRows if isMarked(row))
    if len(oldRows) != len(newRows) or sorted(key(row) for row in oldRows) != sorted(key(row) for row in newRows):
        clearMarks(newRows)
        return False
    for row in newRows:
        setMarked(row, key(row) in marked)
    return True

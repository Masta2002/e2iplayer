# Offline tests for the list selection + playlist functions: IPTVPlayer/tools/listselection.py (order of the
# shuffled / reversed list and undo, marks moving with their rows, the next row of "Play marked items", marks
# kept over a refresh). The module has no enigma2 / E2iPlayer imports.
import importlib.util
import os

ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "IPTVPlayer")


def _load():
    spec = importlib.util.spec_from_file_location("listselection_under_test", os.path.join(ROOT, "tools", "listselection.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ls = _load()


class Row(object):
    def __init__(self, name, playable=True, itemIdx=-1):
        self.name = name
        self.playable = playable
        self.itemIdx = itemIdx

    def __repr__(self):
        return self.name


def _movable(row):
    return row.playable


def _names(rows):
    return [row.name for row in rows]


def _list():
    # a folder row on top and a "next page" row at the end stay where they are
    rows = [Row('folder', False), Row('a'), Row('b'), Row('c'), Row('d'), Row('next', False)]
    for idx, row in enumerate(rows):
        row.itemIdx = idx
    return rows


def _fixedShuffle(order):
    # a "random" order the tests know: d c a b -> positions 3 2 0 1
    order[:] = [3, 2, 0, 1]


def test_arrange_original_when_nothing_changed():
    rows = _list()
    assert _names(ls.arrangeRows(rows, _movable)) == _names(rows)


def test_reverse_keeps_other_rows_in_place():
    rows = _list()
    assert _names(ls.arrangeRows(rows, _movable, reverse=True)) == ['folder', 'd', 'c', 'b', 'a', 'next']


def test_reverse_all_playable_like_before():
    rows = [Row('a'), Row('b'), Row('c')]
    assert _names(ls.arrangeRows(rows, _movable, reverse=True)) == ['c', 'b', 'a']


def test_shuffle_uses_the_remembered_order():
    rows = _list()
    order = ls.newShuffleOrder(4, _fixedShuffle)
    assert order == [3, 2, 0, 1]
    assert _names(ls.arrangeRows(rows, _movable, order)) == ['folder', 'd', 'c', 'a', 'b', 'next']


def test_new_shuffle_order_is_a_permutation():
    order = ls.newShuffleOrder(10)
    assert sorted(order) == list(range(10))


def test_shuffle_and_reverse_and_undo_each():
    rows = _list()
    order = [3, 2, 0, 1]
    both = ls.arrangeRows(rows, _movable, order, reverse=True)
    assert _names(both) == ['folder', 'b', 'a', 'c', 'd', 'next']
    # undo shuffle: the original order, reversed
    assert _names(ls.arrangeRows(rows, _movable, None, reverse=True)) == ['folder', 'd', 'c', 'b', 'a', 'next']
    # undo reverse: shuffled only
    assert _names(ls.arrangeRows(rows, _movable, order, reverse=False)) == ['folder', 'd', 'c', 'a', 'b', 'next']
    # both undone: the original list
    assert _names(ls.arrangeRows(rows, _movable)) == _names(rows)


def test_shuffle_order_of_other_length_is_ignored():
    rows = _list()
    assert _names(ls.arrangeRows(rows, _movable, [1, 0])) == _names(rows)


def test_marks_move_with_their_rows():
    rows = _list()
    ls.setMarked(rows[1], True)  # a
    ls.setMarked(rows[3], True)  # c
    arranged = ls.arrangeRows(rows, _movable, reverse=True)
    assert [row.name for row in arranged if ls.isMarked(row)] == ['c', 'a']
    assert not rows[0].__dict__.get(ls.MARK_ATTR, False)


def test_next_play_row_plain_and_marked():
    rows = _list()
    canPlay = _movable
    assert ls.nextPlayRow(rows, 0, canPlay) == 1
    assert ls.nextPlayRow(rows, 2, canPlay) == 2
    assert ls.nextPlayRow(rows, 5, canPlay) == -1
    ls.setMarked(rows[2], True)  # b
    ls.setMarked(rows[4], True)  # d
    assert ls.nextPlayRow(rows, 0, canPlay, True) == 2
    assert ls.nextPlayRow(rows, 3, canPlay, True) == 4
    # after the last marked row the run ends
    assert ls.nextPlayRow(rows, 5, canPlay, True) == -1
    assert ls.nextPlayRow(rows, 6, canPlay, True) == -1


def test_next_play_row_marked_but_not_playable_is_skipped():
    rows = _list()
    ls.setMarked(rows[1], True)
    ls.setMarked(rows[3], True)
    # the first marked row can not be played (e.g. PIN not entered)
    assert ls.nextPlayRow(rows, 0, lambda row: row.name != 'a', True) == 3


def test_next_play_row_follows_the_shuffled_order():
    rows = _list()
    ls.setMarked(rows[1], True)  # a
    ls.setMarked(rows[4], True)  # d
    arranged = ls.arrangeRows(rows, _movable, reverse=True)  # folder d c b a next
    first = ls.nextPlayRow(arranged, 0, _movable, True)
    assert arranged[first].name == 'd'
    second = ls.nextPlayRow(arranged, first + 1, _movable, True)
    assert arranged[second].name == 'a'
    assert ls.nextPlayRow(arranged, second + 1, _movable, True) == -1


def test_arrange_empty_and_single_row():
    assert ls.arrangeRows([], _movable, [], reverse=True) == []
    single = [Row('a')]
    assert _names(ls.arrangeRows(single, _movable, [0], reverse=True)) == ['a']
    noneMovable = [Row('folder', False), Row('next', False)]
    assert _names(ls.arrangeRows(noneMovable, _movable, [], reverse=True)) == ['folder', 'next']


def test_arrange_does_not_change_the_original():
    rows = _list()
    ls.arrangeRows(rows, _movable, [3, 2, 0, 1], reverse=True)
    assert _names(rows) == ['folder', 'a', 'b', 'c', 'd', 'next']


def test_next_play_row_empty_list_and_negative_start():
    assert ls.nextPlayRow([], 0, _movable) == -1
    assert ls.nextPlayRow(_list(), -1, _movable) == 1


def test_carry_marks_over_a_refresh():
    old = _list()
    ls.setMarked(old[2], True)
    new = _list()
    assert ls.carryMarks(old, new, lambda row: row.itemIdx)
    assert [row.name for row in new if ls.isMarked(row)] == ['b']


def test_carry_marks_from_a_reordered_list():
    old = _list()
    ls.setMarked(old[4], True)  # d
    arranged = ls.arrangeRows(old, _movable, reverse=True)
    new = _list()
    assert ls.carryMarks(arranged, new, lambda row: row.itemIdx)
    assert [row.name for row in new if ls.isMarked(row)] == ['d']


def test_carry_marks_refused_for_other_rows():
    old = _list()
    ls.setMarked(old[1], True)
    new = _list()[:4]
    assert not ls.carryMarks(old, new, lambda row: row.itemIdx)
    assert not any(ls.isMarked(row) for row in new)


def _identity(row):
    # like E2iPlayerWidget._getRowIdentity: place in the host list + what the row is
    return (row.itemIdx, row.playable, row.name)


def test_carry_marks_refused_for_other_rows_of_the_same_length():
    # the refresh brought other rows in the same number: no mark may land on a row that was not marked
    old = _list()
    ls.setMarked(old[1], True)  # a
    new = _list()
    new[1].name = 'x'
    ls.setMarked(new[3], True)  # a stale mark on a row object handed out again
    assert not ls.carryMarks(old, new, _identity)
    assert not any(ls.isMarked(row) for row in new)


def test_carry_marks_with_identity_key():
    old = _list()
    ls.setMarked(old[2], True)  # b
    new = _list()
    assert ls.carryMarks(old, new, _identity)
    assert [row.name for row in new if ls.isMarked(row)] == ['b']


def test_carry_marks_onto_the_same_row_objects():
    # a host that returns its cached rows: old and new are the same objects
    rows = _list()
    ls.setMarked(rows[4], True)  # d
    assert ls.carryMarks(rows, list(rows), _identity)
    assert [row.name for row in rows if ls.isMarked(row)] == ['d']


def test_clear_marks():
    rows = _list()
    ls.setMarked(rows[1], True)
    ls.setMarked(rows[3], True)
    ls.clearMarks(rows)
    assert not any(ls.isMarked(row) for row in rows)


def test_remove_row_from_the_original_order():
    rows = _list()
    remaining, order = ls.removeRow(rows, rows[2], _movable)  # b
    assert _names(remaining) == ['folder', 'a', 'c', 'd', 'next']
    assert order is None
    # the rows behind it in the host list move up by one
    assert [row.itemIdx for row in remaining] == [0, 1, 2, 3, 4]


def test_remove_row_from_the_hosts_own_list_in_place():
    # the list is the host's own one (the favourites keep it as cachedRet): it loses the row as well, so a later
    # markItemAsViewed(itemIdx) of a row behind it finds that row at that index
    rows = _list()
    hostList = rows
    remaining, order = ls.removeRow(rows, rows[2], _movable, [3, 2, 0, 1])  # b
    assert remaining is hostList
    assert _names(hostList) == ['folder', 'a', 'c', 'd', 'next']
    assert order == [2, 1, 0]
    assert all(hostList[row.itemIdx] is row for row in hostList)


def test_remove_row_keeps_the_shuffled_order_of_the_others():
    rows = _list()
    order = [3, 2, 0, 1]  # d c a b
    before = ls.arrangeRows(rows, _movable, order, reverse=True)  # folder b a c d next
    removed = rows[3]  # c
    remaining, order = ls.removeRow(rows, removed, _movable, order)
    assert order == [2, 0, 1]
    after = ls.arrangeRows(remaining, _movable, order, reverse=True)
    assert _names(after) == [row.name for row in before if row is not removed]
    assert [row.itemIdx for row in remaining] == [0, 1, 2, 3, 4]


def test_remove_row_that_does_not_move():
    rows = _list()
    remaining, order = ls.removeRow(rows, rows[0], _movable, [3, 2, 0, 1])  # folder
    assert order == [3, 2, 0, 1]
    assert _names(ls.arrangeRows(remaining, _movable, order)) == ['d', 'c', 'a', 'b', 'next']
    assert [row.itemIdx for row in remaining] == [0, 1, 2, 3, 4]


# playlist of the movie player during a run of the sequencer (info line, overlay, jump back to the row)
def _key(row):
    return (row.itemIdx, row.name)


def test_play_order_is_what_the_sequencer_plays():
    rows = _list()
    assert ls.playOrder(rows, _movable) == [1, 2, 3, 4]
    ls.setMarked(rows[2], True)  # b
    ls.setMarked(rows[4], True)  # d
    assert ls.playOrder(rows, _movable, True) == [2, 4]
    # the same steps as nextPlayRow() from every row on
    for start in range(len(rows)):
        nxt = ls.nextPlayRow(rows, start, _movable, True)
        assert nxt == next((idx for idx in ls.playOrder(rows, _movable, True) if idx >= start), -1)
    assert ls.playOrder([], _movable) == []


def test_build_playlist_in_the_shown_order():
    rows = ls.arrangeRows(_list(), _movable, [3, 2, 0, 1], reverse=True)  # folder b a c d next
    playlist = ls.buildPlaylist(rows, 3, _movable, _key, shuffled=True, reverse=True, playedKeys=[_key(rows[1]), _key(rows[2])])
    assert [entry['title'] for entry in playlist['entries']] == ['b', 'a', 'c', 'd']
    assert [entry['row'] for entry in playlist['entries']] == [1, 2, 3, 4]
    assert playlist['current'] == 2
    assert [entry['played'] for entry in playlist['entries']] == [True, True, False, False]
    assert playlist['shuffled'] and playlist['reversed'] and not playlist['marked_only']


def test_build_playlist_current_never_played_and_none_off_the_list():
    rows = _list()
    playlist = ls.buildPlaylist(rows, 2, _movable, _key, playedKeys=[_key(rows[2])])
    assert not playlist['entries'][1]['played']
    # current is not a row the sequencer plays (a folder, a row not marked in "Play marked items")
    assert ls.buildPlaylist(rows, 0, _movable, _key) is None
    assert ls.buildPlaylist(rows, 1, _movable, _key, markedOnly=True) is None


def test_build_playlist_marked_only():
    rows = _list()
    ls.setMarked(rows[1], True)  # a
    ls.setMarked(rows[4], True)  # d
    playlist = ls.buildPlaylist(rows, 4, _movable, _key, markedOnly=True)
    assert [entry['title'] for entry in playlist['entries']] == ['a', 'd']
    assert playlist['current'] == 1 and playlist['marked_only']


def test_playlist_info_text():
    rows = _list()
    texts = ('Playlist', 'marked', 'shuffled', 'reversed')
    assert ls.playlistInfoText(None, *texts) == ''
    assert ls.playlistInfoText({'entries': [], 'current': 0}, *texts) == ''
    assert ls.playlistInfoText(ls.buildPlaylist(rows, 2, _movable, _key), *texts) == 'Playlist 2/4'
    for row in rows[1:5]:
        ls.setMarked(row, True)
    playlist = ls.buildPlaylist(rows, 4, _movable, _key, markedOnly=True, shuffled=True, reverse=True)
    assert ls.playlistInfoText(playlist, *texts) == 'Playlist 4/4 (marked, shuffled, reversed)'
    playlist = ls.buildPlaylist(rows, 1, _movable, _key, reverse=True)
    assert ls.playlistInfoText(playlist, *texts) == 'Playlist 1/4 (reversed)'


def test_zap_to_answer_finds_the_row():
    rows = _list()
    playlist = ls.buildPlaylist(rows, 1, _movable, _key)
    answer = ls.zapToAnswer(playlist['entries'][2])  # c
    assert ls.isZapToAnswer(answer)
    assert ls.findZapToRow(rows, answer, _key) == 3
    # the row moved (list refreshed in another order): found by its key
    moved = [rows[0], rows[3], rows[1], rows[2], rows[4], rows[5]]
    assert ls.findZapToRow(moved, answer, _key) == 1
    # gone
    assert ls.findZapToRow([row for row in rows if row.name != 'c'], answer, _key) == -1


def test_is_zap_to_answer_only_for_the_overlay():
    for answer in (None, 'zap_next', 'zap_prev', 'key_stop', 'save_buffer', ('zap_to',), ('zap_next', 1, 2)):
        assert not ls.isZapToAnswer(answer)
    assert ls.isZapToAnswer(('zap_to', 0, (0, 'a')))

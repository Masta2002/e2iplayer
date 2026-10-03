# -*- coding: utf-8 -*-
# Basketball-Video (basketball-video.com) - NBA / WNBA / EuroLeague / College full game replays
# Site: uCoz catalogue like nfl-video.com (navigation groups, "?pageN" / "/<cat>-N" paging, /search/ needs the cookie)
# Game page: "Server #N XX" buttons -> link pages (nbaontv.com, nhlgamestoday.com, ...) with one hoster <iframe>
#   (ok.ru, vidara, ...), older games embed the hoster <iframe> directly. Resolved lazily in getVideoLinks.
# Last Modified: 03.10.2026 - rebuild: basketball-video.com only (NFL-Video has its own host, MLBLive and
#   FullRaces are behind a Cloudflare challenge), watched flag, name normalisation, sidecar, search, INFO
###################################################
# LOCAL import
###################################################
from Plugins.Extensions.IPTVPlayer.components.iptvplayerinit import TranslateTXT as _, SetIPTVPlayerLastHostError
from Plugins.Extensions.IPTVPlayer.components.ihost import CHostBase, CBaseHostClass
from Plugins.Extensions.IPTVPlayer.components.iptvconfigmenu import IsSidecarEnabled, IsMediaNamingNormalized
from Plugins.Extensions.IPTVPlayer.tools.iptvtools import printDBG, printExc
from Plugins.Extensions.IPTVPlayer.tools.iptvtypes import strwithmeta
from Plugins.Extensions.IPTVPlayer.tools.iptvwatchedhelper import IPTVWatchedHelper
from Plugins.Extensions.IPTVPlayer.tools.iptvwatchedfoldermixin import GenericFolderWatchedScraperMixin, GenericFolderWatchedHostMixin
from Plugins.Extensions.IPTVPlayer.libs.urlmetahelper import buildSidecarFromItem, applySidecarToLinks, sidecarFromUrlMeta, decorateResolvedLinkItems
from Plugins.Extensions.IPTVPlayer.libs.e2ijson import dumps as json_dumps
from Plugins.Extensions.IPTVPlayer.p2p3.UrlLib import urllib_quote_plus
###################################################
# FOREIGN import
###################################################
import re
###################################################

MONTHS = {'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6, 'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12}
DATE_RE = r'\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})\b'
DATE_NUM_RE = r'\b(\d{2})\.(\d{2})\.(\d{4})\b'
LABEL_RE = r'\bFull (?:Game|Show)(?: Replays?)?(?:\s*(?:&amp;|&|and)\s*Highlights)?\b'
# navigation entries that answer 404 on the site
DEAD_NAV = ('/wnba-video', '/videos/nba_news_tv_show/nba_tv_show/46', '/content-policy-dcma')


def GetConfigList():
    return []


def gettytul():
    return 'https://basketball-video.com/'


class BasketballVideo(GenericFolderWatchedScraperMixin, CBaseHostClass):

    FAV_FIELDS = ('name', 'category', 'type', 'url', 'title', 'icon', 'desc', 'raw_title', 'competition')

    def __init__(self):
        CBaseHostClass.__init__(self, {'history': 'basketball-video.com', 'cookie': 'basketball-video.cookie'})
        self.MAIN_URL = 'https://basketball-video.com/'
        self.DEFAULT_ICON_URL = self.MAIN_URL + '_pu/75/37346371.png'
        self.HEADER = self.cm.getDefaultHeader(browser='chrome')
        self.defaultParams = {'header': self.HEADER, 'with_metadata': True, 'use_cookie': True, 'load_cookie': True, 'save_cookie': True, 'cookiefile': self.COOKIE_FILE}
        self.watchedHelper = IPTVWatchedHelper('basketballvideocom')
        self.wfInitFolderCache()

    ###################################################
    # watched flag
    ###################################################
    def _getWatchedKeyForItem(self, cItem):
        try:
            if not isinstance(cItem, dict):
                return ''
            if cItem.get('search_item') or cItem.get('name') == 'history':
                return ''
            if cItem.get('type') == 'video' or cItem.get('category') == 'video':
                url = self._stableUrl(cItem.get('url', ''))
                return 'video:%s' % url if url else ''
            if cItem.get('category') == 'list_items':
                # "Next page" rows carry the folder's url (wf_url), so page 2+ keys like page 1
                url = self._stableUrl(cItem.get('wf_url') or cItem.get('url', ''))
                return 'folder:%s' % url if url else ''
        except Exception:
            printExc()
        return ''

    def _stableUrl(self, url):
        # path only, so the domain may move
        url = str(url or '').strip()
        if not url or '/search/' in url:
            return ''
        url = re.sub(r'^https?://[^/]+', '', url)
        url = re.sub(r'\?page\d+$', '', url)
        return url or '/'

    ###################################################
    def getPage(self, url, addParams=None, post_data=None):
        if addParams is None:
            addParams = dict(self.defaultParams)
        return self.cm.getPage(url, addParams, post_data)

    def getFavouriteData(self, cItem):
        try:
            if cItem.get('type') == 'video':
                return json_dumps(dict((key, cItem[key]) for key in self.FAV_FIELDS if key in cItem))
        except Exception:
            printExc()
        return CBaseHostClass.getFavouriteData(self, cItem)

    ###################################################
    # naming
    ###################################################
    def _parseDate(self, text):
        m = re.search(DATE_RE, text or '', re.I)
        if m:
            return '%s-%02d-%02d' % (m.group(3), MONTHS[m.group(1).lower()[:3]], int(m.group(2)))
        m = re.search(DATE_NUM_RE, text or '')
        if m and 0 < int(m.group(2)) <= 12 and 0 < int(m.group(1)) <= 31:
            return '%s-%s-%s' % (m.group(3), m.group(2), m.group(1))
        return ''

    def _normTitle(self, title):
        # "Knicks vs. Spurs - NBA Finals - Game 5 - Full Game Replay - June 13, 2026" -> "Knicks vs. Spurs - NBA Finals - Game 5 (2026-06-13)"
        # "Pistons vs Heat Full Game Replay March 19, 2025 NBA" -> "Pistons vs. Heat - NBA (2025-03-19)"
        if not IsMediaNamingNormalized():
            return title
        try:
            date = self._parseDate(title)
            out = re.sub(r'\s*\|\s*', ' - ', title)
            out = re.sub(DATE_RE, ' - ', out, flags=re.I)
            out = re.sub(DATE_NUM_RE, ' - ', out)
            out = re.sub(LABEL_RE, ' - ', out, flags=re.I)
            out = re.sub(r'\bvs\.?(?=\s)', 'vs.', out)
            keep = []
            for p in out.split(' - '):
                p = p.strip(' ,:-')
                if p and p.lower() not in [k.lower() for k in keep]:
                    keep.append(p)
            out = ' - '.join(keep) or title
            if date:
                out = '%s (%s)' % (out, date)
            return out
        except Exception:
            printExc()
        return title

    ###################################################
    # listing
    ###################################################
    def _navLinks(self, html):
        links = []
        for url, attrs, title in re.findall(r'<a href="((?:https?://[^/"]+)?/[^"#]*)"([^>]*)>([^<]+)</a>', html):
            path = re.sub(r'^https?://[^/]+', '', url)
            if 'nofollow' in attrs or path in DEAD_NAV:
                continue
            links.append((self.getFullUrl(url), self.cleanHtmlStr(title)))
        return links

    def listMain(self, cItem):
        sts, data = self.getPage(self.getMainUrl())
        if not sts:
            return
        self.setMainUrl(data.meta.get('url', self.getMainUrl()))
        nav = self.cm.ph.getDataBeetwenNodes(data, ('<ul', '>', 'list_cat'), ('</nav', '>'), False)[1]
        params = dict(cItem)
        params.update({'category': 'list_items', 'title': _('Latest'), 'url': self.getMainUrl()})
        self.addDir(params)
        # top level links, then the "beefup" groups (per teams / per year / other) as sub folders
        top = re.sub(r'<li class="beefup2">.*?</ul>\s*</li>', '', nav, flags=re.S)
        for url, title in self._navLinks(top):
            params = dict(cItem)
            params.update({'category': 'list_items', 'title': title, 'url': url})
            self.addDir(params)
        for group in self.cm.ph.getAllItemsBeetwenMarkers(nav, '<li class="beefup2">', '</ul>'):
            title = self.cleanHtmlStr(self.cm.ph.getSearchGroups(group, r'class="beefup-head"[^>]*>([^<]+)<')[0])
            subs = self._navLinks(group.split('</a>', 1)[-1])
            if not title or not subs:
                continue
            params = dict(cItem)
            params.update({'category': 'list_group', 'title': title, 'subs': subs})
            self.addDir(params)
        self.listsTab(self.searchItems(), cItem)

    def listGroup(self, cItem):
        for url, title in cItem.get('subs', []):
            params = dict(cItem)
            params.pop('subs', None)
            params.update({'category': 'list_items', 'title': title, 'url': url})
            self.addDir(params)

    def _addGame(self, cItem, url, title, icon, desc, competition=''):
        if not url or not title:
            return
        params = dict(cItem)
        for key in ('subs', 'page', 'wf_url'):
            params.pop(key, None)
        params.update({'good_for_fav': True, 'category': 'video', 'title': self._normTitle(title), 'raw_title': title,
                       'url': url, 'icon': icon, 'desc': desc, 'competition': competition})
        self.addVideo(params)

    def _addNextPage(self, cItem, nextPage):
        nextPage = nextPage.replace('&amp;', '&')
        if nextPage.startswith('//'):
            nextPage = 'https:' + nextPage
        params = dict(cItem)
        params.update({'good_for_fav': False, 'title': _('Next page'), 'url': self.getFullUrl(nextPage),
                       'page': cItem.get('page', 1) + 1, 'wf_url': cItem.get('wf_url') or cItem.get('url', '')})
        self.addDir(params)

    def listItems(self, cItem):
        printDBG("BasketballVideo.listItems [%s]" % cItem['url'])
        sts, data = self.getPage(cItem['url'])
        if not sts:
            return
        # the pager's own "next" link (from page 2 on the first swchItem points back to page 1)
        nextPage = self.cm.ph.getSearchGroups(data, r'swchItem-next"\s+href="([^"]+)"')[0]
        items = self.cm.ph.getAllItemsBeetwenMarkers(data, 'class="poster">', 'class="short_bottom"')
        for item in items:
            url = self.getFullUrl(self.cm.ph.getSearchGroups(item, r'href="([^"]+)"')[0])
            title = self.cleanHtmlStr(self.cm.ph.getDataBeetwenNodes(item, ('<h3', '>'), ('</h3', '>'), False)[1])
            icon = self.getFullIconUrl(self.cm.ph.getSearchGroups(item, r'<img[^>]+src="([^"]+)"')[0])
            desc = self.cleanHtmlStr(self.cm.ph.getDataBeetwenNodes(item, ('<div', '>', 'short_descr'), ('</div', '>'), False)[1])
            competition = self.cleanHtmlStr(self.cm.ph.getDataBeetwenNodes(item, ('<div', '>', 'short_cat'), ('</div', '>'), False)[1])
            self._addGame(cItem, url, title, icon, desc, competition)
        if nextPage and items:
            self._addNextPage(cItem, nextPage)

    def listSearchResult(self, cItem, searchPattern, searchType):
        url = cItem.get('url', '')
        if not url:
            url = self.getFullUrl('/search/?q=%s' % urllib_quote_plus(searchPattern))
        params = dict(self.defaultParams)
        params['header'] = dict(self.HEADER, Referer=self.getMainUrl())
        sts, data = self.getPage(url, params)
        if not sts:
            return
        nextPage = self.cm.ph.getSearchGroups(data, r'swchItem-next"\s+href="([^"]+)"')[0]
        items = self.cm.ph.getAllItemsBeetwenMarkers(data, '<table border="0" cellpadding="0" cellspacing="0" width="100%" class="eBlock"', '</table>')
        for item in items:
            tmp = self.cm.ph.getDataBeetwenNodes(item, ('<div', '>', 'eTitle'), ('</a', '>'))[1]
            link = self.cm.ph.getSearchGroups(tmp, r'href="([^"]+)"')[0]
            title = self.cleanHtmlStr(tmp)
            icon = self.getFullIconUrl(self.cm.ph.getSearchGroups(item, r'<img[^>]+src="([^"]+)"')[0])
            if not link or '/search/' in link:
                continue
            self._addGame(cItem, self.getFullUrl(link), title, icon, '')
        if nextPage and items:
            # ";md=" is a per-request token, the plain query pages fine
            self._addNextPage(cItem, nextPage.split(';md=')[0])

    ###################################################
    # links
    ###################################################
    def _gameBody(self, data):
        body = self.cm.ph.getDataBeetwenMarkers(data, 'fullstory block_elem', 'full_info block_elem', False)[1]
        return re.sub(r'<(script|style)[^>]*>.*?</\1>', '', body, flags=re.S | re.I)

    def _isLabel(self, text):
        return 0 < len(text) < 90 and not text.lower().startswith('disclaimer') and not set(text) <= set('- ')

    def getLinksForVideo(self, cItem):
        printDBG("BasketballVideo.getLinksForVideo [%s]" % cItem['url'])
        sts, data = self.getPage(cItem['url'])
        if not sts:
            return []
        body = self._gameBody(data)
        urlTab = []
        seen = set()

        def addLink(url, name):
            url = url.replace('&amp;', '&')
            if url.startswith('//'):
                url = 'https:' + url
            url = self.getFullUrl(url)
            if not self.cm.isValidUrl(url) or url in seen:
                return
            seen.add(url)
            urlTab.append({'name': name or self.up.getHostName(url), 'url': strwithmeta(url, {'Referer': cItem['url']}), 'need_resolve': 1})

        # day pages (Summer League, ...): a table "Matchup | OK | Filemoon" with one "Watch" button per hoster column
        for table in re.findall(r'<table[^>]+class="nhl-box".*?</table>', body, re.S):
            columns = []
            for row in re.findall(r'<tr[^>]*>(.*?)</tr>', table, re.S):
                cells = re.findall(r'<td[^>]*>(.*?)</td>', row, re.S)
                if 'nhl-game' not in row:
                    if 'href=' not in row and len(cells) > 1:
                        columns = [self.cleanHtmlStr(c) for c in cells]
                    continue
                game = self.cleanHtmlStr(cells[0]) if cells else ''
                for idx, cell in enumerate(cells[1:], 1):
                    column = columns[idx] if idx < len(columns) else ''
                    for url in re.findall(r'<a[^>]+href="([^"]+)"', cell):
                        addLink(url, ' - '.join([x for x in (game, column) if x]))
        body = re.sub(r'<table[^>]+class="nhl-box".*?</table>', '', body, flags=re.S)

        label = ''
        # walk the page in order: a short paragraph ("Server #2 (FM)", "Baskonia vs Olimpia Milan") names
        # the following buttons / players
        # (no zero-width re.split - Python 2.7 does not split on empty matches)
        for chunk in re.sub(r'(<p[\s>])', r'<!--split-->\1', body).split('<!--split-->'):
            para = self.cm.ph.getDataBeetwenNodes(chunk, ('<p', '>'), ('</p', '>'), False)[1]
            if para and '<br' not in para:
                heading = self.cleanHtmlStr(re.sub(r'<a[^>]+>.*?</a>', '', para, flags=re.S))
                if self._isLabel(heading):
                    label = heading
            anchors = re.findall(r'<a[^>]+class="su-button[^"]*"[^>]+href="([^"]+)"[^>]*>(.*?)</a>', chunk, re.S)
            frames = re.findall(r'<iframe[^>]+src="([^"]+)"', chunk, re.I)
            for url, text in anchors:
                text = self.cleanHtmlStr(text)
                if text.lower() == 'watch':
                    text = ''
                addLink(url, ' - '.join([x for x in (label, text) if x]))
            for url in frames:
                host = self.up.getHostName('https:' + url if url.startswith('//') else url)
                addLink(url, ' - '.join([x for x in (label, host) if x]))
        if not urlTab:
            SetIPTVPlayerLastHostError(_("No video sources found on this page (the replay may not be uploaded yet)."))
            return []
        # e.g. two ok.ru players under one "Server #2" heading -> "(1)", "(2)"
        names = [item['name'] for item in urlTab]
        counter = {}
        for item in urlTab:
            if names.count(item['name']) > 1:
                counter[item['name']] = counter.get(item['name'], 0) + 1
                item['name'] = '%s (%d)' % (item['name'], counter[item['name']])
        synopsis = self.cleanHtmlStr(cItem.get('desc', ''))
        return applySidecarToLinks(urlTab, buildSidecarFromItem(cItem, IsSidecarEnabled(), synopsis))

    def getVideoLinks(self, videoUrl):
        printDBG("BasketballVideo.getVideoLinks [%s]" % videoUrl)
        videoUrl = strwithmeta(videoUrl)
        if not self.cm.isValidUrl(videoUrl):
            return []
        sidecar = sidecarFromUrlMeta(videoUrl, IsSidecarEnabled())
        url = videoUrl
        if 1 != self.up.checkHostSupport(url):
            # link page of the site network: one hoster <iframe>
            params = dict(self.defaultParams)
            params['header'] = dict(self.HEADER, Referer=videoUrl.meta.get('Referer', self.getMainUrl()))
            sts, data = self.getPage(url, params)
            if not sts:
                return []
            frame = self.cm.ph.getSearchGroups(data, r'<iframe[^>]+src="([^"]+)"', ignoreCase=True)[0].replace('&amp;', '&')
            if frame.startswith('//'):
                frame = 'https:' + frame
            if not self.cm.isValidUrl(frame):
                SetIPTVPlayerLastHostError(_("This source is not available any more."))
                return []
            url = strwithmeta(frame, {'Referer': videoUrl})
            if 0 > self.up.checkHostSupport(url):
                SetIPTVPlayerLastHostError(_("Hoster %s is not supported.") % self.up.getHostName(url))
                return []
        return decorateResolvedLinkItems(self.up.getVideoLinkExt(url), sidecar)

    ###################################################
    # INFO
    ###################################################
    def getArticleContent(self, cItem):
        printDBG("BasketballVideo.getArticleContent [%s]" % cItem.get('url', ''))
        title = cItem.get('raw_title') or cItem.get('title', '')
        text = cItem.get('desc', '')
        icon = cItem.get('icon', '')
        other = {}
        if cItem.get('competition'):
            other['category'] = cItem['competition']
        sts, data = self.getPage(cItem['url'])
        if sts:
            title = self.cleanHtmlStr(self.cm.ph.getSearchGroups(data, r'<h1[^>]*>(.*?)</h1>')[0]) or title
            body = self._gameBody(data)
            body = re.sub(r'<a[^>]+class="su-button.*?</a>', '', body, flags=re.S)
            lines = []
            for para in re.findall(r'<(?:p|div)[^>]*>((?:(?!<(?:p|div)[\s>]).)*?)</(?:p|div)>', body, re.S):
                para = self.cleanHtmlStr(re.sub(r'<br\s*/?>', '[/br]', para))
                if not para or set(para) <= set('-[/br] ') or para.lower().startswith('disclaimer') or 'Server #' in para:
                    continue
                lines.append(para)
            if lines:
                text = '[/br]'.join(lines)
            icon = icon or self.getFullIconUrl(self.cm.ph.getSearchGroups(data, r'class="full_img"[^>]*>.*?<img[^>]+src="([^"]+)"')[0])
            category = self.cleanHtmlStr(self.cm.ph.getSearchGroups(data, r'class="e-category"[^>]*>(.*?)</span>')[0])
            if category:
                other['category'] = category
            views = self.cm.ph.getSearchGroups(data, r'class="ed-value">(\d+)<')[0]
            if views:
                other['views'] = views
        date = self._parseDate(title)
        if date:
            other['released'] = date
        return [{'title': self.cleanHtmlStr(title), 'text': text, 'images': [{'title': '', 'url': icon}] if icon else [], 'other_info': other}]

    ###################################################
    def handleService(self, index, refresh=0, searchPattern='', searchType=''):
        CBaseHostClass.handleService(self, index, refresh, searchPattern, searchType)
        name = self.currItem.get("name", '')
        category = self.currItem.get("category", '')
        printDBG("BasketballVideo.handleService name[%s] category[%s]" % (name, category))
        self.currList = []
        if name is None:
            self.listMain({'name': 'category'})
        elif category == 'list_group':
            self.listGroup(self.currItem)
        elif category == 'list_items':
            self.listItems(self.currItem)
        elif category in ('search', 'search_next_page'):
            cItem = dict(self.currItem)
            cItem.update({'search_item': False, 'name': 'category', 'category': 'search_next_page'})
            self.listSearchResult(cItem, searchPattern, searchType)
        elif category == 'search_history':
            self.listsHistory({'name': 'history', 'category': 'search'}, 'desc', _("Type: "))
        else:
            printExc()
        CBaseHostClass.endHandleService(self, index, refresh)


class IPTVHost(GenericFolderWatchedHostMixin, CHostBase):

    def __init__(self):
        CHostBase.__init__(self, BasketballVideo(), True, [])
        self.cachedRet = None
        self.refreshAfterWatchedFlagChange = False
        self.watchedHelper = IPTVWatchedHelper('basketballvideocom')

    def withArticleContent(self, cItem):
        return cItem.get('type') == 'video'

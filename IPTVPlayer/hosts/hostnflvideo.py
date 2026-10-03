# -*- coding: utf-8 -*-
# NFL Video (nfl-video.com) - NFL / College Football full game replays, condensed games, Super Bowls
# Site: uCoz catalogue (seasons / teams from the side navigation, "?pageN" paging, /search/ needs the ucz_h cookie)
# Game page: "Server #N XX" buttons -> link pages (nhlgamestoday.com, nbaontv.com, ...) with one hoster <iframe>
#   (ok.ru, odysee, vidara, ...), older games embed the hoster <iframe> directly. Resolved lazily in getVideoLinks.
# Last Modified: 03.10.2026 - rewrite: watched flag, name normalisation, sidecar, search, INFO
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


def GetConfigList():
    return []


def gettytul():
    return 'https://nfl-video.com/'


class NFLVideo(GenericFolderWatchedScraperMixin, CBaseHostClass):

    FAV_FIELDS = ('name', 'category', 'type', 'url', 'title', 'icon', 'desc', 'raw_title')

    def __init__(self):
        CBaseHostClass.__init__(self, {'history': 'nflvideo', 'cookie': 'nflvideo.cookie'})
        self.MAIN_URL = 'https://nfl-video.com/'
        self.DEFAULT_ICON_URL = ''  # the site has no logo image (text logotype only)
        self.HEADER = self.cm.getDefaultHeader(browser='chrome')
        self.defaultParams = {'header': self.HEADER, 'with_metadata': True, 'use_cookie': True, 'load_cookie': True, 'save_cookie': True, 'cookiefile': self.COOKIE_FILE}
        self.watchedHelper = IPTVWatchedHelper('nflvideo')
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
            url = self._stableUrl(cItem.get('url', ''))
            if not url:
                return ''
            if cItem.get('type') == 'video' or cItem.get('category') == 'video':
                return 'video:%s' % url
            if cItem.get('category') == 'list_items':
                return 'folder:%s' % url
        except Exception:
            printExc()
        return ''

    def _stableUrl(self, url):
        # path only, without the uCoz "?pageN" paging, so page 2 keys like page 1 and the domain may move
        url = str(url or '').strip()
        if not url or '/search/' in url:
            return ''
        url = re.sub(r'^https?://[^/]+', '', url)
        url = re.sub(r'\?page\d+$', '', url)
        url = re.sub(r'^(/archive/[^?]+/\d+)-\d+$', r'\1', url)
        return url

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
        m = re.search(r'\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+(\d{1,2}),?\s+(\d{4})', text or '', re.I)
        if m:
            return '%s-%02d-%02d' % (m.group(3), MONTHS[m.group(1).lower()[:3]], int(m.group(2)))
        return ''

    def _normTitle(self, title):
        # "Steelers vs. Browns - Full Game Replay - NFL Week 04 - October 1, 2026" -> "Steelers vs. Browns - NFL Week 04 (2026-10-01)"
        if not IsMediaNamingNormalized():
            return title
        try:
            date = self._parseDate(title)
            parts = [p.strip() for p in title.split(' - ') if p.strip()]
            keep = []
            for p in parts:
                if re.match(r'^Full Game(?: Replay)?(?:\s*(?:&|and)\s*Highlights)?$', p, re.I):
                    continue
                if date and self._parseDate(p) and len(re.sub(r'[\d,\s]', '', p)) <= 10:
                    continue
                keep.append(p)
            out = ' - '.join(keep) or title
            if date and date[:4] not in out.split('(')[-1]:
                out = '%s (%s)' % (out, date)
            return out
        except Exception:
            printExc()
        return title

    ###################################################
    # listing
    ###################################################
    def listMain(self, cItem):
        sts, data = self.getPage(self.getMainUrl())
        if not sts:
            return
        self.setMainUrl(data.meta.get('url', self.getMainUrl()))
        nav = self.cm.ph.getDataBeetwenNodes(data, ('<ul', '>', 'list_cat'), ('</nav', '>'), False)[1]
        params = dict(cItem)
        params.update({'category': 'list_items', 'title': _('Latest'), 'url': self.getMainUrl()})
        self.addDir(params)
        # top level links, then the "beefup" groups (Full Games / by Teams / ...) as sub folders
        top = re.sub(r'<li class="beefup2">.*?</ul>\s*</li>', '', nav, flags=re.S)
        for url, title in re.findall(r'<a href="(/[^"]+)"[^>]*>([^<]+)</a>', top):
            params = dict(cItem)
            params.update({'category': 'list_items', 'title': self.cleanHtmlStr(title), 'url': self.getFullUrl(url)})
            self.addDir(params)
        for group in self.cm.ph.getAllItemsBeetwenMarkers(nav, '<li class="beefup2">', '</ul>'):
            title = self.cleanHtmlStr(self.cm.ph.getSearchGroups(group, r'class="beefup-head"[^>]*>([^<]+)<')[0])
            subs = re.findall(r'<a href="(/[^"]+)"[^>]*>([^<]+)</a>', group)
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
            params.update({'category': 'list_items', 'title': self.cleanHtmlStr(title), 'url': self.getFullUrl(url)})
            self.addDir(params)

    def _addGame(self, cItem, url, title, icon, desc):
        if not url or not title:
            return
        params = dict(cItem)
        params.pop('subs', None)
        params.pop('page', None)
        params.update({'good_for_fav': True, 'category': 'video', 'title': self._normTitle(title), 'raw_title': title,
                       'url': url, 'icon': icon, 'desc': desc})
        self.addVideo(params)

    def listItems(self, cItem):
        printDBG("NFLVideo.listItems [%s]" % cItem['url'])
        sts, data = self.getPage(cItem['url'])
        if not sts:
            return
        nextPage = self.cm.ph.getSearchGroups(data, r'swchItem-next"\s+href="([^"]+)"')[0]
        items = self.cm.ph.getAllItemsBeetwenMarkers(data, 'class="poster">', 'class="short_bottom"')
        for item in items:
            url = self.getFullUrl(self.cm.ph.getSearchGroups(item, r'href="([^"]+)"')[0])
            title = self.cleanHtmlStr(self.cm.ph.getDataBeetwenNodes(item, ('<h3', '>'), ('</h3', '>'), False)[1])
            icon = self.getFullIconUrl(self.cm.ph.getSearchGroups(item, r'<img[^>]+src="([^"]+)"')[0])
            desc = self.cleanHtmlStr(self.cm.ph.getDataBeetwenNodes(item, ('<div', '>', 'short_descr'), ('</div', '>'), False)[1])
            self._addGame(cItem, url, title, icon, desc)
        if not items and 'fullstory block_elem' in data:
            # a navigation entry that is a single show page (e.g. Hard Knocks)
            title = self.cleanHtmlStr(self.cm.ph.getSearchGroups(data, r'<h1[^>]*>(.*?)</h1>')[0]) or cItem['title']
            icon = self.getFullIconUrl(self.cm.ph.getSearchGroups(data, r'class="full_img"[^>]*>\s*<img[^>]+src="([^"]+)"')[0])
            self._addGame(cItem, cItem['url'], title, icon, '')
        if nextPage and items:
            params = dict(cItem)
            params.update({'good_for_fav': False, 'title': _('Next page'), 'url': self.getFullUrl(nextPage.replace('&amp;', '&')), 'page': cItem.get('page', 1) + 1})
            self.addDir(params)

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
            nextPage = nextPage.replace('&amp;', '&').split(';md=')[0]
            if nextPage.startswith('//'):
                nextPage = 'https:' + nextPage
            params = dict(cItem)
            params.update({'good_for_fav': False, 'title': _('Next page'), 'url': self.getFullUrl(nextPage), 'page': cItem.get('page', 1) + 1})
            self.addDir(params)

    ###################################################
    # links
    ###################################################
    def _gameBody(self, data):
        body = self.cm.ph.getDataBeetwenNodes(data, ('<div', '>', 'video-content'), ('<div', '>', 'entry-meta-bottom'), False)[1]
        if not body:
            body = self.cm.ph.getDataBeetwenMarkers(data, 'fullstory block_elem', 'full_info block_elem', False)[1]
        return body

    def getLinksForVideo(self, cItem):
        printDBG("NFLVideo.getLinksForVideo [%s]" % cItem['url'])
        sts, data = self.getPage(cItem['url'])
        if not sts:
            return []
        body = self._gameBody(data)
        urlTab = []
        seen = set()
        label = ''
        # walk the page in order: a paragraph text without buttons ("Server #2 DM", "Condensed Game") names the
        # following buttons; a paragraph with a heading and buttons carries both
        for chunk in re.split(r'(?=<p[\s>])', body):
            anchors = re.findall(r'<a[^>]+class="su-button[^"]*"[^>]+href="([^"]+)"[^>]*>(.*?)</a>', chunk, re.S)
            frames = re.findall(r'<iframe[^>]+src="([^"]+)"', chunk, re.I)
            heading = self.cleanHtmlStr(re.sub(r'<a[^>]+>.*?</a>', '', chunk, flags=re.S))
            isLabel = (anchors or frames) and len(heading) < 40
            isLabel = isLabel or (len(heading) < 30 and re.search(r'Server|Condensed|Highlights', heading))
            if heading and isLabel:
                label = heading
            for url, text in anchors:
                url = self.getFullUrl(url.replace('&amp;', '&'))
                if not self.cm.isValidUrl(url) or url in seen:
                    continue
                seen.add(url)
                text = self.cleanHtmlStr(text)
                name = '%s - %s' % (label, text) if label and text else (label or text or self.up.getHostName(url))
                urlTab.append({'name': name, 'url': strwithmeta(url, {'Referer': cItem['url']}), 'need_resolve': 1})
            for url in frames:
                url = url.replace('&amp;', '&')
                if url.startswith('//'):
                    url = 'https:' + url
                if not self.cm.isValidUrl(url) or url in seen:
                    continue
                seen.add(url)
                host = self.up.getHostName(url)
                name = '%s - %s' % (label, host) if label else host
                urlTab.append({'name': name, 'url': strwithmeta(url, {'Referer': cItem['url']}), 'need_resolve': 1})
        if not urlTab:
            SetIPTVPlayerLastHostError(_("No video sources found on this page (the replay may not be uploaded yet)."))
            return []
        synopsis = self.cleanHtmlStr(cItem.get('desc', ''))
        return applySidecarToLinks(urlTab, buildSidecarFromItem(cItem, IsSidecarEnabled(), synopsis))

    def getVideoLinks(self, videoUrl):
        printDBG("NFLVideo.getVideoLinks [%s]" % videoUrl)
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
        printDBG("NFLVideo.getArticleContent [%s]" % cItem.get('url', ''))
        title = cItem.get('raw_title') or cItem.get('title', '')
        text = cItem.get('desc', '')
        icon = cItem.get('icon', '')
        other = {}
        sts, data = self.getPage(cItem['url'])
        if sts:
            body = self._gameBody(data)
            body = re.sub(r'<p[^>]*>\s*<span[^>]*>\s*<span[^>]*>Server.*?</p>', '', body, flags=re.S)
            body = re.sub(r'<a[^>]+class="su-button.*?</a>', '', body, flags=re.S)
            lines = []
            for para in re.findall(r'<p[^>]*>(.*?)</p>', body, re.S):
                para = self.cleanHtmlStr(para.replace('<br />', '[/br]').replace('<br>', '[/br]'))
                if not para or set(para) <= set('-[/br] ') or para.startswith('Disclaimer') or 'Server #' in para:
                    continue
                lines.append(para)
            if lines:
                text = '[/br]'.join(lines)
            icon = icon or self.getFullIconUrl(self.cm.ph.getSearchGroups(data, r'class="full_img"[^>]*>\s*<img[^>]+src="([^"]+)"')[0])
        date = self._parseDate(title)
        if date:
            other['released'] = date
        return [{'title': self.cleanHtmlStr(title), 'text': text, 'images': [{'title': '', 'url': icon}] if icon else [], 'other_info': other}]

    ###################################################
    def handleService(self, index, refresh=0, searchPattern='', searchType=''):
        CBaseHostClass.handleService(self, index, refresh, searchPattern, searchType)
        name = self.currItem.get("name", '')
        category = self.currItem.get("category", '')
        printDBG("NFLVideo.handleService name[%s] category[%s]" % (name, category))
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
        CHostBase.__init__(self, NFLVideo(), True, [])
        self.cachedRet = None
        self.refreshAfterWatchedFlagChange = False
        self.watchedHelper = IPTVWatchedHelper('nflvideo')

    def withArticleContent(self, cItem):
        return cItem.get('type') == 'video'

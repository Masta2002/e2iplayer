# -*- coding: utf-8 -*-
# 7reels (7reels.cc) - TMDb-indexed movie/series aggregator
# based on a community host by "alawa m2"
import json
import re
from Plugins.Extensions.IPTVPlayer.components.ihost import CBaseHostClass, CHostBase
from Plugins.Extensions.IPTVPlayer.components.iptvplayerinit import TranslateTXT as _
from Plugins.Extensions.IPTVPlayer.p2p3.UrlLib import urllib_quote_plus
from Plugins.Extensions.IPTVPlayer.tools.iptvtools import printDBG, printExc
from Plugins.Extensions.IPTVPlayer.tools.iptvtypes import strwithmeta
from Plugins.Extensions.IPTVPlayer.tools.iptvwatchedhelper import IPTVWatchedHelper
from Plugins.Extensions.IPTVPlayer.tools.iptvwatchedfoldermixin import GenericFolderWatchedScraperMixin, GenericFolderWatchedHostMixin
from Plugins.Extensions.IPTVPlayer.libs.urlmetahelper import buildSidecarFromItem, applySidecarToLinks, sidecarFromUrlMeta, decorateResolvedLinkItems
from Plugins.Extensions.IPTVPlayer.components.iptvconfigmenu import IsSidecarEnabled, IsMediaNamingNormalized


def GetConfigList():
    return []


def gettytul():
    return 'https://7reels.cc/'


class SevenReels(GenericFolderWatchedScraperMixin, CBaseHostClass):

    IMG_URL = 'https://image.tmdb.org/t/p/w500'

    def __init__(self):
        CBaseHostClass.__init__(self, {'history': 'SevenReels', 'cookie': 'SevenReels.cookie'})
        self.MAIN_URL = gettytul()
        self.HEADER = self.cm.getDefaultHeader(browser='chrome')
        self.defaultParams = {'header': self.HEADER, 'use_cookie': True, 'load_cookie': True, 'save_cookie': True, 'cookiefile': self.COOKIE_FILE}
        api = self.MAIN_URL + 'api/'
        self.MENU = [
            {'category': 'list_items', 'title': _('Trending this week'), 'url': api + 'recs/top-this-week'},
            {'category': 'list_items', 'title': _('Short Reels'), 'url': api + 'top-reels'},
            {'category': 'list_items', 'title': _('Movies'), 'url': api + 'tmdb/discover/movie?sort_by=popularity.desc'},
            {'category': 'list_items', 'title': _('Series'), 'url': api + 'tmdb/discover/tv?sort_by=popularity.desc'},
            {'category': 'list_items', 'title': _('Comedy'), 'url': api + 'tmdb/discover/movie?with_genres=35'},
            {'category': 'list_items', 'title': _('Action & Thriller'), 'url': api + 'tmdb/discover/movie?with_genres=28'},
            {'category': 'list_items', 'title': _('Drama'), 'url': api + 'tmdb/discover/movie?with_genres=18'},
            {'category': 'list_items', 'title': _('Horror'), 'url': api + 'tmdb/discover/movie?with_genres=27'},
            {'category': 'list_items', 'title': _('Sci-Fi & Fantasy'), 'url': api + 'tmdb/discover/movie?with_genres=878'},
            {'category': 'list_items', 'title': _('Romance'), 'url': api + 'tmdb/discover/movie?with_genres=10749'},
            {'category': 'list_items', 'title': _('Documentary'), 'url': api + 'tmdb/discover/movie?with_genres=99'},
            {'category': 'list_items', 'title': _('Animation'), 'url': api + 'tmdb/discover/movie?with_genres=16'},
        ] + self.searchItems()

        self.watchedHelper = IPTVWatchedHelper('sevenreels')
        self.wfInitFolderCache()

    ###################################################
    # watched flag
    ###################################################
    def _getWatchedKeyForItem(self, cItem):
        try:
            if not isinstance(cItem, dict):
                return ''
            if cItem.get('type', '') in ('video', 'audio'):
                url = str(cItem.get('url', '') or '').strip()
                return 'video:%s' % url if url else ''
            if cItem.get('search_item') or cItem.get('name') == 'history':
                return ''
            if cItem.get('category', '') in ('search', 'search_next_page', 'search_history'):
                return ''
            url = self.wfNormalizeUrlKey(cItem.get('url', ''))
            return 'folder:%s' % url if url else ''
        except Exception:
            printExc()
        return ''

    def getPage(self, baseUrl, addParams=None, post_data=None):
        if addParams is None:
            addParams = dict(self.defaultParams)
        return self.cm.getPage(baseUrl, addParams, post_data)

    def _extractItems(self, parsed):
        """Flatten the several shapes the 7reels API returns into a plain list of TMDb entries."""
        if not isinstance(parsed, dict):
            return []
        if isinstance(parsed.get('items'), list):
            return parsed['items']
        if isinstance(parsed.get('featured'), dict):
            out = []
            for key in ('movie', 'tv'):
                out.extend(parsed['featured'].get(key) or [])
            return out
        for key in ('results', 'topInCountry'):
            if isinstance(parsed.get(key), list):
                return parsed[key]
        return []

    def listItems(self, cItem):
        printDBG("SevenReels.listItems |%s|" % cItem['url'])
        page = cItem.get('page', 1)
        url = cItem['url']
        if 'page=' in url:
            url = re.sub(r'page=\d+', 'page=%d' % page, url)
        else:
            url += ('&' if '?' in url else '?') + 'page=%d' % page

        sts, data = self.getPage(url)
        if not sts:
            return
        try:
            parsed = json.loads(data)
        except Exception:
            printExc()
            return

        items = self._extractItems(parsed)
        defType = 'tv' if 'discover/tv' in cItem['url'] else 'movie'
        normalize = IsMediaNamingNormalized()
        count = 0
        for item in items:
            mediaId = item.get('id')
            title = self.cleanHtmlStr(item.get('title') or item.get('name') or '')
            if not mediaId or not title:
                continue
            mediaType = item.get('media_type') or defType
            poster = item.get('poster_path') or ''
            year = (item.get('release_date') or item.get('first_air_date') or '')[:4]
            dispTitle = ('%s (%s)' % (title, year)) if (year and (normalize or mediaType == 'movie')) else title
            params = dict(cItem)
            params.pop('page', None)
            params.update({
                'good_for_fav': True,
                'category': 'video',
                'title': dispTitle,
                's_title': title,
                'year': year,
                'url': '%s%s/%s/watch' % (self.MAIN_URL, mediaType, mediaId),
                'icon': (self.IMG_URL + poster) if poster else '',
                'desc': self.cleanHtmlStr(item.get('overview', '')),
            })
            self.addVideo(params)
            count += 1

        if count >= 18:
            params = dict(cItem)
            params.update({'good_for_fav': False, 'title': _('Next page'), 'page': page + 1, 'category': 'list_items'})
            self.addDir(params)

    def listSearchResult(self, cItem, searchPattern, searchType):
        printDBG("SevenReels.listSearchResult [%s]" % searchPattern)
        cItem = dict(cItem)
        cItem['url'] = self.MAIN_URL + 'api/search/smart?q=' + urllib_quote_plus(searchPattern)
        self.listItems(cItem)

    # 7reels' watch page is a JS shell that just iframes one of a fixed set of
    # TMDb-keyed embed providers (server list + URL shapes lifted from the site's
    # own bundle). We hand every candidate to urlparser; whichever ones it knows
    # how to resolve show up as playable links. "tv" appends /<season>/<episode>.
    _EMBEDS = (
        ('AdRock', 'https://vidrock.net/%(kind)s/%(id)s%(se)s'),
        ('Strigil', 'https://strigil.cc/embed/%(kind)s/%(id)s%(se)s?embedKey=key_c90081fa77254eb5&autoPlay=true'),
        ('VidSrc', 'https://vidsrc.mov/embed/%(kind)s/%(id)s%(se)s'),
        ('VidEasy', 'https://player.videasy.to/%(kind)s/%(id)s%(se)s'),
        ('VidLink', 'https://vidlink.pro/%(kind)s/%(id)s%(se)s'),
        ('VidCore', 'https://vidcore.net/%(kind)s/%(id)s%(se)s'),
        ('VidNest', 'https://vidnest.fun/%(kind)s/%(id)s%(se)s'),
        ('Vidzee', 'https://player.vidzee.wtf/embed/%(kind)s/%(id)s%(se)s'),
        ('VidUp', 'https://vidup.to/%(kind)s/%(id)s%(se)s'),
    )

    def getLinksForVideo(self, cItem):
        printDBG("SevenReels.getLinksForVideo [%s]" % cItem['url'])
        m = re.search(r'/(movie|tv)/(\d+)', cItem['url'])
        if not m:
            return []
        fields = {'kind': m.group(1), 'id': m.group(2), 'se': '/1/1' if m.group(1) == 'tv' else ''}

        urlTab = []
        for label, tpl in self._EMBEDS:
            urlTab.append({'name': label, 'url': strwithmeta(tpl % fields, {'Referer': self.MAIN_URL}), 'need_resolve': 1})
        return applySidecarToLinks(urlTab, buildSidecarFromItem(cItem, IsSidecarEnabled()))

    def getVideoLinks(self, videoUrl):
        printDBG("SevenReels.getVideoLinks [%s]" % videoUrl)
        if self.cm.isValidUrl(videoUrl):
            sidecar = sidecarFromUrlMeta(videoUrl, IsSidecarEnabled())
            return decorateResolvedLinkItems(self.up.getVideoLinkExt(videoUrl), sidecar)
        return []

    def handleService(self, index, refresh=0, searchPattern='', searchType=''):
        printDBG('SevenReels.handleService start')
        CBaseHostClass.handleService(self, index, refresh, searchPattern, searchType)
        name = self.currItem.get('name', None)
        category = self.currItem.get('category', '')
        self.currList = []

        if name is None:
            self.listsTab(self.MENU, {'name': 'category'})
        elif category == 'list_items':
            self.listItems(self.currItem)
        elif category in ('search', 'search_next_page'):
            cItem = dict(self.currItem)
            cItem.update({'search_item': False, 'name': 'category'})
            self.listSearchResult(cItem, searchPattern, searchType)
        elif category == 'search_history':
            self.listsHistory({'name': 'history', 'category': 'search'}, 'desc')
        else:
            printExc()

        CBaseHostClass.endHandleService(self, index, refresh)


class IPTVHost(GenericFolderWatchedHostMixin, CHostBase):

    def __init__(self):
        CHostBase.__init__(self, SevenReels(), True, [])
        self.cachedRet = None
        self.refreshAfterWatchedFlagChange = False
        self.watchedHelper = IPTVWatchedHelper('sevenreels')

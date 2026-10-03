# -*- coding: utf-8 -*-
# Al Jazeera - live channels and the programme archive of ajnet.me (Arabic) / aljazeera.com (English).
# Both sites run the same WordPress GraphQL API (/graphql?wp-site=aja|aje, GET with persisted
# operation names); an episode carries its Brightcove video id, played through the Brightcove
# playback API (policy key read from the site's player script).
import re
from Plugins.Extensions.IPTVPlayer.components.ihost import CBaseHostClass, CHostBase
from Plugins.Extensions.IPTVPlayer.components.iptvplayerinit import TranslateTXT as _
from Plugins.Extensions.IPTVPlayer.components.iptvconfigmenu import IsSidecarEnabled, IsMediaNamingNormalized
from Plugins.Extensions.IPTVPlayer.tools.iptvtools import printDBG, printExc, GetDefaultLang
from Plugins.Extensions.IPTVPlayer.tools.iptvtypes import strwithmeta
from Plugins.Extensions.IPTVPlayer.tools.iptvnaming import normalizeMediathekTitle
from Plugins.Extensions.IPTVPlayer.tools.iptvwatchedhelper import IPTVWatchedHelper
from Plugins.Extensions.IPTVPlayer.tools.iptvwatchedfoldermixin import GenericFolderWatchedScraperMixin, GenericFolderWatchedHostMixin
from Plugins.Extensions.IPTVPlayer.libs.urlmetahelper import buildSidecarFromItem, applySidecarToLinks
from Plugins.Extensions.IPTVPlayer.libs.e2ijson import loads as json_loads, dumps as json_dumps
from Plugins.Extensions.IPTVPlayer.p2p3.UrlLib import urllib_quote
from Components.config import config, ConfigSelection, getConfigListEntry

config.plugins.iptvplayer.aljazeera_site = ConfigSelection(default='auto', choices=[
    ('auto', _('Auto')), ('ar', 'العربية (ajnet.me)'), ('en', 'English (aljazeera.com)')])


def GetConfigList():
    return [getConfigListEntry(_('Programme archive:'), config.plugins.iptvplayer.aljazeera_site)]


def gettytul():
    return 'https://www.aljazeera.com/'


class AlJazeera(GenericFolderWatchedScraperMixin, CBaseHostClass):

    SITES = {
        'ar': {'url': 'https://www.ajnet.me', 'wp': 'aja', 'account': '665001584001', 'player': 'nUW9Zv8wm',
               'categories': [('investigative', 'تحقيقات'), ('documentaries', 'وثائقيات'),
                              ('discussions', 'برامج حوارية'), ('digital', 'برامج رقمية')]},
        'en': {'url': 'https://www.aljazeera.com', 'wp': 'aje', 'account': '665003303001', 'player': '6tKQRAx7lu',
               'categories': []},
    }
    LIVE = [('Al Jazeera Arabic', 'https://live-hls-web-aja.getaj.net/AJA/index.m3u8'),
            ('Al Jazeera English', 'https://live-hls-web-aje-fa.getaj.net/AJE/index.m3u8'),
            ('Al Jazeera Mubasher', 'https://live-hls-web-ajm.getaj.net/AJM/index.m3u8')]
    PROGRAMS_PER_PAGE = 50
    EPISODES_PER_PAGE = 20

    def __init__(self):
        CBaseHostClass.__init__(self, {'history': 'AlJazeera', 'cookie': 'AlJazeera.cookie'})
        self.MAIN_URL = gettytul()
        self.DEFAULT_ICON_URL = 'https://www.aljazeera.com/images/logo_aje.png'
        self.HEADER = self.cm.getDefaultHeader(browser='chrome')
        self._policyKeys = {}
        self.watchedHelper = IPTVWatchedHelper('aljazeera')
        self.wfInitFolderCache()

    def site(self):
        lang = config.plugins.iptvplayer.aljazeera_site.value
        if lang == 'auto':
            lang = 'ar' if GetDefaultLang() == 'ar' else 'en'
        return self.SITES[lang]

    ###################################################
    # watched flag
    ###################################################
    def _getWatchedKeyForItem(self, cItem):
        try:
            if not isinstance(cItem, dict) or cItem.get('live'):
                return ''
            if cItem.get('type', '') == 'video':
                vid = cItem.get('video_id', '')
                return 'video:%s' % vid if vid else ''
            if cItem.get('category', '') == 'list_episodes' and cItem.get('program'):
                return 'folder:%s' % cItem['program']
        except Exception:
            printExc()
        return ''

    ###################################################
    # API
    ###################################################
    def graphql(self, operation, variables):
        site = self.site()
        url = '%s/graphql?wp-site=%s&operationName=%s&variables=%s&extensions=%%7B%%7D' % (
            site['url'], site['wp'], operation, urllib_quote(json_dumps(variables, separators=(',', ':'))))
        header = dict(self.HEADER)
        header.update({'Accept': 'application/json', 'Content-Type': 'application/json', 'wp-site': site['wp'],
                       'original-domain': site['url'].split('//', 1)[-1], 'Referer': site['url'] + '/'})
        sts, data = self.cm.getPage(url, {'header': header})
        if not sts:
            return {}
        try:
            return json_loads(data).get('data') or {}
        except Exception:
            printExc()
        return {}

    def fullUrl(self, url):
        if url and url.startswith('/'):
            return self.site()['url'] + url
        return url or ''

    ###################################################
    # lists
    ###################################################
    def listMainMenu(self):
        self.listsTab([{'category': 'list_live', 'title': _('Live')}], {'name': 'category'})
        for slug, title in self.site()['categories']:
            self.addDir({'name': 'category', 'category': 'list_programs', 'title': title, 'program_cat': slug})
        self.listsTab([{'category': 'list_programs', 'title': _('All programmes')}] + self.searchItems(), {'name': 'category'})

    def listLive(self, cItem):
        for title, url in self.LIVE:
            self.addVideo({'good_for_fav': True, 'title': title, 'url': url, 'live': True, 'desc': _('Live')})

    def addProgram(self, cItem, program):
        title = self.cleanHtmlStr(program.get('title', ''))
        link = program.get('link', '')
        slug = link.rstrip('/').rsplit('/', 1)[-1]
        if not title or not slug:
            return
        params = dict(cItem)
        params.update({'good_for_fav': True, 'name': 'category', 'category': 'list_episodes', 'title': title,
                       'program': slug, 'program_title': title, 'page': 0,
                       'icon': self.fullUrl((program.get('featuredImage') or {}).get('sourceUrl', '')),
                       'desc': self.cleanHtmlStr(program.get('excerpt', ''))})
        self.addDir(params)

    def listPrograms(self, cItem):
        page = cItem.get('page', 0)
        variables = {'quantity': self.PROGRAMS_PER_PAGE, 'offset': page * self.PROGRAMS_PER_PAGE}
        if cItem.get('program_cat'):
            variables['category'] = cItem['program_cat']
        programs = self.graphql('ArchipelagoProgramsQuery', variables).get('programs') or []
        for program in programs:
            self.addProgram(cItem, program)
        if len(programs) >= self.PROGRAMS_PER_PAGE:
            params = dict(cItem)
            params.update({'title': _('Next page'), 'page': page + 1})
            self.addMore(params)

    def listEpisodes(self, cItem):
        page = cItem.get('page', 0)
        articles = self.graphql('ArchipelagoEpisodesQuery', {'category': cItem['program'], 'quantity': self.EPISODES_PER_PAGE,
                                                             'offset': page * self.EPISODES_PER_PAGE}).get('articles') or []
        program = cItem.get('program_title', '')
        for article in articles:
            vid = (article.get('video') or {}).get('id', '')
            if not vid:
                continue
            title = self.episodeTitle(self.cleanHtmlStr(article.get('title', '')), program)
            date = (article.get('date') or '')[:10]
            duration = (article.get('video') or {}).get('duration', '')
            desc = '\n'.join(x for x in (date, duration, self.cleanHtmlStr(article.get('excerpt', ''))) if x)
            if IsMediaNamingNormalized() and program:
                # "Programme - Episode (YYYY-MM-DD)" for the download file name
                title = normalizeMediathekTitle('%s - %s' % (program, title), date=date)
            self.addVideo({'good_for_fav': True, 'title': title,
                           'url': self.fullUrl(article.get('link', '')), 'video_id': vid, 'date': date,
                           'icon': self.fullUrl((article.get('featuredImage') or {}).get('sourceUrl', '')), 'desc': desc})
        if len(articles) >= self.EPISODES_PER_PAGE:
            params = dict(cItem)
            params.update({'title': _('Next page'), 'page': page + 1})
            self.addMore(params)

    @staticmethod
    def episodeTitle(title, program):
        # episode titles mostly repeat the programme name ("ما وراء الخبر" يناقش ...)
        if program:
            for quoted in ('"%s"' % program, '“%s”' % program, program):
                if title.startswith(quoted):
                    title = title[len(quoted):]
                    break
        title = re.sub(r'^\s*[-|:–—ـ]+\s*', '', title).strip()
        return title or program

    def listSearch(self, cItem, searchPattern, searchType):
        # the site search is not open to API clients - match the programme names
        pattern = searchPattern.strip().lower()
        if not pattern:
            return
        page = 0
        while page < 10:
            programs = self.graphql('ArchipelagoProgramsQuery', {'quantity': 100, 'offset': page * 100}).get('programs') or []
            for program in programs:
                if pattern in (program.get('title') or '').lower():
                    self.addProgram(cItem, program)
            if len(programs) < 100:
                break
            page += 1

    ###################################################
    # links
    ###################################################
    def getPolicyKey(self, site):
        key = self._policyKeys.get(site['account'])
        if key:
            return key
        sts, data = self.cm.getPage('https://players.brightcove.net/%s/%s_default/index.min.js' % (site['account'], site['player']),
                                    {'header': self.HEADER})
        key = self.cm.ph.getSearchGroups(data, r'''policyKey\s*:\s*["']([^"']+)["']''')[0] if sts else ''
        if key:
            self._policyKeys[site['account']] = key
        return key

    def getLinksForVideo(self, cItem):
        printDBG('AlJazeera.getLinksForVideo [%s]' % cItem.get('url', ''))
        meta = {'User-Agent': self.HEADER['User-Agent']}
        if cItem.get('live'):
            return [{'name': cItem['title'], 'url': strwithmeta(cItem['url'], dict(meta, iptv_proto='m3u8')), 'need_resolve': 0}]
        vid = cItem.get('video_id', '')
        site = self.site()
        account = site['account']
        if not vid:
            # an article page: read the Brightcove embed from it
            sts, data = self.cm.getPage(cItem['url'], {'header': self.HEADER})
            m = re.search(r'players\.brightcove\.net/(\d+)/([A-Za-z0-9_-]+)_default/index\.html\?videoId=(\d+)', data or '')
            if not sts or not m:
                return []
            account, vid = m.group(1), m.group(3)
            site = dict(site, account=account, player=m.group(2))
        policyKey = self.getPolicyKey(site)
        if not policyKey:
            return []
        header = dict(self.HEADER, Accept='application/json;pk=%s' % policyKey, Origin='https://players.brightcove.net')
        sts, data = self.cm.getPage('https://edge.api.brightcove.com/playback/v1/accounts/%s/videos/%s' % (account, vid), {'header': header})
        if not sts:
            return []
        try:
            data = json_loads(data)
        except Exception:
            printExc()
            return []
        subTracks = []
        for track in data.get('text_tracks') or []:
            if track.get('kind') in ('captions', 'subtitles') and track.get('src'):
                lang = (track.get('srclang') or '').split('-')[0]
                subTracks.append({'title': track.get('label') or lang.upper(), 'url': track['src'], 'lang': lang, 'format': 'vtt'})
        if subTracks:
            meta['external_sub_tracks'] = subTracks
        mp4, hls = {}, ''
        for source in data.get('sources') or []:
            src = source.get('src', '')
            if not src.startswith('https'):
                continue
            if source.get('container') == 'MP4' and source.get('height'):
                mp4.setdefault(source['height'], src)
            elif source.get('type') == 'application/x-mpegURL' and not hls:
                hls = src
        urlTab = [{'name': 'MP4 %sp' % height, 'url': strwithmeta(mp4[height], meta), 'need_resolve': 0}
                  for height in sorted(mp4, reverse=True)]
        if hls:
            urlTab.append({'name': 'HLS', 'url': strwithmeta(hls, dict(meta, iptv_proto='m3u8')), 'need_resolve': 0})
        return applySidecarToLinks(urlTab, buildSidecarFromItem(cItem, IsSidecarEnabled()))

    def getArticleContent(self, cItem):
        return [{'title': cItem.get('title', ''), 'text': cItem.get('desc', ''),
                 'images': [{'title': '', 'url': cItem.get('icon') or self.DEFAULT_ICON_URL}], 'other_info': {}}]

    def handleService(self, index, refresh=0, searchPattern='', searchType=''):
        printDBG('AlJazeera.handleService start')
        CBaseHostClass.handleService(self, index, refresh, searchPattern, searchType)
        name = self.currItem.get('name', None)
        category = self.currItem.get('category', '')
        searchPattern = self.currItem.get('search_pattern', searchPattern)
        self.currList = []

        if name is None:
            self.listMainMenu()
        elif category == 'list_live':
            self.listLive(self.currItem)
        elif category == 'list_programs':
            self.listPrograms(self.currItem)
        elif category == 'list_episodes':
            self.listEpisodes(self.currItem)
        elif category in ('search', 'search_next_page'):
            cItem = dict(self.currItem)
            cItem.update({'search_item': False, 'name': 'category'})
            self.listSearch(cItem, searchPattern, searchType)
        elif category == 'search_history':
            self.listsHistory({'name': 'history', 'category': 'search'}, 'desc')
        else:
            printExc()

        CBaseHostClass.endHandleService(self, index, refresh)


class IPTVHost(GenericFolderWatchedHostMixin, CHostBase):

    def __init__(self):
        CHostBase.__init__(self, AlJazeera(), True, [])
        self.cachedRet = None
        self.refreshAfterWatchedFlagChange = False
        self.watchedHelper = IPTVWatchedHelper('aljazeera')

    def withArticleContent(self, cItem):
        return cItem.get('type', '') == 'video' and not cItem.get('live')

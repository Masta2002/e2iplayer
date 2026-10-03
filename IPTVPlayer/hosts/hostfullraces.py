# -*- coding: utf-8 -*-
# FullRaces (fullraces.com) - Formula 1 (sessions, archive 2000-2018), NASCAR, IndyCar, WSBK, WRC, F2, F3,
#   Formula E, F1 Academy and MotoGP ("Other") full race replays
# Site: uCoz catalogue like basketball-video.com / nfl-video.com (navigation groups, "?pageN" paging, /search/),
#   behind Cloudflare that only lets Chrome's TLS fingerprint through -> every page via curl-impersonate
# Race page: a player block with one button per source (ok.ru, Dailymotion parts, filemoon/byse) and/or
#   headings with hoster <iframe>s and "Part N" buttons (Dailymotion, vidara, ...). Resolved lazily in getVideoLinks.
# Last Modified: 03.10.2026 - new host (was a sub-menu of basketball-video.com): watched flag, name
#   normalisation, sidecar, search, INFO, curl-impersonate for the Cloudflare check
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
# "May 29-31, 2026", "July 30 - August 2, 2026" (rallies, race weekends): the first day counts
DATE_RANGE_RE = r'\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+(\d{1,2})\s*-\s*(?:(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+)?\d{1,2},?\s+(\d{4})\b'
YEAR_RE = r'\b((?:19|20)\d\d)\b'
LABEL_RE = r'\bFull (?:Race|Show)?\s*Replays?\b|\bFull Race\b|\bOnline Free\b'
# series: (pattern, name) - the first one found names the race, all of them are cut from the event name
SERIES = ((r'\bF1\s+Academy\b', 'F1 Academy'),
          (r'\bFormula\s*E\b', 'Formula E'),
          (r'\bFormula\s*2\b(?:\s+Championship)?|\bF2(?:\s+Championship)?\b', 'Formula 2'),
          (r'\bFormula\s*3\b(?:\s+Championship)?|\bF3(?:\s+Championship)?\b', 'Formula 3'),
          (r'\bFormula\s*(?:1|One)\b|\bF1\b', 'Formula 1'),
          (r'\bMotoGP\b', 'MotoGP'),
          (r'\bMoto2\b', 'Moto2'),
          (r'\bMoto3\b', 'Moto3'),
          (r'\bWSBK\b|\bWorldSBK\b|\bSuperbike World Championship\b', 'WorldSBK'),
          (r'\bWRC\b|\bWorld Rally Championship\b', 'WRC'),
          (r'\bNASCAR(?:\s+Cup\s+Series)?\b', 'NASCAR'),
          (r'\bIndy\s*Car\b', 'IndyCar'),
          (r'\bFormula\s*4\b', ''))
# a session at the start of the title or as its own " - " part ("RACE - F1 2026 - ...", "Qualifying Formula 1 ...")
SESSION_RE = (r'(?:Sprint\s+Qualifying|Sprint\s+Shootout|Sprint\s+Race|Feature\s+Race|Sprint|Qualifying|Race|'
              r'(?:1st|2nd|3rd|First|Second|Third)\s+Practice|Free\s+Practice\s*\d?|FP\d|Practice\s*\d?|Warm[- ]?Up|'
              r'Pre[- ]Race(?:\s+Show)?|Post[- ]Race(?:\s+Show)?|F1\s+Show|(?:Drivers\s+)?Press\s+Conference|Season\s+Review|Shakedown)')
# a short heading that only names the source ("Server #2", "Dailymotion", ...) - belongs to the heading above it
SOURCE_LABEL_RE = r'^(?:server\b|ok\b|ok\.ru|okru|dailymotion|filemoon|byse|vidara|luluvid|youtube|vk\b|backup|mirror|link\b|watch\b)'


def GetConfigList():
    return []


def gettytul():
    return 'https://fullraces.com/'


class FullRaces(GenericFolderWatchedScraperMixin, CBaseHostClass):

    FAV_FIELDS = ('name', 'category', 'type', 'url', 'title', 'icon', 'desc', 'raw_title', 'competition')

    def __init__(self):
        CBaseHostClass.__init__(self, {'history': 'fullraces.com', 'cookie': 'fullraces.cookie'})
        self.MAIN_URL = 'https://fullraces.com/'
        self.DEFAULT_ICON_URL = ''
        self.HEADER = self.cm.getDefaultHeader(browser='chrome')
        # Cloudflare there blocks every non-Chrome TLS fingerprint: curl-impersonate, no cookie needed
        self.defaultParams = {'header': self.HEADER, 'with_metadata': True, 'use_cookie': True, 'load_cookie': True, 'save_cookie': True,
                              'cookiefile': self.COOKIE_FILE, 'impersonate': True}
        self.watchedHelper = IPTVWatchedHelper('fullraces')
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
        return self.cm.getPageCFProtection(url, addParams, post_data)

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
        m = re.search(DATE_RANGE_RE, text or '', re.I) or re.search(DATE_RE, text or '', re.I)
        if m:
            return '%s-%02d-%02d' % (m.group(3), MONTHS[m.group(1).lower()[:3]], int(m.group(2)))
        m = re.search(DATE_NUM_RE, text or '')
        if m and 0 < int(m.group(2)) <= 12 and 0 < int(m.group(1)) <= 31:
            return '%s-%s-%s' % (m.group(3), m.group(2), m.group(1))
        return ''

    def _normTitle(self, title):
        # "RACE - F1 2026 - Azerbaijan Grand Prix - Full Race Replay - September 26, 2026 - Formula 1"
        #   -> "Formula 1 - Azerbaijan Grand Prix - Race (2026-09-26)"
        # "WRC Rally Japan - Full Race Replay - May 29-31, 2026 - World Rally Championship" -> "WRC - Rally Japan (2026-05-29)"
        # "2014 F1 Abu Dhabi Grand Prix Full Race Replay" -> "Formula 1 - Abu Dhabi Grand Prix (2014)"
        if not IsMediaNamingNormalized():
            return title
        try:
            date = self._parseDate(title)
            out = re.sub(r'\s*\|\s*', ' - ', title)
            out = re.sub(DATE_RANGE_RE, ' - ', out, flags=re.I)
            out = re.sub(DATE_RE, ' - ', out, flags=re.I)
            out = re.sub(DATE_NUM_RE, ' - ', out)
            out = re.sub(LABEL_RE, ' - ', out, flags=re.I)
            series = ''
            for pattern, name in SERIES:
                if name and re.search(pattern, re.sub(r'\bF1\s+Show\b', '', title, flags=re.I), re.I):
                    series = name
                    break
            # the session: at the very start or a " - " part of its own (never inside an event name like "Night Race")
            session = ''
            m = re.match(r'\s*(%s)(?=\s|$)' % SESSION_RE, out, re.I)
            if m:
                session = m.group(1)
                out = ' - ' + out[m.end():]
            parts = []
            for p in out.split(' - '):
                if not session and re.match(r'^\s*(%s)\s*$' % SESSION_RE, p, re.I):
                    session = p.strip()
                    continue
                parts.append(p)
            out = ' - '.join(parts)
            for pattern, name in SERIES:
                out = re.sub(pattern, ' ', out, flags=re.I)
            if not date:
                date = self.cm.ph.getSearchGroups(out, YEAR_RE)[0]
            out = re.sub(YEAR_RE, ' ', out)
            keep = []
            for p in out.split(' - '):
                p = re.sub(r'\s+', ' ', p).strip(' ,:-&')
                p = re.sub(r'^(?:of|the)\s+', '', p, flags=re.I)
                if p and p.lower() not in [k.lower() for k in keep]:
                    keep.append(p)
            if session.isupper():
                session = session.title()
            out = ' - '.join([x for x in [series] + keep + [re.sub(r'\s+', ' ', session)] if x]) or title
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
            if 'nofollow' in attrs or 'content-policy' in url:
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
        # top level links, then the "beefup" group (Formula 1 seasons) as sub folder
        top = re.sub(r'<li class="beefup2">.*?</ul>\s*</li>', '', nav, flags=re.S)
        links = self._navLinks(top)
        # MotoGP is only reachable through the "Other" category of its posts, not in the navigation
        if not [u for u, t in links if u.rstrip('/').endswith('/other')]:
            links.append((self.getFullUrl('/other'), 'MotoGP & Other'))
        for url, title in links:
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
        printDBG("FullRaces.listItems [%s]" % cItem['url'])
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
        return 0 < len(text) < 90 and not text.lower().startswith('disclaimer') and not set(text) <= set('-_=* ')

    def getLinksForVideo(self, cItem):
        printDBG("FullRaces.getLinksForVideo [%s]" % cItem['url'])
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
            # "Server #3" -> "Server #3 - bysesukior.com" (not for the site's own link pages)
            host = self.up.getHostName(url)
            if host and host not in self.getMainUrl() and not re.search(r'\b%s\b' % re.escape((host.split('.')[-2:-1] or [host])[0]), name, re.I):
                name = ' - '.join([x for x in (name, host) if x])
            urlTab.append({'name': name or host, 'url': strwithmeta(url, {'Referer': cItem['url']}), 'need_resolve': 1})

        # newer pages: a player block with one button per source ("OK.ru / Main", "Dailymotion 1 / Part 1", ...)
        for player in re.findall(r'<div class="gameplayer">(.*?)class="gp-foot"', body, re.S):
            heading = self.cleanHtmlStr(self.cm.ph.getDataBeetwenNodes(player, ('<h2', '>', 'gp-match'), ('</h2', '>'), False)[1])
            for url, inner in re.findall(r'<a[^>]+class="gp-src[^"]*"[^>]+href="([^"]+)"[^>]*>(.*?)</a>', player, re.S):
                source = self.cleanHtmlStr(self.cm.ph.getSearchGroups(inner, r'<b>(.*?)</b>')[0])
                note = self.cleanHtmlStr(self.cm.ph.getSearchGroups(inner, r'class="off">([^<]*)')[0])
                if note.lower() in ('main', 'playing'):
                    note = ''
                addLink(url, ' - '.join([x for x in (heading, source, note) if x]))
        body = re.sub(r'<div class="gameplayer">.*?class="gp-foot".*?</p>', '', body, flags=re.S)

        main = sub = ''
        # walk the page in order: a short paragraph names the following buttons / players; "Server #2" or
        # "Dailymotion" under a longer heading is added to it (no zero-width re.split - Python 2.7)
        for chunk in re.sub(r'(<p[\s>])', r'<!--split-->\1', body).split('<!--split-->'):
            para = self.cm.ph.getDataBeetwenNodes(chunk, ('<p', '>'), ('</p', '>'), False)[1]
            if para and '<br' not in para:
                heading = self.cleanHtmlStr(re.sub(r'<a[^>]+>.*?</a>', '', para, flags=re.S))
                if heading and set(heading) <= set('-_=* '):
                    main = sub = ''
                elif self._isLabel(heading):
                    if re.match(SOURCE_LABEL_RE, heading, re.I):
                        sub = heading
                    else:
                        main, sub = heading, ''
            anchors = re.findall(r'<a[^>]+class="su-button[^"]*"[^>]+href="([^"]+)"[^>]*>(.*?)</a>', chunk, re.S)
            frames = re.findall(r'<iframe[^>]+src="([^"]+)"', chunk, re.I)
            for url, text in anchors:
                text = self.cleanHtmlStr(text)
                if text.lower() == 'watch':
                    text = ''
                addLink(url, ' - '.join([x for x in (main, sub, text) if x]))
            for url in frames:
                addLink(url, ' - '.join([x for x in (main, sub) if x]))
        if not urlTab:
            SetIPTVPlayerLastHostError(_("No video sources found on this page (the replay may not be uploaded yet)."))
            return []
        # e.g. two players under one "Server #2" heading -> "(1)", "(2)"
        names = [item['name'] for item in urlTab]
        counter = {}
        for item in urlTab:
            if names.count(item['name']) > 1:
                counter[item['name']] = counter.get(item['name'], 0) + 1
                item['name'] = '%s (%d)' % (item['name'], counter[item['name']])
        synopsis = self.cleanHtmlStr(cItem.get('desc', ''))
        return applySidecarToLinks(urlTab, buildSidecarFromItem(cItem, IsSidecarEnabled(), synopsis))

    def getVideoLinks(self, videoUrl):
        printDBG("FullRaces.getVideoLinks [%s]" % videoUrl)
        videoUrl = strwithmeta(videoUrl)
        if not self.cm.isValidUrl(videoUrl):
            return []
        sidecar = sidecarFromUrlMeta(videoUrl, IsSidecarEnabled())
        url = videoUrl
        if 1 != self.up.checkHostSupport(url) and not self._isDirect(url):
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
        host = self.up.getHostName(url)
        if 1 == self.up.checkHostSupport(url):
            return decorateResolvedLinkItems(self.up.getVideoLinkExt(url), sidecar)
        if self._isDirect(url):
            # a plain MP4 / HLS file in the page
            return decorateResolvedLinkItems([{'name': self.up.getHostName(url), 'url': strwithmeta(url, {'User-Agent': self.HEADER['User-Agent']})}], sidecar)
        SetIPTVPlayerLastHostError(_("Hoster %s is not supported.") % host)
        return []

    def _isDirect(self, url):
        return re.search(r'\.(?:mp4|m3u8)(?:\?|$)', url.split('#')[0], re.I) is not None

    ###################################################
    # INFO
    ###################################################
    def getArticleContent(self, cItem):
        printDBG("FullRaces.getArticleContent [%s]" % cItem.get('url', ''))
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
            body = re.sub(r'<a[^>]+class="(?:su-button|gp-src).*?</a>', '', body, flags=re.S)
            body = re.sub(r'<(?:div|p)[^>]+class="gp-(?:load|foot)".*?</(?:div|p)>', '', body, flags=re.S)
            lines = []
            for para in re.findall(r'<(?:p|div)[^>]*>((?:(?!<(?:p|div)[\s>]).)*?)</(?:p|div)>', body, re.S):
                para = self.cleanHtmlStr(re.sub(r'<br\s*/?>', '[/br]', para))
                para = re.sub(r'^(?:\s*\[/br\])+|(?:\[/br\]\s*)+$', '', para).strip()
                if not para or set(para) <= set('-[/br] ') or para.lower().startswith('disclaimer') or re.match(SOURCE_LABEL_RE, para, re.I):
                    continue
                if para not in lines:
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
        printDBG("FullRaces.handleService name[%s] category[%s]" % (name, category))
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
        CHostBase.__init__(self, FullRaces(), True, [])
        self.cachedRet = None
        self.refreshAfterWatchedFlagChange = False
        self.watchedHelper = IPTVWatchedHelper('fullraces')

    def withArticleContent(self, cItem):
        return cItem.get('type') == 'video'

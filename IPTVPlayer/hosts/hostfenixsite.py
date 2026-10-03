# -*- coding: utf-8 -*-
# Last Modified: 03.10.2026 - rewrite for the current fenixsite.net (uCoz "movie-box" grids with
#   "?pageN" / "<cat>-N" pager and "?sort=N", POST /load/ search, title page player tabs:
#   voe / byse / vidara / vidsonic / streamcash folders + vsembed "Player CC" by IMDb id)
#   + watched flag / downloaded flag / name normalisation / sidecar / moviemeta INFO /
#   favourites. Shows are the series categories (/load/strane_serije/<show>/<id>).
import re

from Plugins.Extensions.IPTVPlayer.components.ihost import CBaseHostClass, CHostBase
from Plugins.Extensions.IPTVPlayer.components.iptvplayerinit import TranslateTXT as _, SetIPTVPlayerLastHostError
from Plugins.Extensions.IPTVPlayer.components.iptvconfigmenu import IsSidecarEnabled, IsMediaNamingNormalized
from Plugins.Extensions.IPTVPlayer.libs.e2ijson import dumps as json_dumps
from Plugins.Extensions.IPTVPlayer.libs.moviemeta import getMeta, getMetaByImdbId
from Plugins.Extensions.IPTVPlayer.libs.urlmetahelper import buildSidecarFromItem, applySidecarToLinks, sidecarFromUrlMeta, decorateResolvedLinkItems
from Plugins.Extensions.IPTVPlayer.tools.iptvnaming import formatSxxExx
from Plugins.Extensions.IPTVPlayer.tools.iptvtools import printDBG, printExc
from Plugins.Extensions.IPTVPlayer.tools.iptvtypes import strwithmeta
from Plugins.Extensions.IPTVPlayer.tools.iptvwatchedhelper import IPTVWatchedHelper
from Plugins.Extensions.IPTVPlayer.tools.iptvwatchedfoldermixin import GenericFolderWatchedScraperMixin, GenericFolderWatchedHostMixin


def GetConfigList():
    return []


def gettytul():
    return "https://www.fenixsite.net/"


# episode page of a show category: /load/strane_serije/<show>/<episode slug>/<cat id>-1-0-<entry id>
SHOW_EPISODE_RE = re.compile(r"/load/strane_serije/([a-z0-9_]+)/[^/]+/(\d+)-\d+-\d+-\d+")
# collection categories, not one show
NO_SHOW_SLUGS = ("mini_serije",)
EPISODE_TITLE_RE = re.compile(r"^(.*?)\s*\bS(\d{1,2})\s*E(\d{1,3})(?:\s*-\s*E?(\d{1,3}))?\s*$", re.I)
MOVIE_TITLE_RE = re.compile(r"^(.*?)\s*\((\d{4})\)\s*$")
SHOW_TITLE_RE = re.compile(r"^(.*?)\s*\((\d{4})[^)]*\)\s*$")
# hosters that are gone or that urlparser cannot play (netu/hqq/waaw)
DEAD_HOSTS = ("openload", "hqq.", "waaw.", "netu.")


class Fenixsite(GenericFolderWatchedScraperMixin, CBaseHostClass):
    # what identifies a row and is needed to open it again (desc carries views/rating, which change)
    FAV_FIELDS = ("name", "category", "type", "url", "title", "s_title", "season", "episode", "show_url",
                  "icon", "meta_type", "meta_title", "meta_year")

    def __init__(self):
        CBaseHostClass.__init__(self, {"history": "fenixsite", "cookie": "fenixsite.cookie"})
        self.HEADER = self.cm.getDefaultHeader(browser="chrome")
        self.defaultParams = {"header": self.HEADER, "use_cookie": True, "load_cookie": True, "save_cookie": True, "cookiefile": self.COOKIE_FILE}
        self.MAIN_URL = gettytul()
        self.MENU = [{"category": "list_items", "title": _("Movies") + " - " + _("Latest"), "url": self.getFullUrl("strani_filmovi")},
                     {"category": "list_items", "title": _("Movies") + " - " + _("Popular"), "url": self.getFullUrl("strani_filmovi?sort=12")},
                     {"category": "list_items", "title": _("Movies") + " - " + _("Top rated"), "url": self.getFullUrl("strani_filmovi?sort=6")},
                     {"category": "list_cats", "title": _("Genres"), "url": self.MAIN_URL, "cat_kind": "genre"},
                     {"category": "list_cats", "title": _("Years"), "url": self.MAIN_URL, "cat_kind": "year"},
                     {"category": "list_items", "title": _("Series") + " - " + _("Latest episodes"), "url": self.getFullUrl("strane_serije")},
                     {"category": "list_items", "title": _("Series") + " - " + _("Shows with new episodes"), "url": self.getFullUrl("strane_serije"), "mode": "shows"},
                     {"category": "list_items", "title": _("Series") + " - " + _("Popular"), "url": self.getFullUrl("strane_serije?sort=12")},
                     {"category": "list_items", "title": _("Mini series"), "url": self.getFullUrl("load/strane_serije/mini_serije/971")}] + self.searchItems()

        self.watchedHelper = IPTVWatchedHelper("fenixsite")
        self.wfInitFolderCache()

    ###################################################
    # watched flag
    ###################################################
    def _getWatchedKeyForItem(self, cItem):
        try:
            if not isinstance(cItem, dict) or cItem.get("is_next"):
                return ""
            url = str(cItem.get("url", "") or "").strip()
            if cItem.get("type", "") in ("video", "audio"):
                return "video:%s" % url if url else ""
            if cItem.get("category", "") == "fx_show":
                showUrl = str(cItem.get("show_url", "") or "").strip()
                return "series:%s" % showUrl if showUrl else ""
            return ""
        except Exception:
            printExc()
        return ""

    ###################################################
    # helpers
    ###################################################
    def getPage(self, baseUrl, addParams=None, post_data=None):
        if addParams is None:
            addParams = dict(self.defaultParams)
        sts, data = self.cm.getPage(baseUrl, addParams, post_data)
        if not sts and post_data is None:
            # the origin answers with Cloudflare 522 every few requests - one more try
            printDBG("Fenixsite.getPage retry [%s]" % baseUrl)
            sts, data = self.cm.getPage(baseUrl, addParams, post_data)
        return sts, data

    def _siteUrl(self, url, currUrl=None):
        # one spelling per page (the site mixes fenixsite.net and www.fenixsite.net)
        url = self.getFullUrl(url.replace("&amp;", "&"), currUrl)
        return re.sub(r"^https?://(?:www\.)?fenixsite\.(?:net|com)/", self.MAIN_URL, url)

    def _showUrl(self, url):
        match = SHOW_EPISODE_RE.search(url)
        if not match or match.group(1) in NO_SHOW_SLUGS:
            return ""
        return "%sload/strane_serije/%s/%s" % (self.MAIN_URL, match.group(1), match.group(2))

    def _splitShowTitle(self, title):
        match = SHOW_TITLE_RE.match(title)
        if match and match.group(1).strip():
            return match.group(1).strip(), match.group(2)
        return title, ""

    def _cleanTitle(self, title):
        return re.sub(r"\s+", " ", self.cleanHtmlStr(title)).strip()

    def _titleParams(self, title, url):
        # row title + naming fields from the site title ("Runner (2026)", "All American S08E06")
        epMatch = EPISODE_TITLE_RE.match(title)
        if epMatch and epMatch.group(1).strip() and ("/strane_serije/" in url or "/strani_filmovi/" not in url):
            sTitle, season, episode, lastEpisode = epMatch.groups()
            sTitle = sTitle.strip()
            if IsMediaNamingNormalized():
                tag = formatSxxExx(season, episode)
                if lastEpisode:
                    tag += "-E%02d" % int(lastEpisode)
                rowTitle = "%s - %s" % (sTitle, tag)
            else:
                rowTitle = title
            return {"title": rowTitle, "s_title": sTitle, "season": str(int(season)), "episode": str(int(episode)),
                    "meta_type": "tv", "meta_title": sTitle, "meta_year": ""}
        movieMatch = MOVIE_TITLE_RE.match(title)
        if movieMatch and movieMatch.group(1).strip():
            sTitle, year = movieMatch.group(1).strip(), movieMatch.group(2)
        else:
            sTitle, year = title, ""
        rowTitle = "%s (%s)" % (sTitle, year) if IsMediaNamingNormalized() and year else title
        return {"title": rowTitle, "s_title": sTitle, "meta_type": "movie", "meta_title": sTitle, "meta_year": year}

    ###################################################
    # lists
    ###################################################
    def listCategories(self, cItem):
        printDBG("Fenixsite.listCategories [%s]" % cItem.get("cat_kind", ""))
        sts, data = self.getPage(cItem["url"])
        if not sts:
            return
        data = self.cm.ph.getDataBeetwenMarkers(data, 'class="hm-list', 'class="hm-rkads', False)[1]
        wantYears = cItem.get("cat_kind", "") == "year"
        items = []
        seen = set()
        for url, slug, label in re.findall(r'<a href="([^"]*/load/strani_filmovi/([^/"]+)/\d+)"[^>]*>(.*?)</a>', data, re.DOTALL):
            if slug.isdigit() != wantYears:
                continue
            url = self._siteUrl(url)
            label = self._cleanTitle(label)
            if url in seen or not label:
                continue
            seen.add(url)
            items.append((label, url))
        if wantYears:
            items.reverse()
        for label, url in items:
            params = dict(cItem)
            params.update({"good_for_fav": True, "category": "list_items", "title": label, "url": url})
            self.addDir(params)

    def _parseEntries(self, data, currUrl):
        entries = []
        for item in data.split('<div id="entryID')[1:]:
            match = re.search(r'<div class="name">\s*<a href="([^"]+)" title="([^"]*)"', item)
            if not match:
                continue
            url = self._siteUrl(match.group(1), currUrl)
            title = self._cleanTitle(match.group(2))
            if not self.cm.isValidUrl(url) or not title:
                continue
            icon = self.cm.ph.getSearchGroups(item, r'data-src="([^"]+)"')[0] or self.cm.ph.getSearchGroups(item, r'<img[^>]+src="([^"]+)"')[0]
            badges = [self._cleanTitle(b) for b in re.findall(r'<span class="icon-voicer"[^>]*>(.*?)</span>', item, re.DOTALL)]
            meta = [self._cleanTitle(m) for m in re.findall(r"<span>(.*?)</span>", self.cm.ph.getDataBeetwenMarkers(item, 'class="metadata"', "</div>", False)[1], re.DOTALL)]
            entries.append({"url": url, "title": title, "icon": self._siteUrl(icon, currUrl) if icon else "",
                            "rating": self.cm.ph.getSearchGroups(item, r'fa-star"></span>\s*([0-9.]+)')[0],
                            "badges": [b for b in badges if b],
                            "date": meta[1] if len(meta) > 1 else "",
                            "text": self._cleanTitle(self.cm.ph.getDataBeetwenMarkers(item, 'class="texto">', "</div>", False)[1]),
                            "group": self._cleanTitle(self.cm.ph.getDataBeetwenMarkers(item, 'class="mta">', "</div>", False)[1])})
        return entries

    def _addEntries(self, cItem, entries, showsMode=False):
        cnt = 0
        seen = set()
        for entry in entries:
            url = entry["url"]
            showUrl = self._showUrl(url)
            if showsMode:
                # one folder per show of the listed episodes
                if not showUrl or showUrl in seen:
                    continue
                seen.add(showUrl)
                self._addShowDir(cItem, showUrl, entry["group"], entry["icon"])
                cnt += 1
                continue
            if url in seen:
                continue
            seen.add(url)
            desc = [d for d in [entry["date"]] + entry["badges"] if d]
            if entry["rating"] and entry["rating"] not in ("0", "0.0"):
                desc.append("%s/5" % entry["rating"])
            params = dict(cItem)
            for key in ("search_pattern", "mode", "season", "episode", "is_next", "cat_kind"):
                params.pop(key, None)
            params.update({"good_for_fav": True, "category": "fx_video", "url": url, "icon": entry["icon"],
                           "desc": " | ".join(desc) + ("[/br]" + entry["text"] if entry["text"] else ""),
                           "show_url": showUrl})
            params.update(self._titleParams(entry["title"], url))
            self.addVideo(params)
            cnt += 1
        return cnt

    def _addShowDir(self, cItem, showUrl, group, icon):
        sTitle, year = self._splitShowTitle(group or showUrl.rstrip("/").rsplit("/", 2)[-2].replace("_", " ").title())
        params = dict(cItem)
        for key in ("search_pattern", "mode", "is_next", "cat_kind"):
            params.pop(key, None)
        params.update({"good_for_fav": True, "category": "fx_show", "title": sTitle, "s_title": sTitle,
                       "url": showUrl + "?sort=3", "show_url": showUrl, "icon": icon, "desc": year,
                       "meta_type": "tv", "meta_title": sTitle, "meta_year": year})
        self.addDir(params)

    def _addNextPage(self, cItem, data, currUrl):
        nextPage = self.cm.ph.getSearchGroups(data, r'<a class="swchItem swchItem-next" href="([^"]+)"')[0]
        if not nextPage:
            return
        nextUrl = self._siteUrl(nextPage, currUrl)
        if nextUrl != currUrl:
            params = dict(cItem)
            params.update({"good_for_fav": False, "is_next": True, "title": _("Next page"), "url": nextUrl})
            self.addDir(params)

    def listItems(self, cItem):
        printDBG("Fenixsite.listItems |%s|" % cItem.get("url", ""))
        url = cItem["url"]
        sts, data = self.getPage(url)
        if not sts:
            return
        cnt = self._addEntries(cItem, self._parseEntries(data, url), cItem.get("mode", "") == "shows")
        if cnt or cItem.get("mode", "") == "shows":
            self._addNextPage(cItem, data, url)

    def listShow(self, cItem):
        printDBG("Fenixsite.listShow |%s|" % cItem.get("url", ""))
        url = cItem["url"]
        sts, data = self.getPage(url)
        if not sts:
            return
        if self._addEntries(cItem, self._parseEntries(data, url)):
            self._addNextPage(cItem, data, url)

    def listSearchResult(self, cItem, searchPattern, searchType):
        printDBG("Fenixsite.listSearchResult [%s]" % searchPattern)
        # uCoz module search, at most 40 hits, no pager
        sts, data = self.getPage(self.getFullUrl("load/"), None, {"query": searchPattern, "a": "2"})
        if not sts:
            return
        entries = self._parseEntries(data, self.getFullUrl("load/"))
        cItem = dict(cItem)
        cItem.pop("search_pattern", None)
        # the shows of the found episodes first: they hold all episodes, the search only 40
        self._addEntries(cItem, entries, True)
        self._addEntries(cItem, entries)

    ###################################################
    # title page
    ###################################################
    def _parseTitlePage(self, data):
        info = {"title": "", "desc": "", "poster": "", "year": "", "imdb": "", "genres": [], "released": "", "trailer": ""}
        info["title"] = self._cleanTitle(self.cm.ph.getDataBeetwenMarkers(data, "<h1>", "</h1>", False)[1])
        match = re.search(r'<div class="description">\s*<div class="title[^"]*">[^<]*</div>(.*?)</div>', data, re.DOTALL)
        info["desc"] = self._cleanTitle(match.group(1)) if match else ""
        poster = self.cm.ph.getSearchGroups(self.cm.ph.getDataBeetwenMarkers(data, 'class="movie-left"', 'class="addto-action"', False)[1], r'<img[^>]+src="([^"]+)"')[0]
        info["poster"] = self._siteUrl(poster) if poster else ""
        info["imdb"] = self.cm.ph.getSearchGroups(data, r"/embed/(tt\d+)")[0]
        info["released"] = self._cleanTitle(self.cm.ph.getSearchGroups(data, r'<li class="release">[^<]*<span>([^<]+)</span>')[0])
        info["trailer"] = self.cm.ph.getSearchGroups(data, r'href="(https?://www\.youtube\.com/embed/[^"]+)"[^>]*movie-trailer')[0]
        for label in re.findall(r'class="entAllCats">([^<]+)</a>', data):
            label = label.strip()
            if re.match(r"^\d{4}$", label):
                info["year"] = info["year"] or label
            elif label and label not in info["genres"]:
                info["genres"].append(label)
        if not info["year"]:
            info["year"] = self.cm.ph.getSearchGroups(info["title"], r"\((\d{4})\)\s*$")[0]
        return info

    ###################################################
    # links
    ###################################################
    def _streamcashLinks(self, folderUrl, label, referer):
        # a streamcash.to folder (whole season in one post) -> one link per episode
        links = []
        sts, data = self.cm.getPage(folderUrl, {"header": dict(self.HEADER, Referer=referer)})
        if not sts:
            return links
        base = re.match(r"^(https?://[^/]+)", folderUrl).group(1)
        for href, body in re.findall(r'<a[^>]+href="(/watch/[^"]+)"[^>]*class="v-card"[^>]*>(.*?)</a>', data, re.DOTALL):
            name = self._cleanTitle(body) or href.rsplit("/", 1)[-1]
            links.append({"name": "%s - %s" % (label, name), "url": strwithmeta(base + href, {"Referer": folderUrl}), "need_resolve": 1})
        return links

    def getLinksForVideo(self, cItem):
        printDBG("Fenixsite.getLinksForVideo [%s]" % cItem.get("url", ""))
        pageUrl = cItem.get("url", "")
        if not self.cm.isValidUrl(pageUrl):
            return []
        sts, data = self.getPage(pageUrl)
        if not sts:
            return []
        sidecarTxt = self._parseTitlePage(data)["desc"]

        labels = {}
        for tabId, label in re.findall(r'<li data-id="([^"]+)"[^>]*>\s*<span class="title">([^<]*)<', data):
            labels[tabId] = self._cleanTitle(label)
        players = self.cm.ph.getDataBeetwenMarkers(data, 'id="cn-content"', 'class="player-control"', False)[1]

        urltab = []
        lastTab = []
        skipped = []
        seen = set()
        for tabId, body in re.findall(r'<div class="film-content[^"]*" id="([^"]+)">(.*?)</div>', players, re.DOTALL):
            frame = self.cm.ph.getSearchGroups(body, r'<iframe[^>]+src="([^"]+)"')[0].replace("&amp;", "&").strip()
            if not frame and re.search(r'<div id="07b0[0-9a-f]+"', body):
                skipped.append("netu")  # hex-coded Netu player div
            if frame.startswith("//"):
                frame = "https:" + frame
            if not self.cm.isValidUrl(frame) or frame in seen:
                continue
            seen.add(frame)
            label = labels.get(tabId, "")
            domain = self.up.getDomain(frame)
            if any(dead in domain for dead in DEAD_HOSTS):
                printDBG("Fenixsite: skip dead hoster [%s]" % frame)
                skipped.append(domain)
                continue
            if "vsembed." in domain and not re.search(r"/embed/tt\d+", frame):
                continue  # "Player CC" without IMDb id
            if self.up.checkHostSupport(frame) != 1:
                printDBG("Fenixsite: no urlparser support [%s]" % frame)
                skipped.append(domain)
                continue
            if "streamcash." in domain and "/f/" in frame:
                urltab.extend(self._streamcashLinks(frame, label or domain, pageUrl))
                continue
            hostName = self.up.getHostName(frame)
            link = {"name": "%s (%s)" % (label, hostName) if label else hostName, "url": strwithmeta(frame, {"Referer": self.MAIN_URL}), "need_resolve": 1}
            # "Player CC" (vsembed / vidsrc) is the English source without the site's subtitles: last
            (lastTab if "vsembed." in domain else urltab).append(link)
        urltab.extend(lastTab)
        if not urltab and skipped:
            SetIPTVPlayerLastHostError(_("This title is only available from hosters that are not supported: %s") % ", ".join(sorted(set(skipped))))
        return applySidecarToLinks(urltab, buildSidecarFromItem(cItem, IsSidecarEnabled(), sidecarTxt))

    def getVideoLinks(self, videoUrl):
        printDBG("Fenixsite.getVideoLinks [%s]" % videoUrl)
        if self.cm.isValidUrl(videoUrl):
            sidecar = sidecarFromUrlMeta(videoUrl, IsSidecarEnabled())
            return decorateResolvedLinkItems(self.up.getVideoLinkExt(videoUrl), sidecar)
        return []

    ###################################################
    # info / favourites
    ###################################################
    def getArticleContent(self, cItem):
        printDBG("Fenixsite.getArticleContent [%s]" % cItem.get("url", ""))
        mediaType = cItem.get("meta_type", "")
        info = {"title": "", "desc": "", "poster": "", "year": "", "imdb": "", "genres": [], "released": "", "trailer": ""}
        showDesc = ""
        pageUrl = cItem.get("url", "")
        if cItem.get("category", "") == "fx_show":
            # the show category page only has the story; the IMDb id sits on its episode pages
            sts, data = self.getPage(pageUrl)
            if sts:
                showDesc = self._cleanTitle(self.cm.ph.getSearchGroups(data, r'<div class="rkads-inner">\s*<div class="title">[^<]*</div>\s*<p class="description">(.*?)</p>')[0])
                showDesc = re.sub(r"^Bioskop\s+Strane serije\s*", "", showDesc)
                entries = self._parseEntries(data, pageUrl)
                pageUrl = entries[0]["url"] if entries else ""
            else:
                pageUrl = ""
        if self.cm.isValidUrl(pageUrl):
            sts, data = self.getPage(pageUrl)
            if sts:
                info = self._parseTitlePage(data)
        meta = {}
        try:
            if info["imdb"]:
                meta = getMetaByImdbId(mediaType, info["imdb"])
            if not meta:
                meta = getMeta(mediaType, cItem.get("meta_title", "") or cItem.get("s_title", ""), cItem.get("meta_year", "") or (info["year"] if mediaType == "movie" else ""))
        except Exception:
            printExc()
            meta = {}
        otherInfo = dict(meta.get("info", {}) or {})
        if info["genres"]:
            otherInfo.setdefault("genres", ", ".join(info["genres"]))
        if info["year"] and mediaType == "movie":
            otherInfo.setdefault("year", info["year"])
        if info["released"]:
            otherInfo.setdefault("released", info["released"])
        siteText = showDesc or info["desc"] or cItem.get("desc", "")
        text = meta.get("plot", "") or siteText
        icon = meta.get("poster", "") or info["poster"] or cItem.get("icon", "")
        return [{"title": cItem.get("title", ""), "text": text,
                 "images": [{"title": "", "url": icon}] if icon else [],
                 "other_info": otherInfo}]

    def getFavouriteData(self, cItem):
        try:
            if cItem.get("meta_type"):
                return json_dumps(dict((key, cItem[key]) for key in self.FAV_FIELDS if key in cItem))
        except Exception:
            printExc()
        return CBaseHostClass.getFavouriteData(self, cItem)

    def handleService(self, index, refresh=0, searchPattern="", searchType=""):
        CBaseHostClass.handleService(self, index, refresh, searchPattern, searchType)
        name = self.currItem.get("name", "")
        category = self.currItem.get("category", "")
        printDBG("Fenixsite.handleService name[%s] category[%s]" % (name, category))
        self.currList = []
        if name is None:
            self.listsTab(self.MENU, {"name": "category"})
        elif category == "list_items":
            self.listItems(self.currItem)
        elif category == "list_cats":
            self.listCategories(self.currItem)
        elif category == "fx_show":
            self.listShow(self.currItem)
        elif category in ["search", "search_next_page"]:
            cItem = dict(self.currItem)
            cItem.update({"search_item": False, "name": "category"})
            self.listSearchResult(cItem, searchPattern, searchType)
        elif category == "search_history":
            self.listsHistory({"name": "history", "category": "search"}, "desc", _("Type: "))
        else:
            printExc()
        CBaseHostClass.endHandleService(self, index, refresh)


class IPTVHost(GenericFolderWatchedHostMixin, CHostBase):
    def __init__(self):
        CHostBase.__init__(self, Fenixsite(), True, [])
        self.cachedRet = None
        self.refreshAfterWatchedFlagChange = False
        self.watchedHelper = IPTVWatchedHelper("fenixsite")

    def withArticleContent(self, cItem):
        return bool(cItem.get("meta_type"))

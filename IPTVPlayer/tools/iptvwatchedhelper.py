# -*- coding: utf-8 -*-
# added: 06.08.2026 - central watched helper for normal items, host lists and favourites, file based watched flag handling via hashed keys, item/list/host state updates, favourite hash synchronization, season/series parent propagation for episode items, grouped debug call handling, central config based write protection, custom menu action handling (mark/unmark watched via MENU key), incl. generic group/parent recompute helpers (recomputeGroupWatched/recomputeAllGroupsWatched) for season/series propagation on unmark - Kamikaze24
###################################################
# LOCAL import
###################################################
from Plugins.Extensions.IPTVPlayer.tools.iptvtools import printDBG, printExc, GetFavouritesDir, mkdirs, touch, rm
from Plugins.Extensions.IPTVPlayer.libs.crypto.hash.md5Hash import MD5
from Plugins.Extensions.IPTVPlayer.components.iptvplayerinit import TranslateTXT as _
from Plugins.Extensions.IPTVPlayer.components.ihost import RetHost, CDisplayListItem
from Plugins.Extensions.IPTVPlayer.components.iptvchoicebox import IPTVChoiceBoxItem
###################################################
from Plugins.Extensions.IPTVPlayer.p2p3.pVer import isPY2
###################################################

###################################################
# FOREIGN import
###################################################
from Tools.Directories import fileExists
from binascii import hexlify
import os
from Components.config import config


class IPTVWatchedHelper(object):

    def __init__(self, hostName=''):
        self.hostName = str(hostName or '')
        self._favouritesBaseDir = None
        self._watchedBaseDir = None
        self._ensuredDirs = {}
        self._debugCalls = {}
        self._debugEnabled = True
        self._lastRet = None
        self._lastCurrList = None
        self._lastKeyProvider = None

    ###################################################
    # debug helpers
    ###################################################
    def _dbgCall(self, name):
        try:
            if not self._debugEnabled:
                return
            self._debugCalls[name] = self._debugCalls.get(name, 0) + 1
        except Exception:
            printExc()

    def dumpDebugCalls(self, prefix='IPTVWatchedHelper'):
        try:
            if not self._debugEnabled or self._debugCalls == {}:
                return
            keys = sorted(self._debugCalls.keys())
            parts = []
            for key in keys:
                parts.append('%s.%s x%d' % (prefix, key, self._debugCalls[key]))
            printDBG(' | '.join(parts))
            self._debugCalls = {}
        except Exception:
            printExc()

    def setDebugEnabled(self, enabled):
        try:
            self._debugEnabled = bool(enabled)
        except Exception:
            printExc()

    ###################################################
    # normalization helpers
    ###################################################
    def _normalizeKey(self, watchedKey):
        try:
            watchedKey = str(watchedKey or '').strip()
            return watchedKey
        except Exception:
            printExc()
        return ''

    def _normalizeHostName(self, hostName=None):
        try:
            if hostName in [None, '']:
                hostName = self.hostName
            hostName = str(hostName or '').strip()
            return hostName
        except Exception:
            printExc()
        return ''

    def _hashString(self, value):
        try:
            hashAlg = MD5()
            hashData = hexlify(hashAlg(str(value or '')))
            if not isPY2():
                hashData = hashData.decode()
            return hashData
        except Exception:
            printExc()
        return ''

    def _setItemWatchedFlag(self, item, value):
        try:
            if isinstance(item, dict):
                item['isWatched'] = value
            else:
                item.isWatched = value
        except Exception:
            printExc()

    ###################################################
    # path helpers
    ###################################################
    def _getFavouritesBaseDir(self):
        try:
            if self._favouritesBaseDir is None:
                self._favouritesBaseDir = GetFavouritesDir('').rstrip('/')
            return self._favouritesBaseDir
        except Exception:
            printExc()
        return ''

    def _getWatchedBaseDir(self):
        try:
            if self._watchedBaseDir is None:
                baseDir = self._getFavouritesBaseDir()
                if baseDir == '':
                    return ''
                self._watchedBaseDir = os.path.join(baseDir, 'IPTVWatched')
            return self._watchedBaseDir
        except Exception:
            printExc()
        return ''

    ###################################################
    # config helpers
    ###################################################
    def isMarkingAllowed(self):
        try:
            return bool(config.plugins.iptvplayer.favourites_use_watched_flag.value)
        except Exception:
            printExc()
        return False

    ###################################################
    # watched file helpers
    ###################################################
    def getWatchedFilePath(self, watchedKey):
        self._dbgCall('getWatchedFilePath')
        try:
            watchedKey = self._normalizeKey(watchedKey)
            hostName = self._normalizeHostName()
            if watchedKey == '' or hostName == '':
                return ''
            hashData = self._hashString(watchedKey)
            if hashData == '':
                return ''
            baseDir = self._getWatchedBaseDir()
            if baseDir == '':
                return ''
            return os.path.join(baseDir, hostName, '.%s.iptvhash' % hashData)
        except Exception:
            printExc()
        return ''

    def _ensureWatchedDir(self, hostName=None):
        try:
            hostName = self._normalizeHostName(hostName)
            if hostName == '':
                return False
            dirPath = os.path.join(self._getWatchedBaseDir(), hostName)
            if dirPath == '':
                return False
            if self._ensuredDirs.get(dirPath, False):
                return True
            sts = mkdirs(dirPath)
            if sts:
                self._ensuredDirs[dirPath] = True
            return sts
        except Exception:
            printExc()
        return False

    ###################################################
    # watched state helpers
    ###################################################
    def isWatched(self, watchedKey):
        self._dbgCall('isWatched')
        try:
            flagFilePath = self.getWatchedFilePath(watchedKey)
            if flagFilePath != '':
                return fileExists(flagFilePath)
        except Exception:
            printExc()
        return False

    def markItemWatched(self, item, watchedKey):
        self._dbgCall('markItemWatched')
        try:
            if not self.isMarkingAllowed():
                return False
            watchedKey = self._normalizeKey(watchedKey)
            if watchedKey == '':
                return False
            if not self._ensureWatchedDir():
                return False
            flagFilePath = self.getWatchedFilePath(watchedKey)
            if flagFilePath == '':
                return False
            if touch(flagFilePath):
                self._setItemWatchedFlag(item, True)
                return True
        except Exception:
            printExc()
        return False

    def unmarkItemWatched(self, item, watchedKey):
        self._dbgCall('unmarkItemWatched')
        try:
            watchedKey = self._normalizeKey(watchedKey)
            if watchedKey == '':
                return False
            flagFilePath = self.getWatchedFilePath(watchedKey)
            if flagFilePath == '':
                return False
            if rm(flagFilePath):
                self._setItemWatchedFlag(item, False)
                return True
        except Exception:
            printExc()
        return False

    ###################################################
    # item update helpers
    ###################################################
    def updateItemFlag(self, item, watchedKey):
        self._dbgCall('updateItemFlag')
        try:
            item['isWatched'] = self.isWatched(watchedKey)
        except Exception:
            printExc()
            try:
                item['isWatched'] = False
            except Exception:
                printExc()
        return item

    def updateListFlags(self, itemList, keyProvider):
        self._dbgCall('updateListFlags')
        try:
            for item in itemList:
                try:
                    watchedKey = keyProvider(item)
                except Exception:
                    watchedKey = ''
                    printExc()
                if watchedKey == '':
                    try:
                        item['isWatched'] = False
                    except Exception:
                        printExc()
                else:
                    self.updateItemFlag(item, watchedKey)
        except Exception:
            printExc()
        return itemList

    def updateHostItemFlag(self, host, cItem, keyProvider):
        self._dbgCall('updateHostItemFlag')
        try:
            watchedKey = keyProvider(cItem)
            if watchedKey == '':
                cItem['isWatched'] = False
            else:
                self.updateItemFlag(cItem, watchedKey)
        except Exception:
            printExc()
        return cItem

    def updateHostListFlags(self, host, itemList, keyProvider):
        self._dbgCall('updateHostListFlags')
        try:
            self.updateListFlags(itemList, keyProvider)
        except Exception:
            printExc()
        self.dumpDebugCalls()
        return itemList

    def updateParentWatchedState(self, parentItem, childItems, keyProvider):
        self._dbgCall('updateParentWatchedState')
        try:
            if not isinstance(parentItem, dict):
                return False
            parentKey = keyProvider(parentItem)
            if parentKey == '':
                return False
            childKeys = []
            for childItem in childItems or []:
                try:
                    childKey = keyProvider(childItem)
                except Exception:
                    printExc()
                    childKey = ''
                if childKey != '':
                    childKeys.append(childKey)
            if len(childKeys) == 0:
                return False
            allWatched = all(self.isWatched(childKey) for childKey in childKeys)
            if allWatched:
                self.markItemWatched(parentItem, parentKey)
            else:
                self.unmarkItemWatched(parentItem, parentKey)
            return True
        except Exception:
            printExc()
        return False

    def markHostItemAsWatched(self, host, cItem, keyProvider):
        self._dbgCall('markHostItemAsWatched')
        try:
            if not self.isMarkingAllowed():
                return False
            watchedKey = keyProvider(cItem)
            if watchedKey != '':
                self.markItemWatched(cItem, watchedKey)
            return True
        except Exception:
            printExc()
        return False

    def unmarkHostItemAsWatched(self, host, cItem, keyProvider):
        self._dbgCall('unmarkHostItemAsWatched')
        try:
            watchedKey = keyProvider(cItem)
            if watchedKey != '':
                self.unmarkItemWatched(cItem, watchedKey)
            if isinstance(cItem, dict):
                seriesUrl = str(cItem.get('series_url', '') or '').strip()
                seasonNum = str(cItem.get('season_num', '') or '').strip()
                if seriesUrl != '' and seasonNum != '':
                    seasonItem = {'category': 'list_episodes', 'url': cItem.get('url', ''), 'series_url': seriesUrl, 'season_num': seasonNum}
                    seasonKey = keyProvider(seasonItem)
                    if seasonKey != '':
                        self.unmarkItemWatched(seasonItem, seasonKey)
                if seriesUrl != '':
                    seriesItem = {'category': 'list_seasons', 'url': seriesUrl}
                    seriesKey = keyProvider(seriesItem)
                    if seriesKey != '':
                        self.unmarkItemWatched(seriesItem, seriesKey)
            return True
        except Exception:
            printExc()
        return False

    ###################################################
    # favourite helpers
    ###################################################
    def getFavouriteHashData(self, hostName, displayItem):
        self._dbgCall('getFavouriteHashData')
        try:
            hostName = self._normalizeHostName(hostName)
            if hostName == '' or displayItem is None:
                return None
            hashSrc = '%s_%s' % (str(displayItem.name), str(displayItem.type))
            hashData = self._hashString(hashSrc)
            if hashData == '':
                return None
            return (hostName, hashData)
        except Exception:
            printExc()
        return None

    def getFavouriteHashFilePath(self, hostName, displayItem):
        self._dbgCall('getFavouriteHashFilePath')
        try:
            hashData = self.getFavouriteHashData(hostName, displayItem)
            if hashData is None:
                return ''
            baseDir = self._getWatchedBaseDir()
            if baseDir == '':
                return ''
            return os.path.join(baseDir, hashData[0], '.%s.iptvhash' % hashData[1])
        except Exception:
            printExc()
        return ''

    def isFavouriteItemWatched(self, hostName, displayItem):
        self._dbgCall('isFavouriteItemWatched')
        try:
            flagFilePath = self.getFavouriteHashFilePath(hostName, displayItem)
            if flagFilePath != '':
                return fileExists(flagFilePath)
        except Exception:
            printExc()
        return False

    def markFavouriteItemWatched(self, hostName, displayItem):
        self._dbgCall('markFavouriteItemWatched')
        try:
            if not self.isMarkingAllowed():
                return False
            hostName = self._normalizeHostName(hostName)
            if hostName == '' or displayItem is None:
                return False
            if not self._ensureWatchedDir(hostName):
                return False
            flagFilePath = self.getFavouriteHashFilePath(hostName, displayItem)
            if flagFilePath == '':
                return False
            return touch(flagFilePath)
        except Exception:
            printExc()
        return False

    def unmarkFavouriteItemWatched(self, hostName, displayItem):
        self._dbgCall('unmarkFavouriteItemWatched')
        try:
            flagFilePath = self.getFavouriteHashFilePath(hostName, displayItem)
            if flagFilePath == '':
                return False
            return rm(flagFilePath)
        except Exception:
            printExc()
        return False

    ###################################################
    # ret/favourite sync helpers
    ###################################################
    def updateFavouriteDisplayItemFlag(self, hostName, displayItem):
        self._dbgCall('updateFavouriteDisplayItemFlag')
        try:
            displayItem.isWatched = self.isFavouriteItemWatched(hostName, displayItem)
        except Exception:
            printExc()
        return displayItem

    def updateFavouriteRetHostFlags(self, ret, hostNameProvider):
        self._dbgCall('updateFavouriteRetHostFlags')
        try:
            if ret is None:
                return ret
            if not hasattr(ret, 'value') or ret.value is None:
                return ret
            for idx in range(len(ret.value)):
                try:
                    hostName = hostNameProvider(idx, ret.value[idx])
                except Exception:
                    hostName = ''
                    printExc()
                if hostName != '':
                    self.updateFavouriteDisplayItemFlag(hostName, ret.value[idx])
        except Exception:
            printExc()
        return ret

    def fixHostRet(self, ret, currList, keyProvider, hostNameProvider):
        self._dbgCall('fixHostRet')
        try:
            ret = self.updateFavouriteRetHostFlags(ret, hostNameProvider)
        except Exception:
            printExc()
        try:
            if ret is None or not hasattr(ret, 'value') or ret.value is None:
                self.dumpDebugCalls()
                return ret
            for idx in range(len(ret.value)):
                if currList is not None and idx < len(currList):
                    try:
                        watchedKey = keyProvider(currList[idx])
                        if watchedKey != '':
                            ret.value[idx].isWatched = self.isWatched(watchedKey)
                    except Exception:
                        printExc()
        except Exception:
            printExc()
        self._lastRet = ret
        self._lastCurrList = currList
        self._lastKeyProvider = keyProvider
        self.dumpDebugCalls()
        return ret

    def syncFavouriteFromRet(self, cachedRet, index, hostNameProvider):
        self._dbgCall('syncFavouriteFromRet')
        try:
            if cachedRet is None or not hasattr(cachedRet, 'value'):
                return False
            if index < 0 or index >= len(cachedRet.value):
                return False
            displayItem = cachedRet.value[index]
            hostName = hostNameProvider(index, displayItem)
            if self.markFavouriteItemWatched(hostName, displayItem):
                cachedRet.value[index].isWatched = True
                self.dumpDebugCalls()
                return True
        except Exception:
            printExc()
        return False

    ###################################################
    # menu custom action helpers (watched toggle via MENU key)
    ###################################################
    def getCustomActionsForRet(self, ret, currList, keyProvider, Index=0):
        self._dbgCall('getCustomActionsForRet')
        retCode = RetHost.ERROR
        retlist = []
        try:
            if self.isMarkingAllowed():
                if ret is not None and hasattr(ret, 'value') and ret.value is not None and 0 <= Index < len(ret.value):
                    displayItem = ret.value[Index]
                    watchedKey = ''
                    itemDict = None
                    if keyProvider is not None and currList is not None and Index < len(currList):
                        try:
                            itemDict = currList[Index]
                            watchedKey = keyProvider(itemDict)
                        except Exception:
                            watchedKey = ''
                            printExc()
                    isGroupItem = isinstance(itemDict, dict) and itemDict.get('category', '') in ['list_episodes', 'list_seasons']
                    if displayItem.type in [CDisplayListItem.TYPE_VIDEO, CDisplayListItem.TYPE_AUDIO] or isGroupItem:
                        if watchedKey != '':
                            if displayItem.isWatched:
                                params = IPTVChoiceBoxItem(_('Unset watched'), "", {'action': 'unset_watched_flag', 'item_index': Index, 'watched_key': watchedKey})
                            else:
                                params = IPTVChoiceBoxItem(_('Set watched'), "", {'action': 'set_watched_flag', 'item_index': Index, 'watched_key': watchedKey})
                            retlist.append(params)
                            retCode = RetHost.OK
                            self._lastRet = ret
                            self._lastCurrList = currList
                            self._lastKeyProvider = keyProvider
        except Exception:
            printExc()
        self.dumpDebugCalls()
        return RetHost(retCode, value=retlist)

    def performCustomAction(self, privateData):
        self._dbgCall('performCustomAction')
        retCode = RetHost.ERROR
        retlist = []
        try:
            if self.isMarkingAllowed():
                ret = self._lastRet
                watchedKey = privateData.get('watched_key', '')
                Index = privateData.get('item_index', -1)
                action = privateData.get('action', '')
                if ret is not None and hasattr(ret, 'value') and watchedKey != '' and 0 <= Index < len(ret.value):
                    displayItem = ret.value[Index]

                    if action == 'unset_watched_flag':
                        normalChanged = self.unmarkItemWatched(displayItem, watchedKey)
                        favouriteChanged = self.unmarkFavouriteItemWatched(self.hostName, displayItem)
                        if normalChanged or favouriteChanged:
                            retCode = RetHost.OK

                    elif action == 'set_watched_flag':
                        normalChanged = self.markItemWatched(displayItem, watchedKey)
                        favouriteChanged = self.markFavouriteItemWatched(self.hostName, displayItem)
                        if normalChanged or favouriteChanged:
                            retCode = RetHost.OK

                    if retCode == RetHost.OK:
                        retlist = ['refresh']
        except Exception:
            printExc()
        self.dumpDebugCalls()
        return RetHost(retCode, value=retlist)

    ###################################################
    # group/parent recompute helpers (e.g. season <- episodes)
    ###################################################
    def recomputeGroupWatched(self, childItems, keyProvider, parentItem):
        self._dbgCall('recomputeGroupWatched')
        try:
            childKeys = []
            for child in childItems or []:
                try:
                    childKey = keyProvider(child)
                except Exception:
                    childKey = ''
                    printExc()
                if childKey != '':
                    childKeys.append(childKey)
            parentKey = keyProvider(parentItem)
            if parentKey == '':
                return False
            if len(childKeys) == 0:
                return self.unmarkItemWatched(parentItem, parentKey)
            allWatched = all(self.isWatched(childKey) for childKey in childKeys)
            if allWatched:
                return self.markItemWatched(parentItem, parentKey)
            else:
                return self.unmarkItemWatched(parentItem, parentKey)
        except Exception:
            printExc()
        return False

    def recomputeAllGroupsWatched(self, groupsDict, keyProvider, parentItemBuilder):
        self._dbgCall('recomputeAllGroupsWatched')
        try:
            if not groupsDict:
                return
            for groupId in list(groupsDict.keys()):
                try:
                    parentItem = parentItemBuilder(groupId)
                except Exception:
                    parentItem = None
                    printExc()
                if parentItem is not None:
                    self.recomputeGroupWatched(groupsDict.get(groupId, []), keyProvider, parentItem)
        except Exception:
            printExc()
        self.dumpDebugCalls()

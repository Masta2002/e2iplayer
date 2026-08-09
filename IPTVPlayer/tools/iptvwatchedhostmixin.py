# -*- coding: utf-8 -*-
###################################################
# LOCAL import
###################################################
from Plugins.Extensions.IPTVPlayer.tools.iptvtools import printExc
from Plugins.Extensions.IPTVPlayer.components.ihost import CHostBase
###################################################
# FOREIGN import
###################################################
from Components.config import config


class WatchedFlagHostMixin(object):
    # Shared IPTVHost boilerplate for wiring a per-site host into the centralized
    # watched-flag/favourite-hash system (IPTVWatchedHelper). Include alongside
    # CHostBase, e.g. class IPTVHost(WatchedFlagHostMixin, CHostBase).
    # Requires the including class's __init__ to set up:
    #   self.watchedHelper (IPTVWatchedHelper instance, named after the host)
    #   self.cachedRet, self.refreshAfterWatchedFlagChange

    def fixWatchedFlag(self, ret):
        if config.plugins.iptvplayer.favourites_use_watched_flag.value:
            ret = self.watchedHelper.fixHostRet(ret, self.host.currList, self.host._getWatchedKeyForItem)
        self.cachedRet = ret
        return ret

    def syncWatchedToFavouriteHash(self, Index=0):
        if config.plugins.iptvplayer.favourites_use_watched_flag.value and self.watchedHelper.syncFavouriteFromRet(self.cachedRet, Index):
            self.refreshAfterWatchedFlagChange = True
            return True
        return False

    def getLinksForVideo(self, Index=0, selItem=None):
        # marking the item watched is handled by the host's own getLinksForVideo(cItem),
        # which this delegates into (via CHostBase -> getLinksForItem -> host.getLinksForItem
        # alias) and which is also reached from the favourites direct-play path that never
        # goes through this Index-based method at all - marking it here too would be redundant
        try:
            self.syncWatchedToFavouriteHash(Index)
        except Exception:
            printExc()
        return CHostBase.getLinksForVideo(self, Index, selItem)

    def getCustomActions(self, Index=0):
        return self.watchedHelper.getCustomActionsForRet(self.cachedRet, self.host.currList, self.host._getWatchedKeyForItem, Index)

    def getListForItem(self, Index=0, refresh=0, selItem=None):
        ret = CHostBase.getListForItem(self, Index, refresh, selItem)
        return self.fixWatchedFlag(ret)

    def getPrevList(self, refresh=0):
        ret = CHostBase.getPrevList(self, refresh)
        return self.fixWatchedFlag(ret)

    def getCurrentList(self, refresh=0):
        if refresh == 1 and self.refreshAfterWatchedFlagChange and self.cachedRet is not None:
            ret = self.cachedRet
        else:
            ret = CHostBase.getCurrentList(self, refresh)
        ret = self.fixWatchedFlag(ret)
        self.refreshAfterWatchedFlagChange = False
        return ret

    def getMoreForItem(self, Index=0):
        ret = CHostBase.getMoreForItem(self, Index)
        return self.fixWatchedFlag(ret)

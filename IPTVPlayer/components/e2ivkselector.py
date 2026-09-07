# -*- coding: utf-8 -*-
#
#  Keyboard Selector
#
#  $Id$
#
#
from Plugins.Extensions.IPTVPlayer.tools.iptvtools import printExc
from Components.config import config


def GetVirtualKeyboard(caps=None):
    # caps is an optional out-param: a caller wanting the has_additional_params
    # / has_suggestions flags back passes a fresh dict; the no-arg callers just
    # need the class. (Was caps={} - a shared mutable default the .update()
    # below kept growing across calls.)
    if caps is None:
        caps = {}
    type = config.plugins.iptvplayer.osk_type.value

    if type in ['own', '']:
        try:
            from enigma import getDesktop
            if getDesktop(0).size().width() >= 1050:
                from Plugins.Extensions.IPTVPlayer.components.e2ivk import E2iVirtualKeyBoard

                caps.update({'has_additional_params': True, 'has_suggestions': True})
                return E2iVirtualKeyBoard
        except Exception:
            printExc()

    from Screens.VirtualKeyBoard import VirtualKeyBoard
    return VirtualKeyBoard

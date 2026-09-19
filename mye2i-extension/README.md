# MyE2iV3 - gepatchte Browser-Erweiterung (v1.18.0)

Dies ist der komplette, gepatchte Quellcode der "MyE2iV3"-Browser-Erweiterung
(Original: http://www.e2iplayer.gitlab.io/mye2iv3_1.17.zip), die zusammen mit
`IPTVPlayer/scripts/mye2iserver.py` für das Lösen von Cloudflare-/Captcha-
Challenges verwendet wird (siehe `getPageCFProtection()` in `libs/pCommon.py`).

Die Original-Erweiterung ist NICHT Teil dieses Repos und wird von einem
Drittanbieter (e2iplayer.gitlab.io) gehostet. Dieser Ordner enthält die von
uns gepatchte Version als **ungepacktes Extension-Verzeichnis** - zum Testen
direkt ladbar über `chrome://extensions` → Entwicklermodus →
"Entpackte Erweiterung laden" → diesen Ordner auswählen.

## Was gefixt wurde (gegenüber Original-v1.17)

Alle Fixes sind rein additiv - eine unveränderte Original-Erweiterung
funktioniert weiterhin identisch mit dem gefixten `mye2iserver.py` (neue
Endpunkte werden von ihr einfach nie angefragt).

1. **`contentscripts/rc2ContentscriptProxy.js` - `main_e2itcf()`**: die
   Cloudflare-Challenge-Erkennung konnte fälschlich "fertig" melden, bevor
   Cloudflare seine Marker (`#challenge-form`, `<link>`, `<script>`)
   überhaupt ins DOM eingefügt hatte (Race Condition bei schnellen
   "Managed Challenges"). Jetzt wird erst ab `document.readyState=="complete"`
   geprüft, zusätzlich per `MutationObserver` auch auf In-Place-DOM-Änderungen
   ohne kompletten Seiten-Reload reagiert.
2. **`ParamsExt` (gleiche Datei)**: stürzte ab, wenn nach einem echten
   Redirect (Challenge bestanden → neue Seite ohne das ursprüngliche
   URL-Fragment) `document.location.hash` leer war. Degradiert jetzt auf
   leere Parameter statt eine `TypeError` zu werfen - die aufrufenden
   Stellen haben dafür bereits funktionierende Fallbacks (z.B. Domain aus
   der aktuellen Seiten-URL ableiten).
3. **`scripts/background.js` + `contentscripts/e2it.js`**: neuer
   `DEBUG_LOG`-Relay-Mechanismus - jede `e2ilog(...)`-Zeile aus dem
   Challenge-Tab wird jetzt zusätzlich an den lokalen `e2it.html`-Tab
   weitergeleitet, der sie per XHR an `mye2iserver.py` (`/debug`-Endpunkt)
   schickt. Landet dort per `printDBG()` direkt im normalen Box-Debug-Log -
   Browser-DevTools sind zum Debuggen nicht mehr zwingend nötig.
4. **`contentscripts/e2it.js`**: meldet beim Laden der lokalen Solver-Seite
   die eigene Erweiterungs-Version an einen neuen `/version`-Endpunkt in
   `mye2iserver.py` - bei zu alter Version erscheint ein Hinweis direkt auf
   dem Box-Bildschirm (nicht nur unauffällig im Browser).
5. Debug-Logging (`e2ilog`) generell aktiviert (war zuvor `//console.log`
   auskommentiert) - sichtbar in der Browser-Konsole UND (Punkt 3) im
   Box-Log.

## Neu in v1.18.0: Debug-Snapshot ("Debug snapshot"-Button)

Zum Entwickeln neuer Hosts: statt aus curl-Ausgaben zu raten, was eine Seite
wirklich ausliefert (JS-gerenderte Inhalte, per AJAX nachgeladene Daten),
lädt der echte Browser die Seite und schickt das Ergebnis ins Box-Debug-Log.

**Ablauf:** wie beim normalen Cloudflare-Lösen die Box-Seite (`e2it.html`,
QR-Code / `http://<box>:9001`) im Browser öffnen und **offen lassen**. Dort
gibt es unter dem grünen Button jetzt ein URL-Feld (vorbelegt mit der Seite,
die die Box angefragt hat - beliebig änderbar, z.B. auf eine Video-Seite)
und den Button **"Debug snapshot"**. Der öffnet die URL in einem neuen Tab
mit dem Fragment `#e2itdbg_sep_c=...`. Zeigt Cloudflare dort eine Challenge,
einfach im Tab lösen - der Snapshot startet automatisch danach.

**Was ins Log kommt** (jeweils als `[MyE2i-DUMP <abschnitt>]`-Zeilen, max.
~500 KB pro Abschnitt im Log; die vollständige Datei liegt zusätzlich unter
`<tmp>/mye2i_debug/<zeit>_<abschnitt>.txt` auf der Box):

| Abschnitt   | Inhalt |
|-------------|--------|
| `meta`      | URL, Titel, User-Agent, Wartezeit |
| `dom`       | das fertig gerenderte HTML (`documentElement.outerHTML`) |
| `resources` | alle geladenen URLs inkl. fetch/XHR (Performance-API) |
| `netlog`    | jeder `fetch()`/`XMLHttpRequest`-Aufruf: Methode, URL, Request-Body, Status und die ersten 3000 Zeichen der Antwort - genau das, was man braucht, um eine Seiten-API nachzubauen |
| `cookies`   | Cookie-Namen, Domain, Flags (Werte auf 40 Zeichen gekürzt) |

Hinweis: die Cookie-Namen/-Werte gehören zur aufgerufenen Domain im
Browser des Testers - Log vor dem Weitergeben ansehen.

**Technik:** ein `POST /debugdump?name=<abschnitt>`-Endpunkt in
`mye2iserver.py` (die bisherigen Endpunkte sind GET und damit für ein ganzes
HTML-Dokument zu klein); `contentscripts/dbgProbe.js` (wird vom
`background.js` nach jedem fertigen Seitenladen des Debug-Tabs injiziert -
ein Cloudflare-Redirect verliert das URL-Fragment) und
`contentscripts/dbgHook.js` (läuft in der Seitenwelt und protokolliert
fetch/XHR, auch nach einem Redirect innerhalb der Sitzung). Getestet in
einem echten Edge 153 gegen eine lokale Testseite (JS-gerendertes DOM,
fetch-POST, XHR, Cookie) - ohne echte Cloudflare-Challenge.

Alle zugehörigen Server-seitigen Ergänzungen (`/debug`, `/version`-Endpunkte,
Routing-Fix, Versions-Konstante `MIN_EXTENSION_VERSION`) liegen in
`IPTVPlayer/scripts/mye2iserver.py` in diesem Branch.

## Bekannte offene Punkte (siehe Memory / nächste Schritte)

- **Kein echtes `.crx` vorhanden.** Für ein signiertes `.crx` bräuchte man
  den privaten Signierschlüssel des Original-Entwicklers, den wir nicht
  haben. Ein selbst erzeugtes `.crx` würde eine andere Extension-ID
  bekommen und lässt sich in modernen Chrome-Versionen ohnehin nicht mehr
  einfach per Drag&Drop installieren (nur über Entwicklermodus). Für
  produktiven Einsatz müsste eine Chrome-Web-Store-Veröffentlichung (oder
  ein alternativer Vertriebsweg) geklärt werden.
- **Hartcodierte Original-URLs** in `mye2iserver.py`
  (`UPDATE_URL = 'http://www.e2iplayer.gitlab.io/mye2iv3_1.17.zip'`) und
  potenziell an weiteren Stellen im Plugin, die auf die MyE2i-Erweiterung
  hinweisen, zeigen noch auf die Original-Download-Adresse des
  Drittanbieters, nicht auf eine eigene GitHub/GitLab-Adresse dieses
  Projekts. Muss noch umgestellt werden, sobald der gepatchte Code irgendwo
  eigenständig gehostet wird.

## Wie man die Original-Erweiterung findet, die ersetzt werden soll

Referenziert u.a. in `IPTVPlayer/components/captchascriptwidget.py` /
`recaptcha_mye2i_widget.py` (Anzeige "Please Open site: http://IP:PORT..."
für den Nutzer) sowie in `IPTVPlayer/scripts/mye2iserver.py` selbst
(`UPDATE_URL`-Konstante für den Versions-Hinweis).

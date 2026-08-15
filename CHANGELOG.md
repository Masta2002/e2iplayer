# Changelog – Storage Overhaul (`rename-config-paths`)

Changes on the `rename-config-paths` branch relative to `python3`.

## Deutsch

**Konfigurationsnamen auf Englisch umgestellt**
- `SciezkaCache` → `CacheDir`, `NaszaTMP` → `TmpDir`, `NaszaSciezka` → `DownloadsDir`
- Bereits gespeicherte, individuell angepasste Pfade gehen dabei nicht verloren: die neuen Optionen übernehmen beim ersten Start automatisch den zuvor gespeicherten Wert

**Automatischer Schutz bei fehlender Storage (z. B. kein `/hdd`, oder ein zuvor genutzter USB-Stick wurde entfernt)**
- Cache-Ordner wird automatisch auf einen Ordner innerhalb des Plugin-Verzeichnisses umgestellt, mit kurzer Meldung an den Nutzer
- Puffer-Ordner wird automatisch auf den Temp-Ordner umgestellt (keine Meldung nötig, rein temporäre Daten)
- Downloads-Ordner: hier wird stattdessen aktiv nachgefragt, wohin Downloads gespeichert werden sollen (Verzeichnisauswahl) – dauerhafte Nutzerdaten werden nie automatisch verschoben
- Die Erkennung unterscheidet zuverlässig zwischen "Ordner existiert einfach noch nicht" (normal beim ersten Start auf einer echten Festplatte) und "hier ist gar keine echte Storage vorhanden" – und merkt sich einmal vom Nutzer bestätigte Downloads-Pfade, damit nicht bei jedem Start erneut gefragt wird
- Kann ein Cache-Unterordner trotzdem nicht angelegt werden, erscheint einmalig eine Warnung statt eines stillen Fehlschlags

**Neue Cache-Verwaltung** (Einstellungen → Speicher-Konfiguration → "Detail/expert mode")
- Für Cookies, JS-Cache, Untertitel und Film-Metadaten jeweils: automatisches Löschen nach einstellbarer Anzahl Tage (0 = nie) sowie eine "jetzt löschen"-Option
- Movie-Player-Präferenz (gemerkter Player/Puffer-Modus je Host), Suchverlauf, Favoriten/Gesehen-Status und Host-Reihenfolge/-Gruppen: jeweils eine "jetzt löschen"-Option (kein automatisches Löschen, da es sich um aktuellen Zustand statt alternder Cache-Daten handelt)
- Thumbnail-Löschung ("Remove thumbnails") von der Skin- in die Speicher-Konfiguration verschoben, jetzt immer sichtbar, und um die Option "never" ergänzt
- Eine Sammel-Option "Delete all cache files now" leert den kompletten Cache-Ordner auf einmal
- Jede Löschaktion fragt vorher per Ja/Nein-Dialog nach; bei Favoriten/Gesehen-Status sowie "Alles löschen" mit besonders deutlichem Warntext
- Alle diese Einträge sind standardmäßig ausgeblendet und erscheinen erst nach Aktivieren von "Detail/expert mode"

**Host-Gruppen und Host-Reihenfolge umgezogen**
- Lagen bisher als einzige Dateien des Plugins direkt im Enigma2-Einstellungsordner (`/etc/enigma2/`) – jetzt im Cache-Ordner (`CacheDir/hostorder/`), zusammen mit allen anderen Cache-Daten
- Bereits vorhandene Dateien werden beim ersten Start automatisch dorthin übernommen, nichts geht verloren

**Zwei Hosts aufgeräumt**
- `hostipla` und `hostlodynet` nutzten bisher eigene, vom Cache-Ordner unabhängige Speicherorte für ihre Cookie-/Cache-Dateien (bei `hostlodynet` sogar ein fest einprogrammierter Pfad, der die eigentliche Einstellung ignorierte) – beide nutzen jetzt denselben zentralen Mechanismus wie alle anderen Hosts

## English

**Config attribute names switched to English**
- `SciezkaCache` → `CacheDir`, `NaszaTMP` → `TmpDir`, `NaszaSciezka` → `DownloadsDir`
- Existing, individually customized paths are preserved: the new options automatically pick up the previously saved value on first start

**Automatic protection when storage is missing** (e.g. no `/hdd`, or a previously used USB stick was removed)
- Cache folder automatically switches to a folder inside the plugin's own directory, with a brief notification
- Buffering folder automatically switches to the temp folder (no notification needed, purely temporary data)
- Downloads folder: instead, the user is actively asked where downloads should be saved (directory picker) – permanent user data is never silently redirected
- Detection reliably distinguishes "this folder simply doesn't exist yet" (normal on first run with a real drive) from "there's no real storage here at all" – and remembers a downloads path once confirmed by the user, so it isn't asked again on every start
- If a cache subfolder still can't be created, a one-time warning appears instead of failing silently

**New cache management** (Settings → Storage configuration → "Detail/expert mode")
- For cookies, JS cache, subtitles, and movie metadata: automatic deletion after a configurable number of days (0 = never), plus a "delete now" option
- Movie player preference (remembered player/buffering choice per host), search history, favourites/watched status, and host order/groups: a "delete now" option each (no automatic aging cleanup, since these reflect current state rather than stale cache)
- Thumbnail cleanup ("Remove thumbnails") moved from Skin to Storage configuration, now always visible, and gained a "never" option
- A combined "Delete all cache files now" option empties the entire cache folder at once
- Every delete action asks for Yes/No confirmation first; favourites/watched status and "delete all" use an especially explicit warning
- All of these entries are hidden by default and only appear once "Detail/expert mode" is enabled

**Host groups and host order relocated**
- Previously the only files this plugin wrote directly into the Enigma2 settings folder (`/etc/enigma2/`) – now live in the cache folder (`CacheDir/hostorder/`) alongside all other cache data
- Any existing files are automatically migrated there on first start, nothing is lost

**Two hosts cleaned up**
- `hostipla` and `hostlodynet` previously used their own storage locations independent of the cache folder (`hostlodynet` even had a hardcoded path that ignored the actual setting) – both now use the same central mechanism as every other host

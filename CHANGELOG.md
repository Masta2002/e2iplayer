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
- Thumbnail-Löschung ("Remove thumbnails") von der Skin- in die Speicher-Konfiguration verschoben, jetzt immer sichtbar, und um die Option "never" ergänzt
- Eine Sammel-Option "Delete all cache files now" leert den kompletten Cache-Ordner auf einmal (Cookies, JS-Cache, Untertitel, Film-Metadaten, Thumbnails)
- Jede Löschaktion fragt vorher per Ja/Nein-Dialog nach
- Alle diese Einträge sind standardmäßig ausgeblendet und erscheinen erst nach Aktivieren von "Detail/expert mode"

**Neuer Config-Ordner für echte Nutzerdaten** (dritte Ordner-Einstellung neben Cache-/Temp-Ordner, Default `/etc/enigma2/IPTVPlayer/`)
- Movie-Player-Präferenz (gemerkter Player/Puffer-Modus je Host), Suchverlauf, Favoriten/Gesehen-Status und Host-Reihenfolge/-Gruppen liegen jetzt in einem eigenen, separat konfigurierbaren Ordner statt im Cache-Ordner, da es sich um echte Nutzerdaten handelt und nicht um regenerierbaren Cache
- Dadurch kann "Delete all cache files now" diese Daten nie versehentlich mitlöschen
- Eigene Sammel-Option "Delete all config files now" leert nur den Config-Ordner (mit deutlich schärferem Warntext, da echte Nutzerdaten betroffen sind)
- Innerhalb des Expertenmodus optisch in zwei Abschnitte "Cache" und "Config" gruppiert
- Bereits vorhandene Daten (die bisher im Cache-Ordner lagen bzw. bei Host-Reihenfolge/-Gruppen direkt im Enigma2-Einstellungsordner `/etc/enigma2/`) werden beim ersten Zugriff automatisch in den neuen Config-Ordner übernommen, nichts geht verloren

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
- Thumbnail cleanup ("Remove thumbnails") moved from Skin to Storage configuration, now always visible, and gained a "never" option
- A combined "Delete all cache files now" option empties the entire cache folder at once (cookies, JS cache, subtitles, movie metadata, thumbnails)
- Every delete action asks for Yes/No confirmation first
- All of these entries are hidden by default and only appear once "Detail/expert mode" is enabled

**New config folder for real user data** (a third folder setting alongside cache/temp folder, default `/etc/enigma2/IPTVPlayer/`)
- Movie player preference (remembered player/buffering choice per host), search history, favourites/watched status, and host order/groups now live in their own, separately configurable folder instead of the cache folder, since this is real user data rather than regenerable cache
- This means "Delete all cache files now" can never accidentally wipe it
- A dedicated "Delete all config files now" option empties only the config folder (with a noticeably stronger warning, since real user data is affected)
- Visually grouped into two sections, "Cache" and "Config", within expert mode
- Any existing data (previously in the cache folder, or - for host order/groups - directly in the Enigma2 settings folder `/etc/enigma2/`) is automatically migrated to the new config folder on first access, nothing is lost

**Two hosts cleaned up**
- `hostipla` and `hostlodynet` previously used their own storage locations independent of the cache folder (`hostlodynet` even had a hardcoded path that ignored the actual setting) – both now use the same central mechanism as every other host

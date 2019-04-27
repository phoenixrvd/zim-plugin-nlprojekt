# zim-plugin-nlprojekt

Integration in das Projektmanagement-Tool **NL-Projekt**, entwickelt von [netlands edv consulting GmbH](https://netlands.de/)

## Installation

```bash
cd $HOME/.local/share/zim/plugins/
git clone git@github.com:phoenixrvd/zim-plugin-nlprojekt.git nlprojekt
```
* das Plugin im ZIM aktivieren

## Funktionen

* Automatisches Übertragen von Zeit-Einträgen aus [ZIM-Tagebuch](https://zim-wiki.org/manual/Plugins/Journal.html) 

## Funktionsweise

Die kommunikation zwischen ZIM und NL-Projekt erfolgt über eine [JSON-RPC](https://en.wikipedia.org/wiki/JSON-RPC) -Schnittstelle.
Um die Schnittstelle im NL-Projekt zu aktivieren, muss man das Programm mit RPC-Server starteten (-r Option von nlprojekt-Binary)
Sobald NL-Projekt gestartet ist, ist der Server unter http://localhost:1420 erreichbar und die Kommunikation kann statt finden.

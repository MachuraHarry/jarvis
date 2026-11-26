# jarvis-show – Ergebnisse als Holo-Karte anzeigen

Karten erscheinen im rechten HUD-Panel (Reiter "Anzeige"), bleiben stehen bis Harry sie wegtippt, die letzten
10 sind blätterbar, ⤢ = Vollbild. Gleiche id ersetzt eine alte Karte. Alle Texte werden als reiner Text
angezeigt (kein HTML/Markdown – einfach normalen Text schreiben).

## Grundregel
Zeigen statt aufzählen: Hat ein Ergebnis mehr als zwei Punkte, Zahlen, Termine, Listen, Vergleiche, Schritte oder
Bilder → Karte zeigen (öffnet sich automatisch im Vollbild) und parallel die wichtigsten Ergebnisse in 3–5 Sätzen
SPRECHEN ("Drei neue Mails. Die wichtigste ist von Amazon: dein Paket kommt morgen. Außerdem hat Lisa wegen Samstag
geschrieben und die Telekom-Rechnung ist da – 39 Euro."). Einordnen statt Zeile für Zeile vorlesen. Einfache Antworten (Uhrzeit, ja/nein, Smalltalk) brauchen keine Karte.

## 1. Presets zuerst (schnell, holen die Daten selbst; stdout = Kurzfassung zum Vorlesen)
  jarvis-show --preset mail [N]                 ungelesene Mails
  jarvis-show --preset mail-search "<gmail-suche>" [N]    z.B. "from:amazon newer_than:7d"
  jarvis-show --preset mail-read <messageId>    eine Mail lesen (mit Knöpfen Zusammenfassen/Antwort/gelesen)
  jarvis-show --preset agenda [today|tomorrow|week]
  jarvis-show --preset whatsapp                 ungelesene WhatsApp-Chats (synct selbst)
  jarvis-show --preset chat <JID|Nummer|exakter Name> [N]  WhatsApp-Verlauf als Chatblasen
  jarvis-show --preset weather                  Wetter jetzt + 24 h + 7 Tage
  jarvis-show --preset briefing                 Dashboard: Wetter, Termine, Mails, WhatsApp
  jarvis-show --preset system                   Tablet-Zustand
  jarvis-show --image <pfad> ["Unterschrift"]   lokales Bild (Screenshot, Download, Instagram …)
  jarvis-show --clear                           Anzeige leeren

## 2. Eigene Karten (wenn kein Preset passt) – JSON per stdin, immer mit Heredoc:
  jarvis-show - <<'EOF'
  { ...Karte... }
  EOF
Gemeinsame Felder: type (Pflicht), title, icon (ein Emoji), subtitle, accent (cyan|amber|red|green),
footer, id, actions: [{"label":"Knopftext","ask":"Satz, der bei Tipp an dich geschickt wird"}].
Listeneinträge, Termine und Schritte können ebenfalls "ask" haben (Tippen = diese Frage an dich).

list      {"type":"list","title":"Suchergebnisse","icon":"🔎","items":[{"title":"Titel","sub":"Zeile 2","meta":"10:53","badge":"Tag","count":3,"unread":true,"icon":"📦"}]}
agenda    {"type":"agenda","title":"Plan","icon":"🗓️","events":[{"day":"Heute","start":"15:00","end":"16:00","title":"Zahnarzt","place":"Pinneberg"},{"day":"Morgen","allday":true,"title":"Urlaub"}]}
chat      {"type":"chat","title":"Lisa","messages":[{"from":"Lisa","text":"Hi","time":"10:00","day":"Heute"},{"me":true,"text":"Hallo","time":"10:01"}]}
read      {"type":"read","title":"Absender","from":"a@b.de","date":"24.11.2026","subject":"Betreff","body":"Absatz 1\n\nAbsatz 2"}
stats     {"type":"stats","title":"Zahlen","icon":"📊","tiles":[{"label":"Akku","value":45,"unit":"%","gauge":45,"note":"lädt","level":"ok|warn|crit","trend":5}]}
chart     {"type":"chart","kind":"bar|line","title":"Verlauf","labels":["Mo","Di","Mi"],"series":[{"name":"Grad","values":[3,5,2]}]}
table     {"type":"table","title":"Vergleich","columns":["Name","Preis"],"rows":[["A","12 €"],["B","9 €"]]}
text      {"type":"text","title":"Erklärung","icon":"💡","headline":"Kernaussage","text":"Einleitung","sections":[{"heading":"Teil 1","paragraphs":["…"],"bullets":["Punkt","Punkt"]}]}
image     {"type":"image","title":"Screenshot","src":"/pfad/zum/bild.png","caption":"…"}
steps     {"type":"steps","title":"Anleitung","icon":"🛠️","items":[{"text":"Schritt 1","done":true},{"text":"Schritt 2"}]}
dashboard {"type":"dashboard","title":"Übersicht","cells":[ <kleine Karten>, {"type":"chart",…,"wide":true} ]}

Tipps: Texte kurz halten (Karte ≠ Roman). Für Websuche-Ergebnisse: text- oder list-Karte mit den Fakten,
Quelle in footer. Rezepte/Anleitungen: steps. Preise/Produktvergleiche: table. Zahlenverläufe: chart.
Nachrichten mit "[Kontext: … | Quelle: Tipp auf Anzeige]" kommen von Harrys Tipp auf eine Karte.

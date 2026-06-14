# 🍶 Getränke-Verwaltung

Bestandsverwaltung für Flaschen in Keller und Oben — gebaut mit Streamlit.

## Dateien

| Datei | Beschreibung |
|---|---|
| `app.py` | Haupt-App |
| `requirements.txt` | Python-Abhängigkeiten |
| `getraenke.json` | Daten (wird automatisch erstellt) |

## Lokaler Start

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deployment auf Streamlit Community Cloud

1. Dieses Repo auf GitHub pushen (alle Dateien ins Root-Verzeichnis)
2. Auf [share.streamlit.io](https://share.streamlit.io) einloggen
3. **New app** → dein Repo auswählen → `app.py` als Main file
4. **Deploy** klicken — fertig!

> **Hinweis:** Auf Streamlit Cloud wird `getraenke.json` bei jedem Neustart zurückgesetzt.  
> Für dauerhaften Speicher: [st.secrets](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management) + eine externe DB (z. B. Supabase Free Tier) nutzen.

## Features

- ✅ Flaschen hinzufügen (Name, Typ, Ort, Anzahl, Füllstand, Notiz)
- ✅ Bestand nach Keller / Oben gruppiert anzeigen
- ✅ Füllstand und Anzahl inline bearbeiten
- ✅ Flasche zwischen Keller ↔ Oben umlagern
- ✅ Flasche löschen (mit Bestätigung)
- ✅ Filter nach Ort, Typ, Name
- ✅ KPI-Übersicht (Anzahl Flaschen gesamt)
- ✅ Daten lokal in `getraenke.json` gespeichert

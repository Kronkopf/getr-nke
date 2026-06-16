import streamlit as st
import json
import requests
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore

# ── Konfiguration ──────────────────────────────────────────────────────────────
TYPEN = ["Wein", "Bier", "Wasser", "Saft", "Spirituosen", "Sonstiges"]
ORTE  = ["Keller", "Oben", "Kühlschrank"]

TYP_EMOJI = {
    "Wein": "🍷", "Bier": "🍺", "Wasser": "💧",
    "Saft": "🧃", "Spirituosen": "🥃", "Sonstiges": "📦",
}
ORT_EMOJI = {"Keller": "🏠", "Oben": "☝️", "Kühlschrank": "🧊"}

IMMER_VORHANDEN = ["Orangen", "Zitronen", "Wasser", "Milch", "Eiswürfel"]

# ── Firebase Verbindung ────────────────────────────────────────────────────────
@st.cache_resource
def init_firebase():
    if not firebase_admin._apps:
        key_dict = {
            "type": "service_account",
            "project_id":                  st.secrets["FIREBASE_PROJECT_ID"],
            "private_key_id":              st.secrets["FIREBASE_PRIVATE_KEY_ID"],
            "private_key":                 st.secrets["FIREBASE_PRIVATE_KEY"].replace("\\n", "\n"),
            "client_email":                st.secrets["FIREBASE_CLIENT_EMAIL"],
            "client_id":                   st.secrets["FIREBASE_CLIENT_ID"],
            "auth_uri":                    "https://accounts.google.com/o/oauth2/auth",
            "token_uri":                   "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url":        st.secrets["FIREBASE_CLIENT_CERT_URL"],
        }
        cred = credentials.Certificate(key_dict)
        firebase_admin.initialize_app(cred)
    return firestore.client()

db = init_firebase()
COLLECTION = "getraenke"

# ── Firestore Datenzugriff ─────────────────────────────────────────────────────
def lade_daten() -> list[dict]:
    docs = db.collection(COLLECTION).stream()
    return [{"id": doc.id, **doc.to_dict()} for doc in docs]

def flasche_hinzufuegen(eintrag: dict) -> None:
    db.collection(COLLECTION).add(eintrag)

def flasche_aktualisieren(doc_id: str, felder: dict) -> None:
    db.collection(COLLECTION).document(doc_id).update(felder)

def flasche_loeschen(doc_id: str) -> None:
    db.collection(COLLECTION).document(doc_id).delete()

# ── Hilfsfunktionen ────────────────────────────────────────────────────────────
def fuellstand_farbe(f: int) -> str:
    if f >= 70:   return "🟢"
    elif f >= 30: return "🟡"
    return "🔴"

def fuellstand_balken(f: int) -> str:
    filled = round(f / 10)
    return "█" * filled + "░" * (10 - filled) + f"  {f}%"

# ── KI Getränkevorschläge ──────────────────────────────────────────────────────
def hole_vorschlaege(daten: list[dict]) -> str:
    verfuegbar = [
        f"{d['name']} ({d['typ']}, {d['fuell']}% voll)"
        for d in daten if d.get("anzahl", 0) > 0 and d.get("fuell", 0) > 0
    ]
    bestand_text = "\n".join(verfuegbar) if verfuegbar else "Kein Bestand vorhanden"
    immer_text   = ", ".join(IMMER_VORHANDEN)

    prompt = f"""Du erstellst eine schlichte Getränkekarte basierend auf dem Bestand.

Bestand:
{bestand_text}

Immer im Haus: {immer_text}
Kaffeevollautomat vorhanden: Espresso, Kaffee, Cappuccino, Latte Macchiato etc. immer möglich.
Wasser: still und sprudelnd immer verfügbar.

Erstelle genau 15 Getränkevorschläge. Format:
- Basics (Bier, Wein, Wasser still/sprudelnd, Saft, Kaffeegetränke): nur Emoji und Name, keine cl
- Mischgetränke und Cocktails: Emoji Name — Zutaten mit cl

Reihenfolge:
1. Basics zuerst: Bier, Wein, Sekt, Wasser still, Wasser sprudelnd, Saft, Espresso, Kaffee, Cappuccino etc.
2. Einfache Klassiker: Aperol Spritz, Hugo, Weinschorle, Radler etc.
3. Ganz am Ende 2-3 kreativere Cocktails/Kombis mit cl-Angaben

Nur machbare Getränke. Kein Erklärtext. Auf Deutsch."""

    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {st.secrets['OPENROUTER_API_KEY']}",
                "Content-Type":  "application/json",
                "HTTP-Referer":  "https://streamlit.io",
                "X-Title":       "Getraenke Verwaltung",
            },
            json={
                "model":      "openrouter/auto",
                "messages":   [{"role": "user", "content": prompt}],
                "max_tokens": 800,
            },
            timeout=30,
        )
        result = response.json()

        # Fehlerdetails aus der API-Antwort ausgeben falls vorhanden
        if "error" in result:
            return f"❌ API Fehler: {result['error'].get('message', result['error'])}"

        return result["choices"][0]["message"]["content"]

    except Exception as e:
        return f"❌ Fehler: {e}"

# ── Seiten-Setup ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Getränke-Verwaltung",
    page_icon="🍶",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("🍶 Getränke-Verwaltung")
st.caption("Keller · Oben · Kühlschrank — Bestand immer aktuell")

# ── Daten laden ────────────────────────────────────────────────────────────────
daten = lade_daten()

# ── 🍹 Getränkekarte für Gäste (automatisch beim Laden) ───────────────────────
st.header("🍹 Getränkekarte für Gäste")

if "vorschlaege" not in st.session_state:
    with st.spinner("🤵 Barkeeper schaut in den Keller..."):
        st.session_state["vorschlaege"] = hole_vorschlaege(daten)

col_txt, col_btn = st.columns([5, 1])
with col_btn:
    if st.button("🔄 Neu generieren", use_container_width=True):
        with st.spinner("🤵 Einen Moment..."):
            st.session_state["vorschlaege"] = hole_vorschlaege(daten)

st.markdown(st.session_state["vorschlaege"])

st.divider()

# ── Sidebar: Flasche hinzufügen ────────────────────────────────────────────────
with st.sidebar:
    st.header("➕ Flasche hinzufügen")

    with st.form("add_form", clear_on_submit=True):
        name    = st.text_input("Bezeichnung", placeholder="z. B. Riesling Kabinett 2022")
        typ     = st.selectbox("Typ", TYPEN)
        ort     = st.selectbox("Ort", ORTE)
        anzahl  = st.number_input("Anzahl", min_value=1, max_value=999, value=1, step=1)
        fuell   = st.slider("Füllstand (%)", 0, 100, 100, step=5)
        notiz   = st.text_input("Notiz (optional)", placeholder="z. B. Jahrgang, Weingut …")
        submit  = st.form_submit_button("💾 Hinzufügen", use_container_width=True)

        if submit:
            if not name.strip():
                st.error("Bitte einen Namen eingeben.")
            else:
                flasche_hinzufuegen({
                    "name":     name.strip(),
                    "typ":      typ,
                    "ort":      ort,
                    "anzahl":   int(anzahl),
                    "fuell":    int(fuell),
                    "notiz":    notiz.strip(),
                    "erstellt": datetime.now().strftime("%d.%m.%Y"),
                })
                st.success(f"✅ {name} hinzugefügt!")
                st.rerun()

    st.divider()
    st.header("🔍 Filter")
    filter_ort  = st.selectbox("Ort",  ["Alle"] + ORTE,  key="filter_ort")
    filter_typ  = st.selectbox("Typ",  ["Alle"] + TYPEN, key="filter_typ")
    filter_name = st.text_input("Suche", placeholder="Name …", key="filter_name")
    st.divider()
    if st.button("🔄 Bestand aktualisieren", use_container_width=True):
        st.rerun()

# ── KPI-Übersicht ──────────────────────────────────────────────────────────────
cols = st.columns(len(ORTE) + 1)
for i, ort_name in enumerate(ORTE):
    gruppe = [d for d in daten if d["ort"] == ort_name]
    total  = sum(d["anzahl"] for d in gruppe)
    cols[i].metric(
        f"{ORT_EMOJI[ort_name]} {ort_name}",
        f"{total} Fl.",
        f"{len(gruppe)} Positionen"
    )
gesamt = sum(d["anzahl"] for d in daten)
cols[-1].metric("📦 Gesamt", f"{gesamt} Fl.", f"{len(daten)} Positionen")

st.divider()

# ── Filter anwenden ────────────────────────────────────────────────────────────
gefiltert = daten[:]
if filter_ort  != "Alle": gefiltert = [d for d in gefiltert if d["ort"] == filter_ort]
if filter_typ  != "Alle": gefiltert = [d for d in gefiltert if d["typ"] == filter_typ]
if filter_name:           gefiltert = [d for d in gefiltert if filter_name.lower() in d["name"].lower()]

if not gefiltert:
    st.info("Keine Einträge gefunden.")
else:
    for ort_name in ORTE:
        gruppe = [d for d in gefiltert if d["ort"] == ort_name]
        if not gruppe:
            continue

        st.subheader(f"{ORT_EMOJI[ort_name]} {ort_name}")

        for eintrag in gruppe:
            with st.container(border=True):
                c1, c2, c3, c4 = st.columns([3, 1, 2, 2])

                with c1:
                    emoji = TYP_EMOJI.get(eintrag["typ"], "📦")
                    st.markdown(f"**{emoji} {eintrag['name']}**")
                    meta = f"`{eintrag['typ']}` · {eintrag['anzahl']} Fl."
                    if eintrag.get("notiz"):
                        meta += f" · _{eintrag['notiz']}_"
                    if eintrag.get("erstellt"):
                        meta += f" · {eintrag['erstellt']}"
                    st.caption(meta)

                with c2:
                    st.markdown(f"{fuellstand_farbe(eintrag['fuell'])} **{eintrag['fuell']}%**")
                    st.caption(fuellstand_balken(eintrag["fuell"]))

                with c3:
                    neuer_fuell = st.slider(
                        "Füllstand", 0, 100, eintrag["fuell"], step=5,
                        key=f"fuell_{eintrag['id']}",
                        label_visibility="collapsed",
                    )
                    neue_anzahl = st.number_input(
                        "Anzahl", min_value=0, max_value=999,
                        value=eintrag["anzahl"], step=1,
                        key=f"anz_{eintrag['id']}",
                        label_visibility="collapsed",
                    )

                with c4:
                    idx_aktuell = ORTE.index(eintrag["ort"])
                    ziel = ORTE[(idx_aktuell + 1) % len(ORTE)]
                    if st.button(f"↕️ → {ziel}", key=f"move_{eintrag['id']}", use_container_width=True):
                        flasche_aktualisieren(eintrag["id"], {"ort": ziel})
                        st.rerun()

                    if st.button("💾 Speichern", key=f"save_{eintrag['id']}", use_container_width=True):
                        flasche_aktualisieren(eintrag["id"], {
                            "fuell":  int(neuer_fuell),
                            "anzahl": int(neue_anzahl),
                        })
                        st.success("Gespeichert!")
                        st.rerun()

                    if st.button("🗑️ Löschen", key=f"del_{eintrag['id']}", use_container_width=True, type="secondary"):
                        st.session_state[f"confirm_{eintrag['id']}"] = True

                    if st.session_state.get(f"confirm_{eintrag['id']}"):
                        st.warning("Wirklich löschen?")
                        col_j, col_n = st.columns(2)
                        if col_j.button("Ja", key=f"ja_{eintrag['id']}"):
                            flasche_loeschen(eintrag["id"])
                            st.rerun()
                        if col_n.button("Nein", key=f"nein_{eintrag['id']}"):
                            st.session_state[f"confirm_{eintrag['id']}"] = False
                            st.rerun()

# ── Footer ─────────────────────────────────────────────────────────────────────
st.divider()
st.caption(f"☁️ Daten in Firebase Firestore · {len(daten)} Positionen · {gesamt} Flaschen gesamt")

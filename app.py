import streamlit as st
import json
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

# ── Firebase Verbindung ────────────────────────────────────────────────────────
@st.cache_resource
def init_firebase():
    if not firebase_admin._apps:
        key_dict = json.loads(st.secrets["FIREBASE_KEY"])
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

# ── Seiten-Setup ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Getränke-Verwaltung",
    page_icon="🍶",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("🍶 Getränke-Verwaltung")
st.caption("Keller · Oben · Kühlschrank — Bestand immer aktuell")

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

# ── Daten laden ────────────────────────────────────────────────────────────────
daten = lade_daten()

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

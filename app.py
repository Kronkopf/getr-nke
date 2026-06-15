import streamlit as st
import json
import os
from datetime import datetime

# ── Konfiguration ──────────────────────────────────────────────────────────────
DATA_FILE = "getraenke.json"

TYPEN = ["Wein", "Bier", "Wasser", "Saft", "Spirituosen", "Sonstiges"]
ORTE  = ["Keller", "Oben"]

TYP_EMOJI = {
    "Wein": "🍷", "Bier": "🍺", "Wasser": "💧",
    "Saft": "🧃", "Spirituosen": "🥃", "Sonstiges": "📦",
}

# ── Datenpersistenz ────────────────────────────────────────────────────────────
def lade_daten() -> list[dict]:
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def speichere_daten(daten: list[dict]) -> None:
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(daten, f, ensure_ascii=False, indent=2)

def naechste_id(daten: list[dict]) -> int:
    return max((d["id"] for d in daten), default=0) + 1

# ── Hilfsfunktionen ────────────────────────────────────────────────────────────
def fuellstand_farbe(f: int) -> str:
    if f >= 70:
        return "🟢"
    elif f >= 30:
        return "🟡"
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
st.caption("Keller & Oben — Bestand im Überblick")

# Daten laden
if "daten" not in st.session_state:
    st.session_state.daten = lade_daten()

daten = st.session_state.daten

# ── Sidebar: Flasche hinzufügen ────────────────────────────────────────────────
with st.sidebar:
    st.header("➕ Flasche hinzufügen")

    with st.form("add_form", clear_on_submit=True):
        name     = st.text_input("Bezeichnung", placeholder="z. B. Riesling Kabinett 2022")
        typ      = st.selectbox("Typ", TYPEN)
        ort      = st.selectbox("Ort", ORTE)
        anzahl   = st.number_input("Anzahl", min_value=1, max_value=999, value=1, step=1)
        fuell    = st.slider("Füllstand (%)", 0, 100, 100, step=5)
        notiz    = st.text_input("Notiz (optional)", placeholder="z. B. Jahrgang, Weingut …")
        speichern = st.form_submit_button("💾 Hinzufügen", use_container_width=True)

        if speichern:
            if not name.strip():
                st.error("Bitte einen Namen eingeben.")
            else:
                neue_flasche = {
                    "id":      naechste_id(daten),
                    "name":    name.strip(),
                    "typ":     typ,
                    "ort":     ort,
                    "anzahl":  int(anzahl),
                    "fuell":   int(fuell),
                    "notiz":   notiz.strip(),
                    "erstellt": datetime.now().strftime("%d.%m.%Y"),
                }
                daten.append(neue_flasche)
                speichere_daten(daten)
                st.success(f"✅ {name} hinzugefügt!")
                st.rerun()

    st.divider()

    # Filter
    st.header("🔍 Filter")
    filter_ort  = st.selectbox("Ort", ["Alle"] + ORTE, key="filter_ort")
    filter_typ  = st.selectbox("Typ", ["Alle"] + TYPEN, key="filter_typ")
    filter_name = st.text_input("Suche", placeholder="Name …", key="filter_name")

# ── Zusammenfassung (KPIs) ─────────────────────────────────────────────────────
keller_flaschen = [d for d in daten if d["ort"] == "Keller"]
oben_flaschen   = [d for d in daten if d["ort"] == "Oben"]

keller_total = sum(d["anzahl"] for d in keller_flaschen)
oben_total   = sum(d["anzahl"] for d in oben_flaschen)
gesamt       = keller_total + oben_total

col1, col2, col3 = st.columns(3)
col1.metric("🏠 Keller",  f"{keller_total} Fl.", f"{len(keller_flaschen)} Positionen")
col2.metric("☝️ Oben",    f"{oben_total} Fl.",   f"{len(oben_flaschen)} Positionen")
col3.metric("📦 Gesamt",  f"{gesamt} Fl.",        f"{len(daten)} Positionen")

st.divider()

# ── Gefilterte Liste ───────────────────────────────────────────────────────────
gefiltert = daten[:]
if filter_ort != "Alle":
    gefiltert = [d for d in gefiltert if d["ort"] == filter_ort]
if filter_typ != "Alle":
    gefiltert = [d for d in gefiltert if d["typ"] == filter_typ]
if filter_name:
    gefiltert = [d for d in gefiltert if filter_name.lower() in d["name"].lower()]

if not gefiltert:
    st.info("Keine Einträge gefunden.")
else:
    # Nach Ort gruppieren
    for ort_name in ORTE:
        gruppe = [d for d in gefiltert if d["ort"] == ort_name]
        if not gruppe:
            continue

        st.subheader(f"{'🏠' if ort_name == 'Keller' else '☝️'} {ort_name}")

        for eintrag in gruppe:
            with st.container(border=True):
                c1, c2, c3, c4 = st.columns([3, 1, 2, 2])

                with c1:
                    emoji = TYP_EMOJI.get(eintrag["typ"], "📦")
                    st.markdown(f"**{emoji} {eintrag['name']}**")
                    meta = f"`{eintrag['typ']}` · {eintrag['anzahl']} Fl."
                    if eintrag.get("notiz"):
                        meta += f" · _{eintrag['notiz']}_"
                    st.caption(meta)

                with c2:
                    farbe = fuellstand_farbe(eintrag["fuell"])
                    st.markdown(f"{farbe} **{eintrag['fuell']}%**")
                    st.caption(fuellstand_balken(eintrag["fuell"]))

                with c3:
                    # Inline bearbeiten
                    neuer_fuell = st.slider(
                        "Füllstand",
                        0, 100, eintrag["fuell"], step=5,
                        key=f"fuell_{eintrag['id']}",
                        label_visibility="collapsed",
                    )
                    neue_anzahl = st.number_input(
                        "Anzahl",
                        min_value=0, max_value=999,
                        value=eintrag["anzahl"],
                        step=1,
                        key=f"anz_{eintrag['id']}",
                        label_visibility="collapsed",
                    )

                with c4:
                    # Umlagern
                    ziel = "Oben" if eintrag["ort"] == "Keller" else "Keller"
                    if st.button(f"↕️ nach {ziel}", key=f"move_{eintrag['id']}", use_container_width=True):
                        eintrag["ort"] = ziel
                        speichere_daten(daten)
                        st.rerun()

                    # Speichern (Füllstand / Anzahl)
                    if st.button("💾 Speichern", key=f"save_{eintrag['id']}", use_container_width=True):
                        eintrag["fuell"]   = int(neuer_fuell)
                        eintrag["anzahl"]  = int(neue_anzahl)
                        speichere_daten(daten)
                        st.success("Gespeichert!")
                        st.rerun()

                    # Löschen
                    if st.button("🗑️ Löschen", key=f"del_{eintrag['id']}", use_container_width=True, type="secondary"):
                        st.session_state[f"confirm_{eintrag['id']}"] = True

                    if st.session_state.get(f"confirm_{eintrag['id']}"):
                        st.warning(f"Wirklich löschen?")
                        col_j, col_n = st.columns(2)
                        if col_j.button("Ja", key=f"ja_{eintrag['id']}"):
                            st.session_state.daten = [d for d in daten if d["id"] != eintrag["id"]]
                            speichere_daten(st.session_state.daten)
                            st.rerun()
                        if col_n.button("Nein", key=f"nein_{eintrag['id']}"):
                            st.session_state[f"confirm_{eintrag['id']}"] = False
                            st.rerun()

# ── Footer ─────────────────────────────────────────────────────────────────────
st.divider()
st.caption(f"Daten gespeichert in `{DATA_FILE}` · {len(daten)} Positionen insgesamt")

import streamlit as st

st.set_page_config(
    page_title="SUAPS UPPA V14 Mobile",
    page_icon="🏃",
    layout="centered",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
.block-container{padding-top:1rem;padding-bottom:5rem;max-width:760px}
[data-testid="stSidebar"]{display:none}
.hero{background:linear-gradient(135deg,#062a5e,#0b72d0);color:white;padding:22px;border-radius:24px;margin-bottom:14px}
.hero h1{margin:0;font-size:2.15rem}.hero p{margin:.35rem 0 0;font-size:1.05rem;opacity:.94}
.card{border:1px solid rgba(120,120,120,.22);border-radius:18px;padding:15px;margin:9px 0;background:rgba(255,255,255,.04)}
.sport{font-size:1.1rem;font-weight:750}.muted{opacity:.76;font-size:.92rem;margin-top:3px}
div[data-testid="stMetric"]{border:1px solid rgba(120,120,120,.18);border-radius:18px;padding:12px}
div.stButton > button{border-radius:14px;min-height:44px}
</style>
""", unsafe_allow_html=True)

SPORTS = [
    ("🏊","Natation","Technique • Endurance • Performance"),
    ("🛟","Sauvetage","Prévenir • Intervenir • Se dépasser"),
    ("🏄","Surf","Glisse • Équilibre • Sensations"),
    ("🏉","Rugby","Équipe • Engagement • Respect"),
    ("🏃","Course à pied","Endurance • Liberté • Progression"),
    ("🥎","Pelote Basque","Adresse • Vitesse • Tradition"),
]

if "page" not in st.session_state:
    st.session_state.page = "Accueil"

st.markdown(
    '<div class="hero"><h1>SUAPS UPPA</h1><p>Bouge ton campus, révèle ton potentiel !</p></div>',
    unsafe_allow_html=True
)

page = st.session_state.page

if page == "Accueil":
    st.subheader("Bienvenue 👋")
    st.write("Retrouve toutes les activités du SUAPS UPPA au même endroit.")

    st.markdown("### Choisis ton activité")
    for ico, title, desc in SPORTS:
        st.markdown(
            f'<div class="card"><div class="sport">{ico} {title}</div>'
            f'<div class="muted">{desc}</div></div>',
            unsafe_allow_html=True
        )

    st.info("👉 Utilise les onglets en bas pour t’inscrire, valider ta présence et consulter tes résultats.")

elif page == "Activités":
    st.subheader("6 activités, 6 ambiances")
    for ico, title, desc in SPORTS:
        st.markdown(
            f'<div class="card"><div class="sport">{ico} {title}</div>'
            f'<div class="muted">{desc}</div></div>',
            unsafe_allow_html=True
        )

elif page == "Inscription":
    st.subheader("Inscription en ligne")
    sport = st.selectbox("Activité", [s[1] for s in SPORTS])
    groupe = st.selectbox("Groupe", ["Tous niveaux","Débutant","Intermédiaire","Confirmé"])
    modalite = st.radio("Modalité", ["UET","UECF","Non noté"])
    if st.button("Valider mon inscription", use_container_width=True):
        st.success(f"Inscription enregistrée : {sport} • {groupe} • {modalite}")

elif page == "Présence":
    st.subheader("Présence")
    st.write("Validation prévue par QR code, NFC ou saisie manuelle.")
    st.info("📷 **Scanner le QR code de la séance**")
    if st.button("Valider ma présence manuellement", use_container_width=True):
        st.success("Présence validée ✅")

elif page == "Résultats":
    st.subheader("Mes résultats")
    st.metric("Moyenne générale","14,6 / 20")
    st.progress(72)
    st.caption("23 compétences acquises sur 32")
    st.write("🏊 100 m crawl — 1:18.45 — 14,5/20")
    st.write("🏃 Test VMA — 15,8 km/h — 16/20")
    st.write("🏉 Yo-Yo IR2 — 1040 m — 13/20")

st.divider()
cols = st.columns(5)
labels = [
    ("🏠","Accueil"),
    ("🏅","Activités"),
    ("📝","Inscription"),
    ("✅","Présence"),
    ("📊","Résultats")
]

for col, (ico, label) in zip(cols, labels):
    with col:
        if st.button(ico, key=f"nav_{label}", use_container_width=True, help=label):
            st.session_state.page = label
            st.rerun()

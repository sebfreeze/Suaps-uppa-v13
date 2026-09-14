from pathlib import Path

TARGET = Path('v14_core.py')
MARKER = '# QR_COURSE_REGISTRATION_V1'


def replace_once(text, old, new, label):
    if old not in text:
        raise RuntimeError(f"Point d'insertion introuvable: {label}")
    return text.replace(old, new, 1)


def patch_text(text):
    if MARKER in text:
        return text

    text = replace_once(
        text,
        'import streamlit as st\n',
        'import streamlit as st\nimport os\nfrom qr_registration import make_qr_png, new_registration_token, register_student_from_qr, registration_url\n\n' + MARKER + '\n',
        'imports',
    )

    text = replace_once(
        text,
        "    CREATE TABLE IF NOT EXISTS offres(id INTEGER PRIMARY KEY AUTOINCREMENT,activite TEXT NOT NULL,intitule TEXT NOT NULL,jour_horaire TEXT,lieu TEXT,capacite INTEGER DEFAULT 20,public TEXT DEFAULT 'Tous',ouverte INTEGER DEFAULT 1);",
        "    CREATE TABLE IF NOT EXISTS offres(id INTEGER PRIMARY KEY AUTOINCREMENT,activite TEXT NOT NULL,intitule TEXT NOT NULL,jour_horaire TEXT,lieu TEXT,capacite INTEGER DEFAULT 20,public TEXT DEFAULT 'Tous',ouverte INTEGER DEFAULT 1,inscription_token TEXT);",
        'schema',
    )

    old_exe = '''def exe(sql,p=()):
    c=db(); q=c.cursor(); q.execute(sql,p); c.commit(); x=q.lastrowid; c.close(); return x

for k,v in {"page":"Accueil","profil":None,"user_id":None,"admin_section":"Tableau de bord","family":None}.items():'''
    new_exe = '''def exe(sql,p=()):
    c=db(); q=c.cursor(); q.execute(sql,p); c.commit(); x=q.lastrowid; c.close(); return x


def ensure_qr_registration_schema():
    c=db()
    try:
        q=c.cursor()
        if bool(globals().get("USE_POSTGRES",False)):
            q.execute("ALTER TABLE offres ADD COLUMN IF NOT EXISTS inscription_token TEXT")
        else:
            cols=set()
            for r in q.execute("PRAGMA table_info(offres)").fetchall():
                try: cols.add(str(r["name"]))
                except Exception: cols.add(str(r[1]))
            if "inscription_token" not in cols:
                q.execute("ALTER TABLE offres ADD COLUMN inscription_token TEXT")
        q.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_offres_inscription_token ON offres(inscription_token)")
        c.commit()
    except Exception:
        try: c.rollback()
        except Exception: pass
        raise
    finally:
        c.close()

ensure_qr_registration_schema()

for k,v in {"page":"Accueil","profil":None,"user_id":None,"admin_section":"Tableau de bord","family":None}.items():'''
    text = replace_once(text, old_exe, new_exe, 'migration')

    route = '''def _registration_base_url():
    configured=os.getenv("APP_BASE_URL","").strip()
    if configured: return configured.rstrip("/")
    render_host=os.getenv("RENDER_EXTERNAL_HOSTNAME","").strip()
    if render_host: return "https://"+render_host
    return "http://localhost:8501"


def qr_inscription(token):
    topbar(); hero("Inscription par QR code","Vérifie le créneau puis confirme ton inscription.","INSCRIPTION SUAPS")
    token=str(token or "").strip()
    o=one("SELECT * FROM offres WHERE inscription_token=?",(token,))
    if not o:
        st.error("QR code invalide ou expiré.")
        return
    n=one("SELECT COUNT(*) n FROM inscriptions WHERE offre_id=? AND statut='Inscrit'",(o["id"],))
    inscrits=int(n["n"] if n else 0); capacite=max(0,int(o["capacite"] or 0)); dispo=max(0,capacite-inscrits)
    card(f"{o['activite']} — {o['intitule']}",f"🕒 {o['jour_horaire'] or 'À définir'} • 📍 {o['lieu'] or 'À définir'} • {dispo}/{capacite} places",[o["public"]])
    if not int(o["ouverte"] or 0):
        st.warning("Les inscriptions à ce créneau sont fermées.")
        return
    if o["public"]=="Personnel":
        st.warning("Ce QR code n'est pas ouvert aux inscriptions étudiantes.")
        return
    if dispo<=0:
        st.error("Créneau complet.")
        return
    _remaining=_auth_remaining("student_login") if "_auth_remaining" in globals() else 0
    if _remaining>0:
        st.error(f"Trop de tentatives. Réessaie dans {_remaining} seconde(s).")
        return
    with st.form("qr_course_registration"):
        email=st.text_input("Adresse e-mail étudiante")
        ident=st.text_input("Numéro étudiant",type="password")
        modalite=st.selectbox("Modalité",["UET","UECF","Non noté"])
        ok=st.form_submit_button("Confirmer mon inscription",type="primary",use_container_width=True)
    if ok:
        try:
            result=register_student_from_qr(db,token,email,ident,modalite,use_postgres=bool(globals().get("USE_POSTGRES",False)))
        except Exception:
            st.error("L'inscription n'a pas pu être enregistrée. Réessaie dans quelques instants.")
            return
        if result=="ok":
            if "_auth_ok" in globals(): _auth_ok("student_login")
            st.success("Inscription enregistrée ✅")
            st.caption("Tu apparais maintenant dans la liste des inscrits du créneau.")
        elif result=="duplicate": st.info("Tu es déjà inscrit à ce créneau.")
        elif result=="full": st.error("Créneau complet : la dernière place vient d'être prise.")
        elif result=="closed": st.warning("Les inscriptions viennent d'être fermées.")
        elif result=="forbidden": st.warning("Ce créneau n'est pas ouvert aux étudiants.")
        elif result in ("unknown_student","bad_credentials"):
            if "_auth_fail" in globals(): _auth_fail("student_login")
            st.error("E-mail ou numéro étudiant incorrect.")
        else: st.error("QR code invalide ou expiré.")


def inscriptions():'''
    text = replace_once(text, 'def inscriptions():', route, 'public QR route')

    teacher_anchor = '''            o=mp[st.selectbox("Modifier un créneau",list(mp))]
            with st.form("editslot"):'''
    teacher_ui = '''            o=mp[st.selectbox("Modifier un créneau",list(mp))]
            with st.expander("📱 QR code d'inscription",expanded=False):
                if o["public"]=="Personnel":
                    st.info("Ce créneau est réservé au personnel : aucun QR étudiant n'est généré.")
                else:
                    qr_token=o.get("inscription_token") if hasattr(o,"get") else o["inscription_token"]
                    qr_count=one("SELECT COUNT(*) n FROM inscriptions WHERE offre_id=? AND statut='Inscrit'",(o["id"],))
                    st.caption(f"{int(qr_count['n'] if qr_count else 0)}/{int(o['capacite'] or 0)} inscrit(s) actuellement")
                    qr_label="Renouveler le QR d'inscription" if qr_token else "Générer le QR d'inscription"
                    if st.button(qr_label,key=f"qr_course_{o['id']}",type="primary",use_container_width=True):
                        qr_token=new_registration_token()
                        exe("UPDATE offres SET inscription_token=? WHERE id=?",(qr_token,o["id"]))
                        st.success("QR code d'inscription généré."); st.rerun()
                    if qr_token:
                        qr_url=registration_url(_registration_base_url(),qr_token)
                        qr_png=make_qr_png(qr_url)
                        st.image(qr_png,width=280)
                        st.code(qr_url,language=None)
                        st.download_button("Télécharger le QR code",qr_png,file_name=f"qr_inscription_{o['id']}.png",mime="image/png",key=f"qr_download_{o['id']}",use_container_width=True)
                        st.caption("Renouveler le QR invalide immédiatement l'ancien code.")
            with st.form("editslot"):'''
    text = replace_once(text, teacher_anchor, teacher_ui, 'teacher QR controls')

    text = replace_once(
        text,
        'pages.get(st.session_state.page,accueil)()',
        '''_qr_registration_token=st.query_params.get("inscription")
if _qr_registration_token:
    qr_inscription(_qr_registration_token)
else:
    pages.get(st.session_state.page,accueil)()''',
        'QR dispatch',
    )
    return text


def main():
    text = TARGET.read_text(encoding='utf-8')
    patched = patch_text(text)
    TARGET.write_text(patched, encoding='utf-8')
    print('QR course registration patch applied' if patched != text else 'QR course registration patch already present')


if __name__ == '__main__':
    main()

from pathlib import Path

TARGET = Path('v14_core.py')
MARKER = '# MANUAL_COURSE_REGISTRATION_V1'


def replace_once(text, old, new, label):
    if old not in text:
        raise RuntimeError(f"Point d'insertion introuvable: {label}")
    return text.replace(old, new, 1)


def patch_text(text):
    if MARKER in text:
        return text

    old_import = 'from qr_registration import make_qr_png, new_registration_token, register_student_from_qr, registration_url\n'
    new_import = (
        'from qr_registration import make_qr_png, new_registration_token, register_student_from_qr, registration_url, '
        'register_student_manually, search_students\n\n' + MARKER + '\n'
    )
    text = replace_once(text, old_import, new_import, 'manual registration imports')

    anchor = '''                        st.caption("Renouveler le QR invalide immédiatement l'ancien code.")
            with st.form("editslot"):'''
    controls = '''                        st.caption("Renouveler le QR invalide immédiatement l'ancien code.")
            with st.expander("➕ Ajouter un étudiant manuellement",expanded=False):
                if o["public"]=="Personnel":
                    st.info("Ce créneau est réservé au personnel : l'ajout d'un étudiant n'est pas proposé.")
                else:
                    manual_query=st.text_input(
                        "Rechercher par nom, e-mail ou numéro étudiant",
                        key=f"manual_student_search_{o['id']}",
                        placeholder="Ex. Dupont, paul@etu.univ-pau.fr ou 12345678",
                    )
                    if manual_query.strip():
                        manual_matches=search_students(db,manual_query,limit=20)
                        if not manual_matches:
                            st.info("Aucun étudiant actif trouvé.")
                        else:
                            manual_options={
                                f"{s['nom']} {s['prenom']} — {s['identifiant'] or 'sans numéro'} — {s['email']}":s
                                for s in manual_matches
                            }
                            manual_label=st.selectbox(
                                "Étudiant",
                                list(manual_options),
                                key=f"manual_student_choice_{o['id']}",
                            )
                            manual_modalite=st.selectbox(
                                "Modalité d'inscription",
                                ["UET","UECF","Non noté"],
                                key=f"manual_student_modality_{o['id']}",
                            )
                            if st.button(
                                "Ajouter au créneau",
                                key=f"manual_student_add_{o['id']}",
                                type="primary",
                                use_container_width=True,
                            ):
                                selected_student=manual_options[manual_label]
                                try:
                                    manual_result=register_student_manually(
                                        db,o["id"],selected_student["id"],manual_modalite,
                                        use_postgres=bool(globals().get("USE_POSTGRES",False)),
                                    )
                                except Exception:
                                    st.error("L'ajout manuel n'a pas pu être enregistré.")
                                else:
                                    if manual_result=="ok":
                                        st.success(f"{selected_student['prenom']} {selected_student['nom']} a été ajouté(e) au créneau ✅")
                                    elif manual_result=="duplicate":
                                        st.info("Cet étudiant est déjà inscrit à ce créneau.")
                                    elif manual_result=="full":
                                        st.error("Créneau complet : aucune place disponible.")
                                    elif manual_result=="unknown_student":
                                        st.error("Le compte étudiant n'est plus actif ou n'existe plus.")
                                    else:
                                        st.error("L'inscription manuelle n'a pas pu être enregistrée.")
            with st.form("editslot"):'''
    text = replace_once(text, anchor, controls, 'manual registration teacher controls')
    return text


def main():
    text = TARGET.read_text(encoding='utf-8')
    patched = patch_text(text)
    TARGET.write_text(patched, encoding='utf-8')
    print('Manual course registration patch applied' if patched != text else 'Manual course registration patch already present')


if __name__ == '__main__':
    main()

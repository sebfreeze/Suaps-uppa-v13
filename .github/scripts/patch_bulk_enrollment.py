from pathlib import Path

TARGET = Path("v14_core.py")
MARKER = "# PRIVATE_BULK_ENROLLMENT_BRIDGE_V1"


def replace_once(text, old, new, label):
    if old not in text:
        raise RuntimeError(f"Point d'insertion introuvable: {label}")
    return text.replace(old, new, 1)


def patch_text(text):
    if MARKER in text:
        return text

    old_import = (
        "from qr_registration import make_qr_png, new_registration_token, "
        "register_student_from_qr, registration_url, register_student_manually, search_students\n"
    )
    new_import = old_import + "from bulk_enrollment import apply_bulk_enrollment_json\n"
    text = replace_once(text, old_import, new_import, "bulk enrollment import")

    anchor = '''ensure_qr_registration_schema()\n\nfor k,v in {"page":"Accueil","profil":None,"user_id":None,"admin_section":"Tableau de bord","family":None}.items():'''
    bridge = '''ensure_qr_registration_schema()\n\n# PRIVATE_BULK_ENROLLMENT_BRIDGE_V1\n@st.cache_resource(show_spinner=False)\ndef _run_private_bulk_enrollment_once():\n    raw=os.getenv("SUAPS_BULK_ENROLL_JSON","").strip()\n    if not raw:\n        return None\n    try:\n        result=apply_bulk_enrollment_json(\n            db,raw,use_postgres=bool(globals().get("USE_POSTGRES",False))\n        )\n    except Exception as exc:\n        print(f"[SUAPS_BULK_ENROLL] status=error type={type(exc).__name__}")\n        return {"status":"error"}\n    status=str(result.get("status") or "unknown")\n    if status=="ok":\n        print(\n            f"[SUAPS_BULK_ENROLL] status=ok enrolled={int(result.get('enrolled') or 0)} "\n            f"created={int(result.get('created') or 0)} updated={int(result.get('updated') or 0)} "\n            f"offer_id={result.get('offer_id')}"\n        )\n    elif status=="missing_students":\n        print(f"[SUAPS_BULK_ENROLL] status=missing_students missing={result.get('missing') or []}")\n    elif status=="ambiguous_students":\n        print(f"[SUAPS_BULK_ENROLL] status=ambiguous_students ambiguous={result.get('ambiguous') or []}")\n    else:\n        print(f"[SUAPS_BULK_ENROLL] status={status} details={result}")\n    return result\n\n_run_private_bulk_enrollment_once()\n\nfor k,v in {"page":"Accueil","profil":None,"user_id":None,"admin_section":"Tableau de bord","family":None}.items():'''
    text = replace_once(text, anchor, bridge, "private runtime bridge")
    return text


def main():
    text = TARGET.read_text(encoding="utf-8")
    patched = patch_text(text)
    TARGET.write_text(patched, encoding="utf-8")
    print("Bulk enrollment bridge patch applied" if patched != text else "Bulk enrollment bridge already present")


if __name__ == "__main__":
    main()

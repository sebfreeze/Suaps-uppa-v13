from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "hotfix_bootstrap"))

from resp_options_hotfix import repair_source


def test_repairs_missing_responsable_options_before_first_use():
    broken = '''def admin():
    if sec=="Créneaux":
        o=mp[st.selectbox("Modifier un créneau",list(mp))]
        with st.form("editslot"):
            e,f=st.columns(2); ec=e.number_input("Capacité",1,200,int(o["capacite"])); ep=f.selectbox("Public",["Tous","Étudiants","Personnel"])
            _can_change_resp=st.session_state.get("teacher_role")=="Admin"
            r1,r2=st.columns(2)
            eresp=r1.selectbox("Responsable",_resp_options,index=_resp_options.index(_current_resp) if _current_resp in _resp_options else 0)
'''
    fixed = repair_source(broken)
    assert '_resp_options=["— Non attribué —"]+_resp_names' in fixed
    assert fixed.index('_resp_options=["— Non attribué —"]+_resp_names') < fixed.index('eresp=r1.selectbox')
    compile(fixed, '<hotfix-test>', 'exec')


def test_does_not_duplicate_existing_definition():
    source = '''def admin():
    _resp_names=[]
    _resp_options=["— Non attribué —"]+_resp_names
    _can_change_resp=True
    eresp=r1.selectbox("Responsable",_resp_options)
'''
    fixed = repair_source(source)
    assert fixed == source

import streamlit as st
from api.knowledge_api import KnowledgeAPI
import uuid

st.title("ナレッジ管理")

api = KnowledgeAPI()

# 初期データのロード
if "knowledge_list" not in st.session_state:
    try:
        st.session_state["knowledge_list"] = api.get_knowledge_list()
    except Exception:
        st.session_state["knowledge_list"] = []

if "selected" not in st.session_state and st.session_state["knowledge_list"]:
    st.session_state["selected"] = st.session_state["knowledge_list"][0]

left_col, right_col = st.columns([1, 2])

with left_col:
    # 契約種別の取得
    try:
        contract_types = api.get_contract_types()
        type_names = [
            t.get("contract_type")
            for t in contract_types
            if isinstance(t, dict) and t.get("contract_type")
        ]
        if not type_names:
            type_names = ["汎用", "秘密保持", "業務委託", "共同開発", "共同出願"]
    except Exception:
        type_names = ["汎用", "秘密保持", "業務委託", "共同開発", "共同出願"]

    contract_filter = st.selectbox("契約種別", ["すべて"] + type_names)
    search_text = st.text_input("検索")
    if st.button("検索"):
        ctype = None if contract_filter == "すべて" else contract_filter
        try:
            st.session_state["knowledge_list"] = api.get_knowledge_list(ctype, search_text or None)
        except Exception:
            st.session_state["knowledge_list"] = []

    knowledge_options = st.session_state.get("knowledge_list", [])
    option_labels = [
        f"{k.get('knowledge_number')} v{k.get('version')} {k.get('knowledge_title', '')}"
        for k in knowledge_options
    ]
    if option_labels:
        selected_label = st.radio("ナレッジ一覧", option_labels)
        if selected_label:
            knum_part, rest = selected_label.split(" v", 1)
            ver_part = rest.split(" ", 1)[0]
            try:
                refreshed = api.get_knowledge_list()
            except Exception:
                refreshed = []
            selected = next(
                (
                    k
                    for k in refreshed
                    if str(k.get("knowledge_number")) == knum_part
                    and str(k.get("version")) == ver_part
                ),
                None,
            )
            if selected:
                st.session_state["selected"] = selected
    if st.button("新規追加"):
        try:
            new_number = api.get_max_knowledge_number() + 1
        except Exception:
            new_number = 1
        st.session_state["selected"] = {
            "knowledge_number": new_number,
            "version": 1,
            "contract_type": type_names[0] if type_names else "",
            "knowledge_title": "",
            "review_points": "",
            "action_plan": "",
            "clause_sample": "",
            "record_status": "latest",
            "approval_status": "draft",
        }

with right_col:
    selected = st.session_state.get("selected")
    if selected:
        with st.form("detail_form"):
            st.markdown(
                f"**No:** {selected.get('knowledge_number', '')}  \n**Version:** {selected.get('version', '')}"
            )
            st.markdown(
                f"record_status: {selected.get('record_status', '')}  \napproval_status: {selected.get('approval_status', '')}"
            )
            contract_type = st.selectbox(
                "契約種別",
                type_names,
                index=type_names.index(selected.get("contract_type", type_names[0]))
                if selected.get("contract_type", type_names[0]) in type_names
                else 0,
            )
            title = st.text_area("タイトル", selected.get("knowledge_title", ""))
            review = st.text_area("審査観点", selected.get("review_points", ""))
            action = st.text_area("対応策", selected.get("action_plan", ""))
            clause = st.text_area("条項サンプル", selected.get("clause_sample", ""))

            save_btn = st.form_submit_button(
                "保存", disabled=selected.get("approval_status") != "draft"
            )
            revise_btn = st.form_submit_button(
                "改訂", disabled=selected.get("approval_status") != "approved"
            )
            apply_btn = st.form_submit_button(
                "承認申請", disabled=selected.get("approval_status") not in ("draft", "submitted")
            )
            approve_btn = st.form_submit_button(
                "承認", disabled=selected.get("approval_status") != "submitted"
            )
        if save_btn:
            data = dict(selected)
            data.update(
                {
                    "contract_type": contract_type,
                    "knowledge_title": title,
                    "review_points": review,
                    "action_plan": action,
                    "clause_sample": clause,
                }
            )
            try:
                st.session_state["selected"] = api.save_knowledge_draft(data)
                st.success("保存しました")
            except Exception as e:
                st.error(f"保存に失敗しました: {e}")
        if revise_btn:
            if selected.get("approval_status") == "approved":
                try:
                    old = dict(selected)
                    old["record_status"] = "superseded"
                    api.save_knowledge_draft(old)
                    new_data = dict(selected)
                    new_data.pop("id", None)
                    new_data["version"] = selected.get("version", 0) + 1
                    new_data["record_status"] = "latest"
                    new_data["approval_status"] = "draft"
                    new_data.update(
                        {
                            "contract_type": contract_type,
                            "knowledge_title": title,
                            "review_points": review,
                            "action_plan": action,
                            "clause_sample": clause,
                        }
                    )
                    st.session_state["selected"] = api.save_knowledge_draft(new_data)
                    st.success("改訂しました")
                except Exception as e:
                    st.error(f"改訂に失敗しました: {e}")
            else:
                st.warning("承認済みのみ改訂できます。")
        if apply_btn and selected.get("id"):
            new_status = (
                "submitted" if selected.get("approval_status") == "draft" else "draft"
            )
            try:
                api.update_approval_status(selected["id"], new_status)
                selected["approval_status"] = new_status
                st.session_state["selected"] = selected
                st.success("承認申請を更新しました")
            except Exception as e:
                st.error(f"承認申請に失敗しました: {e}")
        if approve_btn and selected.get("id"):
            try:
                api.update_approval_status(selected["id"], "approved")
                api.save_knowledge_with_vectors(selected)
                selected["approval_status"] = "approved"
                st.session_state["selected"] = selected
                st.success("承認しました")
            except Exception as e:
                st.error(f"承認に失敗しました: {e}")

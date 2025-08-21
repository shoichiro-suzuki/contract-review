import streamlit as st
from api.contract_api import ContractAPI

st.title("契約閲覧")

api = ContractAPI()

# --- load contract types ---------------------------------------------------
try:
    contract_types = api.get_contract_types()
    type_names = [
        t.get("contract_type")
        for t in contract_types
        if isinstance(t, dict) and t.get("contract_type")
    ]
    if not type_names:
        raise ValueError
except Exception:
    type_names = ["汎用"]

left, right = st.columns([1, 2])

with left:
    contract_filter = st.selectbox("契約種別", ["すべて"] + type_names)
    search_text = st.text_input("検索")
    if st.button("検索"):
        try:
            contracts = api.get_approved_contracts()
        except Exception:
            contracts = []
        filtered = []
        for c in contracts:
            if contract_filter != "すべて" and c.get("contract_type") != contract_filter:
                continue
            if search_text and search_text not in c.get("title", "") and search_text not in ",".join(c.get("partys", [])):
                continue
            filtered.append(c)
        st.session_state["contracts"] = filtered
    if "contracts" not in st.session_state:
        try:
            st.session_state["contracts"] = api.get_approved_contracts()
        except Exception:
            st.session_state["contracts"] = []
    contracts = st.session_state.get("contracts", [])
    labels = [f"{c.get('contract_type')} - {c.get('title','')}" for c in contracts]
    selected_label = st.radio("契約一覧", labels) if labels else None
    if selected_label:
        idx = labels.index(selected_label)
        st.session_state["selected_contract"] = contracts[idx]

with right:
    contract = st.session_state.get("selected_contract")
    if contract:
        st.write(f"契約種別: {contract.get('contract_type','')}")
        st.write(f"契約当事者: {', '.join(contract.get('partys', []))}")
        st.write(f"背景情報: {contract.get('background_info','')}")
        st.write(f"タイトル: {contract.get('title','')}")
        st.write(f"前文: {contract.get('introduction','')}")
        for clause in contract.get("clauses", []):
            st.markdown(f"### 条項{clause.get('clause_number','')}")
            st.write(clause.get("clause", ""))
            if clause.get("review_points"):
                st.write(f"審査観点: {clause['review_points']}")
            if clause.get("action_plan"):
                st.write(f"アクションプラン: {clause['action_plan']}")
        if st.button("ドラフトに戻す"):
            try:
                contract["approval_status"] = "draft"
                api.upsert_contract(contract)
                st.success("ドラフトに戻しました")
            except Exception as e:
                st.error(f"更新に失敗しました: {e}")

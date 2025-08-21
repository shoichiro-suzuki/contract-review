import streamlit as st

st.title("契約審査サポートアプリ")
st.page_link("new_contract_window.py", label="契約登録・修正", icon="📝")
st.page_link("analyze_contract_window.py", label="契約審査", icon="🔍")
st.page_link("view_contract_window.py", label="契約閲覧", icon="📄")
st.page_link("pages/knowledge.py", label="ナレッジ管理", icon="📚")

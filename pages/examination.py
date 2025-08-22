import streamlit as st
from api.contract_api import ContractAPI
from api.knowledge_api import KnowledgeAPI
from api.examination_api import examination_api
from services.document_input import extract_text_from_document
import tempfile
import os

st.set_page_config(layout="wide")


def main():
    st.title("契約審査")
    if "contract_api" not in st.session_state:
        st.session_state["contract_api"] = ContractAPI()
    api = st.session_state["contract_api"]
    if "knowledge_api" not in st.session_state:
        st.session_state["knowledge_api"] = KnowledgeAPI()
    if "knowledge_all" not in st.session_state:
        try:
            st.session_state["knowledge_all"] = api.get_knowledge_list()
        except Exception:
            st.session_state["knowledge_all"] = []

    # --- state initialization --------------------------------------------------
    if "exam_contract_id" not in st.session_state:
        st.session_state["exam_contract_id"] = None
    if "exam_contract_type" not in st.session_state:
        st.session_state["exam_contract_type"] = ""
    if "exam_partys" not in st.session_state:
        st.session_state["exam_partys"] = ""
    if "exam_background" not in st.session_state:
        st.session_state["exam_background"] = ""
    if "exam_title" not in st.session_state:
        st.session_state["exam_title"] = ""
    if "exam_intro" not in st.session_state:
        st.session_state["exam_intro"] = ""
    if "exam_clauses" not in st.session_state:
        st.session_state["exam_clauses"] = []
    if "exam_page_status" not in st.session_state:
        st.session_state["exam_page_status"] = "start"

    # --- file upload -----------------------------------------------------------
    uploaded = st.file_uploader("契約ファイル選択")
    if st.button("契約案から条文抽出", disabled=uploaded is None):
        if uploaded is not None:
            with st.spinner("解析中...", show_time=True):
                with tempfile.NamedTemporaryFile(
                    delete=False, suffix=os.path.splitext(uploaded.name)[1]
                ) as tmp_file:
                    tmp_file.write(uploaded.read())
                    tmp_path = tmp_file.name
                try:
                    result = extract_text_from_document(tmp_path)
                    if "error" in result:
                        st.error(result["error"])
                    else:
                        st.session_state["exam_title"] = result.get("title", "")
                        st.session_state["exam_intro"] = result.get("introduction", "")
                        st.session_state["exam_clauses"] = [
                            {
                                "clause_number": c.get("clause_number", ""),
                                "clause": c.get("text", ""),
                                "review_points": "",
                                "action_plan": "",
                            }
                            for c in result.get("clauses", [])
                        ]
                        st.session_state["exam_signature_section"] = result.get(
                            "signature_section", ""
                        )
                        st.session_state["exam_attachments"] = result.get(
                            "attachments", ""
                        )
                        st.success("解析完了")
                        st.session_state["exam_page_status"] = "document_loaded"
                except Exception as e:
                    st.error(f"解析に失敗しました: {e}")
                finally:
                    if os.path.exists(tmp_path):
                        os.remove(tmp_path)
        else:
            st.warning("ファイルを選択してください。")
    st.markdown("---")

    if (
        st.session_state["exam_page_status"] == "document_loaded"
        or st.session_state["exam_page_status"] == "examination"
    ):
        col_partys, col_contract_type = st.columns([2, 1])
        # --- contract type ---------------------------------------------------------
        with col_contract_type:
            if "exam_contract_types" not in st.session_state:
                try:
                    st.session_state["exam_contract_types"] = api.get_contract_types()
                except Exception:
                    st.session_state["exam_contract_types"] = []
            contract_types = st.session_state["exam_contract_types"]
            try:
                type_map = {
                    t.get("contract_type", ""): t.get("id")
                    for t in contract_types
                    if isinstance(t, dict) and t.get("contract_type")
                }
                if not type_map:
                    raise ValueError("no contract types")
            except Exception:
                type_map = {"汎用": None}
            current_type = st.selectbox(
                "契約種別", list(type_map.keys()), key="exam_contract_type"
            )

        # --- basic information -----------------------------------------------------
        with col_partys:
            st.text_input(
                "契約当事者（カンマ区切り）",
                key="exam_partys",
                placeholder="例: 甲社,乙社",
            )

        col_title, col_background = st.columns([1, 3])
        with col_title:
            st.text_input("タイトル", key="exam_title")
        with col_background:
            st.text_area("背景情報", height=75, key="exam_background")

        st.text_area("前文", height=75, key="exam_intro")
        st.markdown("---")

        # --- clauses ---------------------------------------------------------------
        st.subheader("条文")
        for idx, clause in enumerate(st.session_state["exam_clauses"]):
            col_num, col_clause = st.columns([1, 9])
            with col_num:
                st.text_input(
                    "条項番号",
                    value=clause.get("clause_number", ""),
                    key=f"exam_clause_number_{idx}",
                )
            with col_clause:
                st.text_area(
                    "条文",
                    clause.get("clause", ""),
                    key=f"exam_clause_{idx}",
                    height="content",
                )

                # 審査結果（懸念事項）の表示
                if st.session_state.get("analyzed_clauses"):
                    for analyzed in st.session_state["analyzed_clauses"]:
                        if analyzed.get("clause_number") == clause.get("clause_number"):
                            if analyzed.get("amendment_clause"):
                                st.markdown("---")
                                # st.markdown("**修正条文：**")
                                st.text_area(
                                    "修正条文：",
                                    f"{analyzed.get('amendment_clause', '')}",
                                    height="content",
                                )
                                # st.markdown(
                                #     analyzed.get("amendment_clause", "").replace(
                                #         "\n", "<br>"
                                #     ),
                                #     unsafe_allow_html=True,
                                # )
                                st.markdown("**懸念事項：**")
                                st.markdown(
                                    analyzed.get("concern", "").replace("\n", "<br>"),
                                    unsafe_allow_html=True,
                                )
                            else:
                                st.markdown("---")
                                st.markdown("懸念事項なし")

            st.markdown("---")

        def collect_exam_clauses():
            clauses = []
            for idx in range(len(st.session_state["exam_clauses"])):
                clauses.append(
                    {
                        "clause_number": st.session_state.get(
                            f"exam_clause_number_{idx}", ""
                        ),
                        "clause": st.session_state.get(f"exam_clause_{idx}", ""),
                    }
                )
            return clauses

        # --- action buttons -------------------------------------------------------

        exam_clicked = st.button("審査開始")

        if exam_clicked:
            contract_type = st.session_state["exam_contract_type"]
            background_info = st.session_state["exam_background"]
            partys = [
                p.strip()
                for p in st.session_state["exam_partys"].split(",")
                if p.strip()
            ]
            introduction = st.session_state["exam_intro"]
            title = st.session_state["exam_title"]
            clauses = collect_exam_clauses()
            with st.spinner("審査中...", show_time=True):
                try:
                    analyzed_clauses = examination_api(
                        contract_type=contract_type,
                        background_info=background_info,
                        partys=partys,
                        introduction=introduction,
                        title=title,
                        clauses=clauses,
                        knowledge_all=st.session_state["knowledge_all"],
                    )
                    if not analyzed_clauses:
                        st.info("審査結果がありません。")
                    else:
                        st.session_state["analyzed_clauses"] = analyzed_clauses
                        st.session_state["exam_page_status"] = "examination"
                        st.rerun()
                except Exception as e:
                    st.error(f"審査処理でエラーが発生しました: {e}")
    if st.session_state["exam_page_status"] == "examination":
        st.success("審査結果を表示しました。")


if __name__ == "__main__":
    main()

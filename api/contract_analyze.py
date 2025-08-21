from PySide6.QtCore import QThread, Signal
from services.document_input import extract_text_from_document
import os
import json


class AnalyzeWorker(QThread):
    finished = Signal(dict)
    error = Signal(str)

    def __init__(self, api, file_path):
        super().__init__()
        self.api = api
        self.file_path = file_path

    def run(self):
        try:
            result = extract_text_from_document(self.file_path)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


from PySide6.QtWidgets import QMessageBox
from api.contract_api import ContractAPI

contract_api = ContractAPI()


def examination_api(
    settings,
    contract_type_combo,
    background_info_edit,
    partys_edit,
    introduction_edit,
    title_edit,
    clauses_layout,
    intro_label,
    introduction_edit_widget,
    parent=None,
):
    # contract_id = settings.value("contract_master_id", type=str)
    partys_text = partys_edit.text().strip()
    partys = [p.strip() for p in partys_text.split(",") if p.strip()]
    clauses = []
    from PySide6.QtWidgets import QTextEdit, QLineEdit

    for i in range(clauses_layout.count()):
        clause_widget = clauses_layout.itemAt(i).widget()
        if (
            clause_widget is None
            or clause_widget == introduction_edit_widget
            or clause_widget == intro_label
        ):
            continue
        text_edits = clause_widget.findChildren(QTextEdit)
        if not text_edits:
            continue
        clause_number = clause_widget.findChild(QLineEdit)
        clause_text = text_edits[0].toPlainText()
        review_points = text_edits[1].toPlainText() if len(text_edits) > 1 else ""
        action_plan = text_edits[2].toPlainText() if len(text_edits) > 2 else ""
        if not clause_text.strip():
            continue
        clause_id = getattr(clause_widget, "clause_id", None)
        if not clause_id:
            import uuid

            clause_id = str(uuid.uuid4())
        clause_obj = {
            "clause_id": clause_id,
            "clause_number": clause_number.text() if clause_number else "",
            "clause": clause_text,
            "contents_type": "clauses",
            "review_points": review_points,
            "action_plan": action_plan,
        }
        clauses.append(clause_obj)
    data = {
        "contract_master_id": "",
        "contract_type": contract_type_combo.currentText(),
        "background_info": background_info_edit.toPlainText(),
        "partys": partys,
        "introduction": introduction_edit.toPlainText(),
        "title": title_edit.text(),
        "clauses": clauses,
    }
    sample_path = os.path.join(
        os.path.dirname(__file__), "..", "Examination_data_sample.py"
    )
    sample_path = os.path.abspath(sample_path)

    # # RAGベースの契約審査を実行
    analyzed_clauses = []

    # 1. ナレッジベースからの知識抽出
    from api.contract_api import ContractAPI

    contract_api = ContractAPI()
    try:
        knowledge_entries = []
        knowledge_entries = contract_api.get_knowledge_entries(data["contract_type"])
    except Exception as e:
        print(f"Error occurred: {e}")

    # 2. 各条項に対して類似条項の検索とナレッジ抽出
    similar_clauses_knowledge = []
    # いったんキャンセルするがコメントアウトは消すな！
    # similar_clauses_knowledge = search_similar_clauses(clauses, contract_api)

    print("[LOG] --- 3. 審査処理フロー 開始 ---")

    # 1. knowledge_entries をn個ずつのクラスターに分割
    def chunk_list(lst, n):
        """リストをn個ずつに分割"""
        for i in range(0, len(lst), n):
            yield lst[i : i + n]

    cluster_size = 2  # クラスタサイズは適宜調整
    knowledge_clusters = list(chunk_list(knowledge_entries, cluster_size))
    print(
        f"[LOG] knowledge_entries数: {len(knowledge_entries)} → クラスタ数: {len(knowledge_clusters)} (1クラスタ{cluster_size}件)"
    )

    # 2. LLMに対して、審査対象[data]と審査知見[knowledge_entries]を渡し、審査結果を取得
    def call_llm_for_review(data, knowledge_cluster):
        """
        data: dict, knowledge_cluster: list
        AzureOpenAIServiceのget_openai_response_gpt41nano()で審査を行う
        """
        from azure_.openai_service import AzureOpenAIService
        import json

        print(f"[LOG] LLM呼び出し: knowledge_cluster件数={len(knowledge_cluster)}")
        service = AzureOpenAIService()
        # knowledge_entriesのidを明示する
        # プロンプト生成
        system_prompt = (
            "あなたは契約審査の専門家です。以下の審査対象データと審査知見をもとに、各条項ごとに懸念点と対応策を日本語で出力してください。\n"
            "審査の根拠とする knowledge_ids を必ず提示し、提供する審査知見以外を利用した審査は絶対にしないでください。\n"
            '審査の結果懸念がない場合は、"concern" および "action_plan" を null で出力してください。\n'
            "根拠とする knowledge_ids を必ず提示し、提供する審査知見以外を利用した審査は絶対にしないでください。\n"
            "【出力形式】\n"
            "必ず以下の厳格なJSON配列形式で出力してください。\n"
            "[\n"
            "  {\n"
            '    "clause_number": <条項番号（文字列）>,\n'
            '    "concern": <懸念点> or null,\n'
            '    "action_plan": <対応策> or null,\n'
            '    "knowledge_ids": [<リスク知見IDの配列>]\n'
            "  }, ...\n"
            "]\n"
        )
        prompt = (
            "【審査対象データ】\n"
            f"{json.dumps(data, ensure_ascii=False)}\n"
            "【審査知見（knowledge_entriesクラスタ）】\n"
            f"{json.dumps(knowledge_cluster, ensure_ascii=False)}\n\n"
            "審査は提供する審査知見以外を絶対に利用しないでください。"
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ]
        try:
            # answer = service.get_openai_response_gpt41(messages)
            answer = service.get_openai_response_gpt5_mini(messages)
            print(f"[LOG] LLM応答取得: {str(answer)[:50]} ...")
        except Exception as e:
            print(f"[LOG] LLM呼び出しエラー: {e}")
            # エラー時は空欄返す
            return [
                {
                    "clause_number": clause["clause_number"],
                    "concern": f"LLMエラー: {e}",
                    "action_plan": "",
                    "knowledge_ids": [],
                }
                for clause in data["clauses"]
            ]

        # answerを厳格なJSON配列としてパース
        def try_parse_json_llm_response(resp, max_retry=2):
            for retry in range(max_retry):
                try:
                    result = json.loads(resp)
                    print(f"[LOG] LLMパース結果: {str(result)[:100]}")
                    return result
                except Exception as e:
                    print(f"[LOG] LLM応答JSONパースエラー({retry+1}回目): {e}")
                    if retry < max_retry - 1:
                        # LLMでJSON整形を依頼
                        from azure_.openai_service import AzureOpenAIService

                        service = AzureOpenAIService()
                        fix_prompt = (
                            "以下のテキストはJSON配列として不正な形式です。絶対に他のテキストや説明を含めず、厳格なJSON配列のみを出力してください。\n"
                            "【期待するJSON配列の出力例】\n"
                            "[\n"
                            '  {"clause_number": "1", "concern": "懸念点例", "action_plan": "対応策例", "knowledge_ids": ["id1", "id2"]},\n'
                            '  {"clause_number": "2", "concern": "", "action_plan": "", "knowledge_ids": []}\n'
                            "]\n"
                            "【不正なJSONテキスト】\n"
                            f"{resp}"
                        )
                        fix_messages = [
                            {
                                "role": "system",
                                "content": "あなたはJSON整形の専門家です。",
                            },
                            {"role": "user", "content": fix_prompt},
                        ]
                        try:
                            resp, _, _ = service.get_openai_response_gpt41mini(
                                fix_messages, 2000
                            )
                            print(f"[LOG] LLMによるJSON整形応答: {str(resp)[:100]} ...")
                        except Exception as e2:
                            print(f"[LOG] LLMによるJSON整形リトライ失敗: {e2}")
                            break
                    else:
                        break
            # 2回失敗時は空欄返す
            return [
                {
                    "clause_number": clause["clause_number"],
                    "concern": f"LLM応答パースエラー: {e}",
                    "action_plan": "",
                    "knowledge_ids": [],
                }
                for clause in data["clauses"]
            ]

        result = try_parse_json_llm_response(answer, max_retry=2)
        return result

    # クラスタごとに審査
    cluster_results = []
    for idx, cluster in enumerate(knowledge_clusters):
        print(f"[LOG] クラスタ{idx+1}/{len(knowledge_clusters)} 審査開始")
        review_result = call_llm_for_review(data, cluster)
        cluster_results.append(review_result)
        print(f"[LOG] クラスタ{idx+1} 審査完了")

    # 3. knowledge_entries クラスター毎に出力された審査結果を統合
    print("[LOG] クラスタごとの審査結果を統合中 ...")
    from collections import defaultdict

    merged = defaultdict(
        lambda: {"concern": [], "action_plan": [], "knowledge_ids": []}
    )
    for cluster in cluster_results:
        for item in cluster:
            num = item["clause_number"]
            if item["concern"]:
                merged[num]["concern"].append(item["concern"])
            if item["action_plan"]:
                merged[num]["action_plan"].append(item["action_plan"])
            merged[num]["knowledge_ids"].extend(item["knowledge_ids"])

    # 最終的な審査結果リストを生成
    print("[LOG] 最終的な審査結果リストを生成 ...")
    analyzed_clauses = []
    for clause in data["clauses"]:
        num = clause["clause_number"]
        analyzed_clauses.append(
            {
                "clause_number": num,
                "concern": "\n".join(merged[num]["concern"]),
                "action_plan": "\n".join(merged[num]["action_plan"]),
                "knowledge_ids": list(set(merged[num]["knowledge_ids"])),
            }
        )
    print(f"[LOG] analyzed_clauses: {str(analyzed_clauses)[:100]}")

    print("[LOG] --- 3. 審査処理フロー 終了 ---")

    # Pythonファイルとして書き込む
    with open(sample_path, "w", encoding="utf-8") as f:
        f.write("Examination_data = ")
        json.dump(data, f, ensure_ascii=False, indent=4)
        f.write("\n")
        f.write("knowledge_entries = ")
        json.dump(knowledge_entries, f, ensure_ascii=False, indent=4)
        f.write("\n")
        f.write("similar_clauses_knowledge = ")
        json.dump(similar_clauses_knowledge, f, ensure_ascii=False, indent=4)
        f.write("\n")
        f.write("Analyzed_clauses = ")
        json.dump(analyzed_clauses, f, ensure_ascii=False, indent=4)
        f.write("\n")

    return analyzed_clauses


def search_similar_clauses(clauses, contract_api):
    similar_clauses_knowledge = []
    for clause in clauses:
        print("Clause: ")
        print(clause["clause"][:50])

        clause_text = clause["clause"]
        clause_number = clause["clause_number"]

        # 類似条項の検索とナレッジ抽出
        try:
            similar_clauses = contract_api.search_similar_clauses(clause_text, top_k=3)
        except Exception as e:
            print(f"Error occurred: {e}")
            continue

        # clause_numberと対応付けて、抽出した similar_clauses のclause_id, c.clause, c.review_points, c.action_plan,を格納する
        similar_clauses_knowledge.append(
            {
                "clause_number": clause_number,
                "similar_clauses": [
                    {
                        "clause_id": c["clause_id"],
                        "clause": c["clause"],
                        "review_points": c["review_points"],
                        "action_plan": c["action_plan"],
                    }
                    for c in similar_clauses
                ],
            }
        )

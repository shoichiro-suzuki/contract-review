def examination_api(
    contract_type: str,
    background_info: str,
    partys: list,
    title: str,
    clauses: list,
    knowledge_all: list,
):
    """
    Streamlit用: UI部品を使わず、値を直接受け取って審査処理を行う
    Args:
        contract_type (str): 契約種別
        background_info (str): 背景情報
        partys (list): 当事者リスト
        title (str): タイトル
        clauses (list): 条文リスト（dictのリスト、各要素はclause_number, clause, review_points, action_planを含む）
    Returns:
        analyzed_clauses (list): 審査結果リスト
    """
    import os
    import json

    data = {
        "contract_master_id": "",
        "contract_type": contract_type,
        "background_info": background_info,
        "partys": partys,
        "title": title,
        "clauses": [
            {
                "clause_id": c.get("clause_id", ""),
                "clause_number": c.get("clause_number", ""),
                "clause": c.get("clause", ""),
                "knowledge_id": c.get("knowledge_id", []),
            }
            for c in clauses
        ],
    }
    sample_path = os.path.join(
        os.path.dirname(__file__), "..", "Examination_data_sample.py"
    )
    sample_path = os.path.abspath(sample_path)

    analyzed_clauses = []
    similar_clauses_knowledge = []

    # knowledge_idのユニーク一覧を抽出
    all_knowledge_ids = set()
    for c in data["clauses"]:
        all_knowledge_ids.update(c.get("knowledge_id", []))
    all_knowledge_ids = list(all_knowledge_ids)
    print("all_knowledge_ids:")
    print(all_knowledge_ids)

    from collections import defaultdict

    clause_results = defaultdict(list)  # 条項ごとに複数ナレッジの審査結果を格納

    def call_llm_for_review(clauses, knowledge):
        from azure_.openai_service import AzureOpenAIService
        import json

        print("Call: call_llm_for_review")
        service = AzureOpenAIService()
        system_prompt = (
            "あなたは契約審査の専門家です。以下の審査対象データと審査知見をもとに、各条項ごとに懸念点(concern)と修正条文(amendment_clause)を出力してください。\n"
            "懸念点(concern)は、端的な箇条書きで提供してください。\n"
            "修正した条文(amendment_clause)は、要変更箇所を明示し、端的に示してください。\n"
            "審査の根拠とする knowledge_ids を必ず提示し、提供する審査知見以外を利用した審査は絶対にしないでください。\n"
            '審査の結果懸念がない場合は、"concern" および "amendment_clause" を null で出力してください。\n'
            "【出力形式】\n"
            "必ず以下の厳格なJSON配列形式で出力してください。\n"
            "[\n"
            "  {\n"
            '    "clause_number": <条項番号（文字列）>,\n'
            '    "concern": <懸念点コメント> or null,\n'
            '    "amendment_clause": <修正条文> or null,\n'
            '    "knowledge_ids": [<ナレッジIDの配列>]\n'
            "  }, ...\n"
            "]\n"
        )
        prompt = (
            "【審査対象データ】\n"
            f"{json.dumps(clauses, ensure_ascii=False)}\n"
            "【審査知見（knowledge）】\n"
            f"{json.dumps(knowledge, ensure_ascii=False)}\n\n"
            "審査は提供する審査知見以外を絶対に利用しないでください。"
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ]
        try:
            answer = service.get_openai_response_gpt41(messages)
            print("LLM応答:")
        except Exception as e:
            print(f"LLM呼び出しエラー: {e}")
            return [
                {
                    "clause_number": clause["clause_number"],
                    "concern": f"LLMエラー: {e}",
                    "amendment_clause": "",
                    "knowledge_ids": [],
                }
                for clause in clauses
            ]

        def try_parse_json_llm_response(resp, max_retry=2):
            for retry in range(max_retry):
                try:
                    result = json.loads(resp)
                    return result
                except Exception as e:
                    if retry < max_retry - 1:
                        from azure_.openai_service import AzureOpenAIService

                        service = AzureOpenAIService()
                        fix_prompt = (
                            "以下のテキストはJSON配列として不正な形式です。絶対に他のテキストや説明を含めず、厳格なJSON配列のみを出力してください。\n"
                            "【期待するJSON配列の出力例】\n"
                            "[\n"
                            '  {"clause_number": "1", "concern": "懸念点例", "amendment_clause": "修正条文例", "knowledge_ids": ["id1", "id2"]},\n'
                            '  {"clause_number": "2", "concern": "", "amendment_clause": "", "knowledge_ids": []}\n'
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
                        except Exception:
                            break
                    else:
                        break
            return [
                {
                    "clause_number": clause["clause_number"],
                    "concern": f"LLM応答パースエラー: {e}",
                    "amendment_clause": "",
                    "knowledge_ids": [],
                }
                for clause in clauses
            ]

        result = try_parse_json_llm_response(answer, max_retry=2)
        return result

    # knowledge_idごとに該当条項を抽出し、knowledge_allから該当ナレッジを取得して審査
    for kid in all_knowledge_ids:
        # kidに関連する条項のみ抽出
        target_clauses = [
            c for c in data["clauses"] if kid in c.get("knowledge_id", [])
        ]
        # knowledge_allから該当ナレッジを抽出
        target_knowledge = [k for k in knowledge_all if k.get("id") == kid]
        if not target_clauses or not target_knowledge:
            continue
        review_result = call_llm_for_review(target_clauses, target_knowledge)
        for item in review_result:
            clause_results[item["clause_number"]].append(item)

    # 条項ごとに複数ナレッジの指摘事項があれば要約
    summarized_clauses = []

    def call_llm_for_summary(clause_number, concerns, amendments):
        from azure_.openai_service import AzureOpenAIService
        import json

        print("Call: call_llm_for_summary")
        service = AzureOpenAIService()
        system_prompt = (
            "あなたは契約審査の専門家です。以下の複数の指摘事項・修正条項案を統合し、重複や類似内容をまとめて簡潔にしてください。\n"
            "【出力形式】\n"
            '{"concern": <要約した懸念点>, "amendment_clause": <統合した修正条項案>}'
        )
        prompt = (
            f"【条項番号】{clause_number}\n"
            f"【指摘事項一覧】{json.dumps(concerns, ensure_ascii=False)}\n"
            f"【修正文案一覧】{json.dumps(amendments, ensure_ascii=False)}\n"
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ]
        try:
            answer = service.get_openai_response_gpt41(messages)
            result = json.loads(answer)
            return result.get("concern", ""), result.get("amendment_clause", "")
        except Exception as e:
            return "要約エラー: " + str(e), ""

    for clause in data["clauses"]:
        num = clause["clause_number"]
        results = clause_results.get(num, [])
        if not results:
            summarized_clauses.append(
                {
                    "clause_number": num,
                    "concern": "",
                    "amendment_clause": "",
                    "knowledge_ids": [],
                }
            )
            continue
        concerns = [r["concern"] for r in results if r["concern"]]
        amendments = [r["amendment_clause"] for r in results if r["amendment_clause"]]
        knowledge_ids = []
        for r in results:
            knowledge_ids.extend(r.get("knowledge_ids", []))
        # 複数指摘があれば要約
        if len(concerns) > 1 or len(amendments) > 1:
            concern_summary, amendment_summary = call_llm_for_summary(
                num, concerns, amendments
            )
        else:
            concern_summary = concerns[0] if concerns else ""
            amendment_summary = amendments[0] if amendments else ""
        summarized_clauses.append(
            {
                "clause_number": num,
                "concern": concern_summary,
                "amendment_clause": amendment_summary,
                "knowledge_ids": list(set(knowledge_ids)),
            }
        )

    with open(sample_path, "w", encoding="utf-8") as f:
        f.write("Examination_data = ")
        json.dump(data, f, ensure_ascii=False, indent=4)
        f.write("\n")
        f.write("knowledge_all = ")
        json.dump(knowledge_all, f, ensure_ascii=False, indent=4)
        f.write("\n")
        f.write("similar_clauses_knowledge = ")
        json.dump(similar_clauses_knowledge, f, ensure_ascii=False, indent=4)
        f.write("\n")
        f.write("Analyzed_clauses = ")
        json.dump(summarized_clauses, f, ensure_ascii=False, indent=4)
        f.write("\n")

    return summarized_clauses


def search_similar_clauses(clauses, contract_api):
    similar_clauses_knowledge = []
    for clause in clauses:
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

def setting_clause_and_knowledge(knowledge_all: list, clauses: list):
    """
    - knowledge_all には審査対象となりうる条文の条件が記載されている: knowledge_all[i]["target_clause"]
    - Step1: target_clause の条件に合致する clause_number を clauses から特定する。出力: response
    - Step2: clauses に対応する knowledge_id を追加する。
    - 考慮すべき点･･･これらの処理使った後工程の処理内容:
        - 各clauseの審査において、割り振られた knowledge_id を審査知見として利用して審査する。審査知見がない条項は審査しない。
        - どの条項にも割り当てのない審査知見がある場合は、全ての条項に対して審査する。対応する条項がごっそり抜けている場合を想定。
        - １つの審査知見が複数の条項にまたがる場合は、関係する条項を結合して一度に審査する。
        - １つの条項で複数の審査知見が関係する場合は、各知見を個別に審査する。同じLLM処理に複数の観点が入って処理負荷がかかるのを避ける。
    - response の出力形式例:
    response = [
    {"knowledge_id": "362d7a0d-5c29-4349-be4c-58182eecd502", "clause_number": [1]}, # knowledge_id に対して対応する clause_number を割り当てる
    {"knowledge_id": "845620fe-faf4-4116-ab09-93807d396a87", "clause_number": [1, 2, 3]}, # 複数の clause_number に対応する場合
    {"knowledge_id": "acd057ae-036b-45fe-9f67-9145774cad8c", "clause_number": []} # 審査対象の条文がない場合: 条文が特定できなかったので、Step2では全ての条文に対して追加する
    ]
    - Step2の出力形式例:
    clauses= [{
            "clause_id": "",
            "clause_number": "1",
            "clause": "第1条\n（秘密情報）\n本契約において｢秘密情報｣とは、本契約締結の事実及び内容、本契約に基づき秘密情報を開示する当事者（以下「開示者」という。）が秘密情報を受領する当事者（以下「受領者」という。）に開示した技術情報、並びに本業務の過程で知り得た他の当事者の業務上及び技術上の情報のうち、次の各号に該当するものをいう。\n（1）書面、図面、電子媒体及びその他有形物によって開示された情報。\n（2）電子メール等の電気通信手段により開示された情報。\n（3）口頭又は視覚的手段によって開示された情報であって、開示の際に秘密である旨を表明たもの。\n（4）本業務のために開示者が受領者に提供した物品及び本業務のために製作した物品、並びに、本業務のために行った試験等により得られた情報。\n（5）その他、各当事者が別途協議の上、秘密である旨を書面により確認した情報。\n2．前項の定めにかかわらず、次の各号の一に該当することを立証できる場合、受領者は秘密保持義務を負わない。\n（1）開示された際、既に自ら所有していたもの。\n（2）開示された際、既に公知又は公用であったもの。\n（3）開示された後、自己の責によらず公知又は公用となったもの。\n（4）正当な権原を有する第三者から合法的に入手したもの。\n（5）開示された秘密情報に拠らず、独自に開発したもの。\n3．第1項の定めにかかわらず、受領者は、国、地方公共団体、上場している金融商品取引所その他これらに準ずる公的機関から、法令（規則、命令、決定、裁判等を含む。）に基づき秘密情報の開示を請求された場合は、必要な範囲で、秘密情報を開示することができる。但し、受領者は、当該開示に先立ち、当該開示を請求した者に対して、開示する情報が秘密保持義務を課されたものであることを説明し、開示される秘密情報の範囲を必要最小限度とし、かつ、本契約上の秘密保持義務と同等以上の秘密保持義務を課すよう最大限努力するとともに、開示の事実及び開示対象の秘密情報を開示者に書面にて通知しなければならない。なお、緊急時等開示前の通知が困難な場合には、開示後速やかに通知するものとする。",
            "knowledge_id": ["362d7a0d-5c29-4349-be4c-58182eecd502", "845620fe-faf4-4116-ab09-93807d396a87", "acd057ae-036b-45fe-9f67-9145774cad8c"],
        },{
            "clause_id": "",
            "clause_number": "2",
            "clause": "第2条\n（秘密情報の取扱い）\n　　受領者は、開示者から開示された秘密情報の取扱いについて次の各号に定める事項を遵守する。\n（1）秘密情報を管理する管理責任者を定め、管理責任者を通じて、秘密情報を含む媒体（書面、図面、電子媒体及びその他有形物を含むが、これらに限定されない。以下同じ。）を施錠できる保管庫に保管し、秘密情報を含む電子データへのアクセス権を制限するなど、秘密情報を厳重に保管する。\n2．受領者は、開示者から事前に書面による承諾を得ない限り、秘密情報を第三者に開示してはならない。\n3．秘密情報が漏洩した場合又はそのおそれがある場合、受領者は開示者にその旨を報告し、秘密情報の拡散防止のために必要な措置を講じなければならない。",
            "knowledge_id": ["845620fe-faf4-4116-ab09-93807d396a87", "acd057ae-036b-45fe-9f67-9145774cad8c"]
        },{
            "clause_id": "",
            "clause_number": "3",
            "clause": "第3条\n（知的財産権）\n本業務の過程で、開示された秘密情報に基づき受領者の従業員等が発明、考案、意匠の創作、回路配置の創作（以下｢発明等｣という。）をなした場合は、速やかに開示者に通知し、当該発明等について知的財産権を受ける権利の帰属と当該発明等の取扱いを、当事者間で協議して決定する。",
            "knowledge_id": ["acd057ae-036b-45fe-9f67-9145774cad8c"]
        }]

    - 引数のデータサンプル
    knowledge_all = [{
        "id": "362d7a0d-5c29-4349-be4c-58182eecd502", # knowledge_id に相当する
        "target_clause": "契約書の前文と目的を記載する条項が前文から分離する場合は目的条項を含む",
        "knowledge_title": "前文・目的条項の明確性",
        "review_points": "- 前文で契約の目的をわかりやすく記載し、複雑な場合は目的条項を独立させる\n- 受領当事者の要求を満たすために、秘密情報の開示・使用範囲が目的定義の範囲内に入っているか確認する",
        "action_plan": "- 目的の表現が曖昧でないか、関係者が一目で理解できるかを確認する\n- 必要に応じて範囲を拡大または調整し、当初想定した利用目的が達成できるように修正する",
        "clause_sample": "武蔵精密工業株式会社（以下「甲」という。）とエリーパワー株式会社（以下「乙」という。）は、ハイブリッドバッテリの開発（以下「本業務」という。）を目的として、 互いに開示する情報の秘密保持に関し、以下の通り定める。 "
    },{
        "id": "845620fe-faf4-4116-ab09-93807d396a87",
        "target_clause": "秘密情報の定義が記載された条項",
        "knowledge_title": "秘密情報の特定方法と表示義務",
        "review_points": "秘密情報の特定方法と表示義務が妥当であるか",
        "action_plan": "- 書面・図面等の有形情報には「秘密」「Confidential」等を明示的に表示する。\n- 口頭や映像など無体物による開示時には開示時の表明および開示後30日以内の書面化を必須とする。",
        "clause_sample": "第１条（秘密情報） \n本契約において｢秘密情報｣とは、本契約締結の事実及び内容、本契約に基づき秘密情報を開示する当事者（以下「開示者」という。）が秘密情報を受領する当事者（以下「受領者」という。）に開示した技術情報、並びに本業務の過程で知り得た他の当事者の業務上及び技術上の情報のうち、次の各号に該当するものをいう。 \n（１）書面、図面、電子媒体及びその他有形物による開示であって、当該書面又は媒体上に秘密である旨の表示をなしたもの。 \n（２）電子メール等の電気通信手段により開示された情報であって、当該情報に秘密である旨の表示をなしたもの。 \n（３）口頭又は視覚的手段によって開示された情報であって、開示の際に秘密である旨を表明し、かつ、開示の日より３０日以内に当該情報の概要及び当該情報が秘密である旨を明示した書面が提供されたもの。 \n（４）本業務のために開示者が受領者に提供した物品及び本業務のために製作した物品で当該各物品が秘密である旨を明示した書面が提供された物品、並びに、本業務のために行った試験等により得られた情報で当該情報が秘密である旨を明示した書面が提供された情報。 \n（５）その他、各当事者が別途協議の上、秘密である旨を書面により確認した情報。 "
    },{
        "id": "acd057ae-036b-45fe-9f67-9145774cad8c",
        "target_clause": "条件を定めて情報開示義務を負うことが記載された条項",
        "knowledge_title": "情報開示義務の要否",
        "review_points": "- 秘密保持契約に情報開示義務を課すか否かを検討\n- 開示拒否の合理性と協議プロセス",
        "action_plan": "- 秘密保持契約に情報開示義務を課すか否かを検討し、いずれの場合も条文で明確化する。義務を負わせない場合の受領当事者の期待不足リスクや、義務を負わせる場合の開示過剰リスクを当事者間で事前に共有・確認する。\n- 開示当事者が情報開示を拒否する場合の合理的判断基準を条文で定め、受領当事者が合理性を疑うときは別途協議するプロセスを規定する。",
        "clause_sample": ""
    },]
    clauses= [{
            "clause_id": "",
            "clause_number": "1",
            "clause": "第1条\n（秘密情報）\n本契約において｢秘密情報｣とは、本契約締結の事実及び内容、本契約に基づき秘密情報を開示する当事者（以下「開示者」という。）が秘密情報を受領する当事者（以下「受領者」という。）に開示した技術情報、並びに本業務の過程で知り得た他の当事者の業務上及び技術上の情報のうち、次の各号に該当するものをいう。\n（1）書面、図面、電子媒体及びその他有形物によって開示された情報。\n（2）電子メール等の電気通信手段により開示された情報。\n（3）口頭又は視覚的手段によって開示された情報であって、開示の際に秘密である旨を表明たもの。\n（4）本業務のために開示者が受領者に提供した物品及び本業務のために製作した物品、並びに、本業務のために行った試験等により得られた情報。\n（5）その他、各当事者が別途協議の上、秘密である旨を書面により確認した情報。\n2．前項の定めにかかわらず、次の各号の一に該当することを立証できる場合、受領者は秘密保持義務を負わない。\n（1）開示された際、既に自ら所有していたもの。\n（2）開示された際、既に公知又は公用であったもの。\n（3）開示された後、自己の責によらず公知又は公用となったもの。\n（4）正当な権原を有する第三者から合法的に入手したもの。\n（5）開示された秘密情報に拠らず、独自に開発したもの。\n3．第1項の定めにかかわらず、受領者は、国、地方公共団体、上場している金融商品取引所その他これらに準ずる公的機関から、法令（規則、命令、決定、裁判等を含む。）に基づき秘密情報の開示を請求された場合は、必要な範囲で、秘密情報を開示することができる。但し、受領者は、当該開示に先立ち、当該開示を請求した者に対して、開示する情報が秘密保持義務を課されたものであることを説明し、開示される秘密情報の範囲を必要最小限度とし、かつ、本契約上の秘密保持義務と同等以上の秘密保持義務を課すよう最大限努力するとともに、開示の事実及び開示対象の秘密情報を開示者に書面にて通知しなければならない。なお、緊急時等開示前の通知が困難な場合には、開示後速やかに通知するものとする。",
        },{
            "clause_id": "",
            "clause_number": "2",
            "clause": "第2条\n（秘密情報の取扱い）\n　　受領者は、開示者から開示された秘密情報の取扱いについて次の各号に定める事項を遵守する。\n（1）秘密情報を管理する管理責任者を定め、管理責任者を通じて、秘密情報を含む媒体（書面、図面、電子媒体及びその他有形物を含むが、これらに限定されない。以下同じ。）を施錠できる保管庫に保管し、秘密情報を含む電子データへのアクセス権を制限するなど、秘密情報を厳重に保管する。\n2．受領者は、開示者から事前に書面による承諾を得ない限り、秘密情報を第三者に開示してはならない。\n3．秘密情報が漏洩した場合又はそのおそれがある場合、受領者は開示者にその旨を報告し、秘密情報の拡散防止のために必要な措置を講じなければならない。",
        },{
            "clause_id": "",
            "clause_number": "3",
            "clause": "第3条\n（知的財産権）\n本業務の過程で、開示された秘密情報に基づき受領者の従業員等が発明、考案、意匠の創作、回路配置の創作（以下｢発明等｣という。）をなした場合は、速やかに開示者に通知し、当該発明等について知的財産権を受ける権利の帰属と当該発明等の取扱いを、当事者間で協議して決定する。",
        }]

    LLMの呼び出し方法例
    ```
    from azure_.openai_service import AzureOpenAIService
    service = AzureOpenAIService()
    messages = [(適切に記載)]
    answer = service.get_openai_response_gpt41(messages)
    ```
    """
    print("START: setting_clause_and_knowledge")


def examination_api(
    contract_type: str,
    background_info: str,
    partys: list,
    introduction: str,
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
        introduction (str): 前文
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
        "introduction": introduction,
        "title": title,
        "clauses": [
            {
                "clause_id": c.get("clause_id", ""),
                "clause_number": c.get("clause_number", ""),
                "clause": c.get("clause", ""),
                "contents_type": "clauses",
                # "review_points": c.get("review_points", ""),
                # "action_plan": c.get("action_plan", ""),
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
    # いったんキャンセルするがコメントアウトは消すな！
    # similar_clauses_knowledge = search_similar_clauses(data["clauses"], contract_api)

    def chunk_list(lst, n):
        for i in range(0, len(lst), n):
            yield lst[i : i + n]

    cluster_size = 2
    knowledge_clusters = list(chunk_list(knowledge_all, cluster_size))

    def call_llm_for_review(data, knowledge_cluster):
        from azure_.openai_service import AzureOpenAIService
        import json

        service = AzureOpenAIService()
        system_prompt = (
            "あなたは契約審査の専門家です。以下の審査対象データと審査知見をもとに、各条項ごとに懸念点(concern)と提供する 'clause_sample' を参考に修正した条文(amendment_clause)を出力してください。\n"
            "懸念点(concern)は、端的な箇条書きで提供してください。\n"
            "修正した条文(amendment_clause)は、要変更箇所を明示し、端的に示してください。\n"
            "審査の根拠とする knowledge_ids を必ず提示し、提供する審査知見以外を利用した審査は絶対にしないでください。\n"
            '審査の結果懸念がない場合は、"concern" および "amendment_clause" を null で出力してください。\n'
            "根拠とする knowledge_ids を必ず提示し、提供する審査知見以外を利用した審査は絶対にしないでください。\n"
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
            f"{json.dumps(data, ensure_ascii=False)}\n"
            "【審査知見（knowledge_allクラスタ）】\n"
            f"{json.dumps(knowledge_cluster, ensure_ascii=False)}\n\n"
            "審査は提供する審査知見以外を絶対に利用しないでください。"
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ]
        try:
            answer = service.get_openai_response_gpt41(messages)
        except Exception as e:
            return [
                {
                    "clause_number": clause["clause_number"],
                    "concern": f"LLMエラー: {e}",
                    "amendment_clause": "",
                    "knowledge_ids": [],
                }
                for clause in data["clauses"]
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
                for clause in data["clauses"]
            ]

        result = try_parse_json_llm_response(answer, max_retry=2)
        return result

    cluster_results = []
    try:
        for cluster in knowledge_clusters:
            review_result = call_llm_for_review(data, cluster)
            cluster_results.append(review_result)
    except Exception as e:
        print(f"Error call_llm_for_review: {e}")

    from collections import defaultdict

    merged = defaultdict(
        lambda: {"concern": [], "amendment_clause": [], "knowledge_ids": []}
    )
    try:
        for cluster in cluster_results:
            for item in cluster:
                num = item["clause_number"]
                if item["concern"]:
                    merged[num]["concern"].append(item["concern"])
                if item["amendment_clause"]:
                    merged[num]["amendment_clause"].append(item["amendment_clause"])
                merged[num]["knowledge_ids"].extend(item["knowledge_ids"])
    except Exception as e:
        print(f"Error occurred: {e}")

    analyzed_clauses = []

    def flatten(l):
        return [
            item
            for sublist in l
            for item in (sublist if isinstance(sublist, list) else [sublist])
        ]

    for clause in data["clauses"]:
        num = clause["clause_number"]
        try:
            flat_concern = flatten(merged[num]["concern"])
            flat_amendment = flatten(merged[num]["amendment_clause"])
            analyzed_clauses.append(
                {
                    "clause_number": num,
                    "concern": "\n".join(flat_concern),
                    "amendment_clause": "\n".join(flat_amendment),
                    "knowledge_ids": list(set(merged[num]["knowledge_ids"])),
                }
            )
        except Exception as e:
            print(f"Error at clause_number {num}: {e}")

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
        json.dump(analyzed_clauses, f, ensure_ascii=False, indent=4)
        f.write("\n")

    return analyzed_clauses


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

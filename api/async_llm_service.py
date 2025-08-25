import asyncio
import json
from typing import Sequence, Any, Dict, List
from azure_.openai_service import AzureOpenAIService

# プロセス内で再利用する共有リソース
_sem = asyncio.Semaphore(8)  # Azure のデプロイのTPS/TPMに合わせて調整
_service = AzureOpenAIService()


async def ainvoke_with_limit(
    messages: List[Dict[str, str]], max_retries: int = 2
) -> str:
    """
    セマフォとバックオフ付きの非同期LLM呼び出し
    """
    delay = 0.5
    async with _sem:
        for attempt in range(max_retries):
            try:
                return _service.get_openai_response_gpt41(messages)
            except Exception as e:
                msg = str(e).lower()
                if attempt < max_retries - 1 and (
                    "429" in msg or "timeout" in msg or "temporarily" in msg
                ):
                    await asyncio.sleep(delay)
                    delay = min(delay * 2, 8)
                else:
                    raise


async def run_batch_reviews(reviews: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    複数の条項審査を並列実行
    reviews: [{"clauses": [...], "knowledge": [...]}]の形式
    """

    async def review_one(item: Dict[str, Any]) -> List[Dict[str, Any]]:
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
            f"{json.dumps(item['clauses'], ensure_ascii=False)}\n"
            "【審査知見（knowledge）】\n"
            f"{json.dumps(item['knowledge'], ensure_ascii=False)}\n\n"
            "審査は提供する審査知見以外を絶対に利用しないでください。"
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ]

        try:
            result = await ainvoke_with_limit(messages)
            return json.loads(result)
        except Exception as e:
            return [
                {
                    "clause_number": clause["clause_number"],
                    "concern": f"LLMエラー: {e}",
                    "amendment_clause": "",
                    "knowledge_ids": [],
                }
                for clause in item["clauses"]
            ]

    tasks = [review_one(item) for item in reviews]
    return await asyncio.gather(*tasks)


async def run_batch_summaries(summaries: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """
    複数の要約処理を並列実行
    summaries: [{"clause_number": "...", "concerns": [...], "amendments": [...]}]の形式
    """

    async def summarize_one(item: Dict[str, Any]) -> Dict[str, str]:
        system_prompt = (
            "あなたは契約審査の専門家です。以下の複数の指摘事項・修正条項案を統合し、重複や類似内容をまとめて簡潔にしてください。\n"
            "【出力形式】\n"
            '{"concern": <要約した懸念点>, "amendment_clause": <統合した修正条項案>}'
        )

        prompt = (
            f"【条項番号】{item['clause_number']}\n"
            f"【指摘事項一覧】{json.dumps(item['concerns'], ensure_ascii=False)}\n"
            f"【修正文案一覧】{json.dumps(item['amendments'], ensure_ascii=False)}\n"
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ]

        try:
            result = await ainvoke_with_limit(messages)
            parsed = json.loads(result)
            return {
                "concern": parsed.get("concern", ""),
                "amendment_clause": parsed.get("amendment_clause", ""),
            }
        except Exception as e:
            return {"concern": "要約エラー: " + str(e), "amendment_clause": ""}

    tasks = [summarize_one(item) for item in summaries]
    return await asyncio.gather(*tasks)

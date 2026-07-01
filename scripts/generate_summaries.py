#!/usr/bin/env python3
"""data/qas.json を読み込み Gemini API でテーマ別まとめを生成して
data/summaries.json に保存する。月次で GitHub Actions から実行される。

環境変数:
    GEMINI_API_KEY: Google AI Studio で取得した API キー
"""
import json
import os
import sys
import urllib.request
from pathlib import Path

DATA_FILE = Path(__file__).parent.parent / "data" / "qas.json"
SUMMARIES_FILE = Path(__file__).parent.parent / "data" / "summaries.json"

GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-1.5-flash:generateContent?key={api_key}"
)

SAMPLE_SIZE = 1500

PROMPT = """\
あなたは公認会計士試験の受験生・合格者向けQ&Aアーカイブを整理するアシスタントです。

以下は現役公認会計士（訳アリさん）への質問箱に寄せられたQ&Aデータです。
このデータを分析し、会計士受験生・合格者が関心を持つテーマを10〜15個抽出して、
各テーマについて「訳アリさんの回答を総合した要約」を作成してください。

【出力要件】
- テーマ名: 受験生目線で知りたい内容を表す日本語（15文字以内）
- 要約: 訳アリさんがそのテーマについて語っている内容を400〜600文字で具体的にまとめる
- JSON配列のみ返答（前後に説明文・コードブロック記号は不要）

【出力フォーマット】
[
  {{"topic": "テーマ名", "summary": "要約文", "question_count": 件数}},
  ...
]

【Q&Aデータ】
{qa_data}
"""


def call_gemini(api_key: str, prompt: str) -> str:
    url = GEMINI_URL.format(api_key=api_key)
    body = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.3, "maxOutputTokens": 8192},
    }).encode("utf-8")
    req = urllib.request.Request(
        url, data=body,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        result = json.load(resp)
    return result["candidates"][0]["content"]["parts"][0]["text"]


def extract_json(text: str) -> list:
    start = text.find("[")
    end = text.rfind("]") + 1
    if start == -1 or end == 0:
        raise ValueError(f"JSONが見つかりませんでした:\n{text[:300]}")
    return json.loads(text[start:end])


def main():
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        print("エラー: 環境変数 GEMINI_API_KEY が設定されていません", file=sys.stderr)
        sys.exit(1)

    qas = json.loads(DATA_FILE.read_text("utf-8"))
    sample = qas[:SAMPLE_SIZE]
    qa_data = json.dumps(
        [{"q": x["question"], "a": x["answer"]} for x in sample],
        ensure_ascii=False,
    )

    print(f"Gemini API にリクエスト中... ({len(sample)}件送信)")
    raw = call_gemini(api_key, PROMPT.format(qa_data=qa_data))
    summaries = extract_json(raw)

    SUMMARIES_FILE.write_text(
        json.dumps(summaries, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"完了: {len(summaries)}テーマ → {SUMMARIES_FILE}")


if __name__ == "__main__":
    main()

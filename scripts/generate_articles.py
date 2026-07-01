#!/usr/bin/env python3
"""テーマに関連するQ&A全件をClaude APIに渡し、note風の記事を生成する。

Usage:
    ANTHROPIC_API_KEY=sk-ant-xxx python3 scripts/generate_articles.py
    ANTHROPIC_API_KEY=sk-ant-xxx python3 scripts/generate_articles.py --theme 監査法人の選び方
"""
import argparse
import json
import os
import sys
import time
import urllib.request
import urllib.error
from collections import defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent
QAS_FILE = ROOT / "data" / "qas.json"
ARTICLES_FILE = ROOT / "data" / "articles.json"
QUERIE_ANSWER_URL = "https://querie.me/answer/{id}"

API_URL = "https://api.anthropic.com/v1/messages"
MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 4096

# ── テーマとキーワード ──────────────────────────────────────────
TOPICS = [
    ("監査法人の選び方", [
        "法人選び", "big4", "大手", "中小", "準大手", "トーマツ", "あずさ",
        "新日本", "pwc", "ey", "deloitte", "kpmg", "法人の違い", "どこがいい",
        "入所", "就職先", "法人ごと",
    ]),
    ("給与・ボーナス", [
        "給与", "給料", "年収", "ボーナス", "賞与", "手取り", "昇給", "報酬",
        "いくら", "稼げる", "収入", "月給", "基本給",
    ]),
    ("就活・面接対策", [
        "就活", "就職活動", "面接", "エントリー", "志望動機", "インターン",
        "選考", "内定", "リクルーター", "合同説明会", "受験生", "面談",
    ]),
    ("試験勉強・学習法", [
        "勉強", "学習", "テキスト", "答練", "模試", "cpa", "tac", "大原",
        "短答", "論文", "合格", "勉強時間", "スケジュール", "暗記", "科目",
    ]),
    ("監査の仕事内容", [
        "監査", "クライアント", "往査", "調書", "レビュー", "マネージャー",
        "スタッフ", "シニア", "インチャージ", "監査手続", "仕事内容",
    ]),
    ("キャリア・転職", [
        "転職", "キャリア", "独立", "事業会社", "cfo", "コンサル", "fas",
        "出向", "ipo", "スタートアップ", "将来", "キャリアパス", "退職",
    ]),
    ("ワークライフバランス", [
        "残業", "忙しい", "繁忙期", "有給", "休暇", "休み", "プライベート",
        "働き方", "リモート", "テレワーク", "在宅", "激務",
    ]),
    ("会計・税務の知識", [
        "会計", "税務", "ifrs", "j-gaap", "連結", "開示", "税効果", "減損",
        "のれん", "公認会計士", "税理士", "簿記", "財務諸表", "経理",
    ]),
    ("人間関係・職場環境", [
        "上司", "同僚", "先輩", "後輩", "パートナー", "人間関係", "職場",
        "チーム", "雰囲気", "文化", "コミュニケーション",
    ]),
    ("お金・資産形成", [
        "投資", "株", "資産", "節税", "貯金", "nisa", "ideco",
        "不動産", "副業", "運用", "資産形成",
    ]),
    ("プライベート・趣味", [
        "趣味", "旅行", "恋愛", "結婚", "友達", "遊び", "スポーツ",
        "ゲーム", "読書", "映画", "音楽",
    ]),
    ("試験合格後の生活", [
        "合格後", "登録", "修了考査", "補習所", "合格してから", "会計士になって",
    ]),
]

PROMPT_TEMPLATE = """\
あなたは公認会計士（訳アリさん、公認会計士試験合格者）の経験・知識をまとめるライターです。

以下は「{topic}」というテーマに関連した、訳アリさんへの質問と訳アリさんの回答、計{count}件のデータです。
これらの内容をもとに、公認会計士試験の受験生や監査法人への就職を目指す方向けに、
充実した読み物記事を日本語で作成してください。

【記事作成の要件】
- Q&Aの文章を直接コピー・引用しない（情報・知識・視点を自分の言葉で統合・再構成する）
- 訳アリさんの率直な視点・具体的な数字・実体験に基づいたエピソードを積極的に活用する
- 1500〜2500文字程度の充実した内容にする
- 「はじめに」「本文（複数の小見出しで構成）」「まとめ」の流れで構成する
- 小見出しには ## を使用する
- 各小見出しセクションの末尾に、そのセクションで参考にしたQ&AのIDを
  以下の形式でリスト化する（IDのみ、1セクションあたり最大5件）：
  [参照Q&A]: id1, id2, id3

【Q&Aデータ】
{qa_data}
"""


def classify_qas(qas: list) -> dict:
    buckets = defaultdict(list)
    for qa in qas:
        text = ((qa.get("question") or "") + " " + (qa.get("answer") or "")).lower()
        best, best_score = None, 0
        for name, keywords in TOPICS:
            s = sum(1 for kw in keywords if kw.lower() in text)
            if s > best_score:
                best_score, best = s, name
        if best and best_score >= 1:
            buckets[best].append(qa)
    return buckets


def format_qa_for_prompt(qa: dict) -> str:
    q = (qa.get("question") or "").strip()
    a = (qa.get("answer") or "").strip()
    return f"[ID: {qa['id']}]\nQ: {q}\nA: {a}"


def call_claude(api_key: str, prompt: str) -> str:
    body = json.dumps({
        "model": MODEL,
        "max_tokens": MAX_TOKENS,
        "messages": [{"role": "user", "content": prompt}],
    }).encode("utf-8")
    req = urllib.request.Request(
        API_URL, data=body,
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=300) as resp:
        result = json.load(resp)
    return result["content"][0]["text"]


def extract_references(article_text: str, qas_by_id: dict) -> list:
    """記事内の [参照Q&A]: id1, id2, ... を解析してリストを返す。"""
    import re
    refs = []
    seen = set()
    for match in re.finditer(r'\[参照Q&A\]:\s*([^\n]+)', article_text):
        ids = [i.strip() for i in match.group(1).split(',')]
        for qid in ids:
            if qid and qid not in seen and qid in qas_by_id:
                qa = qas_by_id[qid]
                q_preview = (qa.get("question") or "")[:50].replace("\n", " ")
                refs.append({
                    "id": qid,
                    "question_preview": q_preview,
                    "url": QUERIE_ANSWER_URL.format(id=qid),
                })
                seen.add(qid)
    return refs


def generate_for_theme(api_key: str, topic: str, items: list, qas_by_id: dict) -> dict:
    print(f"  生成中: {topic}（{len(items)}件のQ&A）")

    qa_data = "\n\n---\n\n".join(format_qa_for_prompt(qa) for qa in items)
    prompt = PROMPT_TEMPLATE.format(
        topic=topic,
        count=len(items),
        qa_data=qa_data,
    )

    article_text = call_claude(api_key, prompt)
    references = extract_references(article_text, qas_by_id)

    return {
        "topic": topic,
        "question_count": len(items),
        "article": article_text,
        "references": references,
        "generated_at": datetime.now().strftime("%Y-%m-%d"),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--theme", help="特定のテーマのみ生成（省略時は全テーマ）")
    args = parser.parse_args()

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("エラー: 環境変数 ANTHROPIC_API_KEY が設定されていません", file=sys.stderr)
        sys.exit(1)

    qas = json.loads(QAS_FILE.read_text("utf-8"))
    qas_by_id = {q["id"]: q for q in qas}
    buckets = classify_qas(qas)

    print(f"Q&A読み込み: {len(qas)}件 / {len(buckets)}テーマに分類")

    # 既存の記事を読み込み（追記モード）
    existing = {}
    if ARTICLES_FILE.exists():
        for a in json.loads(ARTICLES_FILE.read_text("utf-8")):
            existing[a["topic"]] = a

    target_topics = [(name, kws) for name, kws in TOPICS if not args.theme or name == args.theme]
    if args.theme and not any(name == args.theme for name, _ in target_topics):
        print(f"エラー: テーマ '{args.theme}' が見つかりません", file=sys.stderr)
        sys.exit(1)

    results = dict(existing)
    for i, (topic, _) in enumerate(target_topics):
        items = buckets.get(topic, [])
        if not items:
            print(f"  スキップ: {topic}（Q&Aなし）")
            continue

        try:
            article = generate_for_theme(api_key, topic, items, qas_by_id)
            results[topic] = article
            print(f"  完了: {topic} → {len(article['references'])}件の参照")

            # 途中経過を保存（途中でエラーになっても失わない）
            ARTICLES_FILE.write_text(
                json.dumps(list(results.values()), ensure_ascii=False, indent=2),
                encoding="utf-8"
            )

            # レート制限対策（最後のテーマは不要）
            if i < len(target_topics) - 1:
                time.sleep(3)

        except Exception as e:
            print(f"  エラー: {topic} → {e}")
            continue

    print(f"\n完了: {len(results)}記事を {ARTICLES_FILE} に保存")


if __name__ == "__main__":
    main()

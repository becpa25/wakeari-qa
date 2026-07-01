#!/usr/bin/env python3
"""data/qas.json を読み込みテーマ別まとめを生成して data/summaries.json に保存する。

動作モード:
  - 環境変数 GEMINI_API_KEY が設定されていれば Gemini API でLLM要約を生成。
  - 未設定 or Gemini が失敗した場合はキーワードベースの分類に自動フォールバック。
"""
import json
import os
import time
import urllib.error
import urllib.request
from collections import defaultdict
from pathlib import Path

DATA_FILE = Path(__file__).parent.parent / "data" / "qas.json"
SUMMARIES_FILE = Path(__file__).parent.parent / "data" / "summaries.json"

# ── API 設定 ──────────────────────────────────────────────────
GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-2.0-flash:generateContent?key={api_key}"
)
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"
QA_PER_THEME = 3   # テーマごとに送るQ&A件数

PROMPT_HEADER = """\
あなたは公認会計士（訳アリさん）の質問箱アーカイブを整理するアシスタントです。

以下に、各テーマに関連する実際のQ&Aを提示します。
各テーマについて、訳アリさんの回答を総合した要約文を作成してください。

【出力要件】
- 要約文は400〜700文字で、訳アリさんの言葉・視点を活かして具体的に
- 数字・固有名詞・具体的なアドバイスを積極的に入れる
- JSON配列のみ返答（説明文・コードブロック不要）

[{{"topic": "テーマ名", "summary": "要約文", "question_count": 件数}}, ...]

【各テーマのQ&Aデータ】
{theme_data}
"""


# ── キーワードベース設定 ────────────────────────────────────────
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


# ── テーマ別Q&Aサンプリング ────────────────────────────────────
def build_theme_buckets(qas: list) -> dict:
    buckets: dict[str, list] = defaultdict(list)
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


def pick_representatives(items: list, n: int) -> list:
    liked = [q for q in items if q.get("liked")]
    by_length = sorted(items, key=lambda x: len(x.get("answer") or ""), reverse=True)
    seen, result = set(), []
    for qa in (liked + by_length):
        if qa["id"] not in seen and len(result) < n:
            if len((qa.get("answer") or "").strip()) >= 20:
                result.append(qa)
                seen.add(qa["id"])
    return result


# ── Groq 呼び出し ──────────────────────────────────────────────
def call_groq(api_key: str, buckets: dict) -> list:
    # テーマごとのQ&Aをテキストにまとめる
    theme_sections = []
    for name, _ in TOPICS:
        items = buckets.get(name, [])
        if not items:
            continue
        reps = pick_representatives(items, QA_PER_THEME)
        lines = [f"▼ テーマ: {name}（全{len(items)}件）"]
        for i, qa in enumerate(reps, 1):
            q = (qa.get("question") or "").replace("\n", " ")[:70]
            a = (qa.get("answer") or "").replace("\n", " ")[:100]
            lines.append(f"Q{i}: {q}")
            lines.append(f"A{i}: {a}")
        theme_sections.append("\n".join(lines))

    theme_data = "\n\n".join(theme_sections)
    prompt = PROMPT_HEADER.format(theme_data=theme_data)

    body = json.dumps({
        "model": GROQ_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 5000,
        "temperature": 0.3,
    }).encode("utf-8")
    req = urllib.request.Request(
        GROQ_URL, data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "groq-python/0.11.0",
        },
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        result = json.load(resp)
    raw = result["choices"][0]["message"]["content"]
    start, end = raw.find("["), raw.rfind("]") + 1
    parsed = json.loads(raw[start:end])
    # question_count をバケット情報で補完
    count_map = {name: len(items) for name, items in buckets.items()}
    for s in parsed:
        if not s.get("question_count"):
            s["question_count"] = count_map.get(s.get("topic", ""), 0)
    return parsed


# ── Gemini 呼び出し ────────────────────────────────────────────
def call_gemini(api_key: str, qas: list) -> list:
    qa_data = json.dumps(
        [{"q": x["question"], "a": x["answer"]} for x in qas[:SAMPLE_SIZE]],
        ensure_ascii=False,
    )
    prompt = PROMPT.format(qa_data=qa_data)
    url = GEMINI_URL.format(api_key=api_key)
    body = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.3, "maxOutputTokens": 8192},
    }).encode("utf-8")

    for attempt in range(3):
        try:
            req = urllib.request.Request(
                url, data=body,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=120) as resp:
                result = json.load(resp)
            raw = result["candidates"][0]["content"]["parts"][0]["text"]
            start, end = raw.find("["), raw.rfind("]") + 1
            return json.loads(raw[start:end])
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < 2:
                wait = 65 * (attempt + 1)
                print(f"  レート制限。{wait}秒後リトライ ({attempt + 1}/3)...")
                time.sleep(wait)
            else:
                raise
    return []


# ── キーワードベース分類（LLM不使用フォールバック）─────────────
def keyword_summaries(buckets: dict) -> list:
    summaries = []
    for name, _ in TOPICS:
        items = buckets.get(name, [])
        if not items:
            continue
        representatives = pick_representatives(items, 5)
        summaries.append({
            "topic": name,
            "question_count": len(items),
            "representative_ids": [q["id"] for q in representatives],
        })
    return summaries


# ── メイン ────────────────────────────────────────────────────
def main():
    qas = json.loads(DATA_FILE.read_text("utf-8"))
    print(f"読み込み: {len(qas)}件")

    buckets = build_theme_buckets(qas)
    print(f"テーマ分類: {sum(len(v) for v in buckets.values())}件 / {len(buckets)}テーマ")

    groq_key = os.environ.get("GROQ_API_KEY", "")
    gemini_key = os.environ.get("GEMINI_API_KEY", "")
    summaries = None

    if groq_key:
        print(f"Groq API で要約生成中...")
        try:
            summaries = call_groq(groq_key, buckets)
            print(f"Groq 完了: {len(summaries)}テーマ")
        except Exception as e:
            print(f"Groq 失敗 ({e})。次を試みます...")
            summaries = None

    if not summaries and gemini_key:
        print("Gemini API で要約生成中...")
        try:
            summaries = call_gemini(gemini_key, qas)
            print(f"Gemini 完了: {len(summaries)}テーマ")
        except Exception as e:
            print(f"Gemini 失敗 ({e})。キーワードベースにフォールバック...")
            summaries = None

    if not summaries:
        print("キーワードベースで分類中...")
        summaries = keyword_summaries(buckets)
        print(f"キーワードベース完了: {len(summaries)}テーマ")

    SUMMARIES_FILE.write_text(
        json.dumps(summaries, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"保存: {SUMMARIES_FILE}")


if __name__ == "__main__":
    main()

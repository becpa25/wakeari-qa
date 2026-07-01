#!/usr/bin/env python3
"""data/qas.json を読み込み、キーワードベースでテーマ別まとめを生成して
data/summaries.json に保存する。外部APIキー不要。

各テーマにキーワードリストを定義し、Q&Aテキストとマッチングして分類する。
各テーマの「まとめ」は代表的な回答を抜粋して構成する。
"""
import json
from pathlib import Path
from collections import defaultdict

DATA_FILE = Path(__file__).parent.parent / "data" / "qas.json"
SUMMARIES_FILE = Path(__file__).parent.parent / "data" / "summaries.json"

# テーマ定義: (テーマ名, キーワードリスト)
TOPICS = [
    ("監査法人の選び方", [
        "法人選び", "big4", "big 4", "大手", "中小", "準大手", "トーマツ", "あずさ",
        "新日本", "pwc", "ey", "deloitte", "kpmg", "法人の違い", "どこがいい",
        "どこに行く", "入所", "就職先", "法人ごと",
    ]),
    ("給与・ボーナス", [
        "給与", "給料", "年収", "ボーナス", "賞与", "手取り", "昇給", "報酬",
        "いくら", "稼げる", "収入", "月給", "基本給", "インセン",
    ]),
    ("就活・面接対策", [
        "就活", "就職活動", "面接", "エントリー", "es", "志望動機", "インターン",
        "選考", "内定", "リクルーター", "合同説明会", "受験生", "面談",
    ]),
    ("試験勉強・学習法", [
        "勉強", "学習", "テキスト", "答練", "模試", "cpa", "tac", "大原",
        "短答", "論文", "合格", "不合格", "勉強時間", "スケジュール",
        "暗記", "理解", "論点", "科目",
    ]),
    ("監査の仕事内容", [
        "監査", "クライアント", "往査", "調書", "レビュー", "マネージャー",
        "スタッフ", "シニア", "in-charge", "インチャージ", "監査手続",
        "監査法人", "会計士の仕事", "仕事内容",
    ]),
    ("キャリア・転職", [
        "転職", "キャリア", "独立", "事業会社", "cfo", "コンサル", "fas",
        "出向", "ipo", "スタートアップ", "ベンチャー", "将来", "キャリアパス",
        "退職", "辞め",
    ]),
    ("ワークライフバランス", [
        "残業", "忙しい", "繁忙期", "暇", "有給", "休暇", "休み", "プライベート",
        "働き方", "リモート", "テレワーク", "在宅", "ワーク", "激務",
    ]),
    ("会計・税務の知識", [
        "会計", "税務", "ifrs", "j-gaap", "連結", "開示", "税効果", "減損",
        "のれん", "公認会計士", "税理士", "簿記", "財務諸表", "経理",
    ]),
    ("人間関係・職場環境", [
        "上司", "同僚", "先輩", "後輩", "パートナー", "人間関係", "職場",
        "チーム", "雰囲気", "文化", "飲み会", "コミュニケーション",
    ]),
    ("お金・資産形成", [
        "投資", "株", "資産", "節税", "貯金", "nisa", "idc", "ideco",
        "不動産", "副業", "運用", "資産形成", "財産",
    ]),
    ("プライベート・趣味", [
        "趣味", "旅行", "恋愛", "結婚", "友達", "遊び", "食事", "スポーツ",
        "ゲーム", "読書", "映画", "音楽", "プライベート",
    ]),
    ("Big4監査法人の比較", [
        "big4比較", "トーマツとあずさ", "どっちがいい", "大手比較",
        "各法人", "法人比較", "big4の違い",
    ]),
    ("試験合格後の生活", [
        "合格後", "登録", "修了考査", "補習所", "合格してから",
        "会計士になって", "資格取得後",
    ]),
]


def score(text: str, keywords: list[str]) -> int:
    t = text.lower()
    return sum(1 for kw in keywords if kw.lower() in t)


def extract_key_answers(qas: list, max_chars: int = 500) -> str:
    """回答を長さ順にソートして代表的なものを抜粋する。"""
    sorted_qas = sorted(qas, key=lambda x: len(x.get("answer") or ""), reverse=True)
    parts = []
    total = 0
    for qa in sorted_qas[:5]:
        ans = (qa.get("answer") or "").strip()
        if not ans or len(ans) < 10:
            continue
        snippet = ans[:120].replace("\n", " ")
        if len(ans) > 120:
            snippet += "…"
        parts.append(f"・{snippet}")
        total += len(snippet)
        if total >= max_chars:
            break
    return "\n".join(parts) if parts else "（回答データなし）"


def main():
    qas = json.loads(DATA_FILE.read_text("utf-8"))
    print(f"読み込み: {len(qas)}件")

    buckets: dict[str, list] = defaultdict(list)
    unclassified = []

    for qa in qas:
        text = (qa.get("question") or "") + " " + (qa.get("answer") or "")
        best_topic = None
        best_score = 0
        for topic_name, keywords in TOPICS:
            s = score(text, keywords)
            if s > best_score:
                best_score = s
                best_topic = topic_name
        if best_topic and best_score >= 1:
            buckets[best_topic].append(qa)
        else:
            unclassified.append(qa)

    summaries = []
    for topic_name, keywords in TOPICS:
        matched = buckets.get(topic_name, [])
        if not matched:
            continue
        liked = [q for q in matched if q.get("liked")]
        representative = liked if liked else matched
        summary_text = extract_key_answers(representative)
        summaries.append({
            "topic": topic_name,
            "summary": summary_text,
            "question_count": len(matched),
        })
        print(f"  {topic_name}: {len(matched)}件")

    if unclassified:
        print(f"  未分類: {len(unclassified)}件")

    SUMMARIES_FILE.write_text(
        json.dumps(summaries, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"完了: {len(summaries)}テーマ → {SUMMARIES_FILE}")


if __name__ == "__main__":
    main()

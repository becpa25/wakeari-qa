#!/usr/bin/env python3
"""querie.me から全Q&Aを取得し data/qas.json に保存する（GitHub Actions用）。
既存データとマージするためid基準でupsertし、新着のみ追加される。"""
import json
import urllib.request
from pathlib import Path

USER_ID = "1nEg2qZrUVBeOfaALc0EP79TjdYk"
API_URL = f"https://querie.me/api/qas?kind=recent&count=50000&userId={USER_ID}"
DATA_FILE = Path(__file__).parent.parent / "data" / "qas.json"


def fetch() -> list:
    req = urllib.request.Request(API_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def main():
    DATA_FILE.parent.mkdir(exist_ok=True)

    existing = {}
    if DATA_FILE.exists():
        for item in json.loads(DATA_FILE.read_text("utf-8")):
            existing[item["id"]] = item

    fetched = fetch()
    new_count = 0
    for item in fetched:
        qid = item["id"]
        record = {
            "id": qid,
            "question": item.get("text") or "",
            "answer": item.get("answer") or "",
            "asked_at": item.get("askedAt"),
            "answered_at": item.get("answeredAt"),
            "liked": bool(item.get("liked")),
            "reply_to_question_id": item.get("replyToQuestionId"),
        }
        if qid not in existing:
            new_count += 1
        existing[qid] = record

    sorted_items = sorted(
        existing.values(),
        key=lambda x: x.get("asked_at") or 0,
        reverse=True,
    )
    DATA_FILE.write_text(
        json.dumps(sorted_items, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"取得: {len(fetched)}件 / 新規: {new_count}件 / 合計: {len(sorted_items)}件")


if __name__ == "__main__":
    main()

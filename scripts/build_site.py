#!/usr/bin/env python3
"""data/qas.json と data/summaries.json から index.html を生成する。
外部CDN依存なし・完全オフライン動作の自己完結HTMLを出力する。"""
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent
QAS_FILE = ROOT / "data" / "qas.json"
SUMMARIES_FILE = ROOT / "data" / "summaries.json"
OUT_FILE = ROOT / "index.html"

QUERIE_URL = "https://querie.me/user/wakearikaikei"

HTML = """\
<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>訳アリさん 過去Q&A検索</title>
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,"Hiragino Sans",sans-serif;background:#f5f6fa;color:#1a1a2e;min-height:100vh}
a{color:inherit;text-decoration:none}

/* ヘッダー */
header{background:#1e3a5f;color:#fff;padding:1.2rem 1rem 1rem;text-align:center}
header h1{font-size:1.25rem;font-weight:700;letter-spacing:.02em}
header p{font-size:.8rem;opacity:.75;margin-top:.3rem}

/* 検索バー（固定） */
#search-wrap{position:sticky;top:0;z-index:100;background:#fff;border-bottom:1px solid #dde;padding:.75rem 1rem;display:flex;gap:.5rem;align-items:center}
#search{flex:1;font-size:1rem;padding:.55rem .8rem;border:1.5px solid #b0b8d0;border-radius:8px;outline:none;transition:border-color .2s}
#search:focus{border-color:#1e3a5f}
#search-count{font-size:.78rem;color:#888;white-space:nowrap;min-width:4.5rem;text-align:right}

main{max-width:780px;margin:0 auto;padding:1rem}

/* テーマ別まとめ */
#summaries-section{margin-bottom:1.5rem}
#summaries-section h2{font-size:.95rem;font-weight:700;color:#1e3a5f;margin-bottom:.6rem;display:flex;align-items:center;gap:.4rem}
#summaries-section h2::before{content:"";display:block;width:4px;height:1em;background:#1e3a5f;border-radius:2px}
.topic-card{background:#fff;border-radius:10px;margin-bottom:.5rem;box-shadow:0 1px 4px rgba(0,0,0,.07);overflow:hidden}
.topic-header{display:flex;justify-content:space-between;align-items:center;padding:.75rem 1rem;cursor:pointer;user-select:none}
.topic-header:hover{background:#f0f4ff}
.topic-name{font-weight:600;font-size:.9rem}
.topic-meta{font-size:.75rem;color:#888;flex-shrink:0;margin-left:.5rem}
.topic-arrow{font-size:.8rem;color:#aaa;transition:transform .2s;flex-shrink:0;margin-left:.4rem}
.topic-body{display:none;padding:.6rem .75rem .75rem;border-top:1px solid #eee}
.topic-card.open .topic-arrow{transform:rotate(180deg)}
.topic-card.open .topic-body{display:block}
#no-summaries{font-size:.85rem;color:#999;text-align:center;padding:1rem 0}
/* テーマ内ミニQ&Aカード */
.topic-qa-list{display:flex;flex-direction:column;gap:.5rem}
.topic-qa-item{background:#f8f9fc;border-radius:8px;padding:.65rem .8rem;border-left:3px solid #c7d3e8}
.topic-qa-q{font-size:.82rem;color:#444;margin-bottom:.35rem;line-height:1.55}
.topic-qa-q::before{content:"Q  ";font-weight:700;color:#1e3a5f;font-size:.75rem}
.topic-qa-a{font-size:.85rem;color:#222;line-height:1.6;background:#fff;border-radius:5px;padding:.4rem .6rem}
.topic-qa-a::before{content:"A  ";font-weight:700;color:#b45309;font-size:.75rem}
.topic-qa-link{display:block;font-size:.72rem;color:#2563eb;margin-top:.35rem;text-align:right}
.topic-qa-link:hover{text-decoration:underline}
.topic-more{font-size:.78rem;color:#888;text-align:center;padding:.4rem 0 .1rem}

/* Q&Aリスト */
#qa-section h2{font-size:.95rem;font-weight:700;color:#1e3a5f;margin-bottom:.6rem;display:flex;align-items:center;gap:.4rem}
#qa-section h2::before{content:"";display:block;width:4px;height:1em;background:#1e3a5f;border-radius:2px}
.qa-card{background:#fff;border-radius:10px;margin-bottom:.75rem;padding:.85rem 1rem;box-shadow:0 1px 4px rgba(0,0,0,.07)}
.qa-meta{display:flex;align-items:center;gap:.4rem;margin-bottom:.5rem;flex-wrap:wrap}
.qa-date{font-size:.75rem;color:#999}
.badge{font-size:.7rem;font-weight:700;padding:.1rem .45rem;border-radius:4px}
.badge-cont{background:#eef2ff;color:#4338ca}
.badge-liked{background:#fff1f2;color:#e11d48}
.qa-q-label,.qa-a-label{font-size:.72rem;font-weight:700;color:#888;margin-top:.5rem;margin-bottom:.2rem}
.qa-q{background:#f3f4f6;border-radius:6px;padding:.5rem .75rem;font-size:.88rem;line-height:1.65;white-space:pre-wrap;word-break:break-word}
.qa-a{background:#fff9ec;border-radius:6px;padding:.5rem .75rem;font-size:.88rem;line-height:1.65;white-space:pre-wrap;word-break:break-word}
.thread-link{font-size:.75rem;margin-top:.35rem;color:#2563eb}
.thread-link a{color:#2563eb}
.thread-link a:hover{text-decoration:underline}

/* 検索結果ゼロ */
#no-results{display:none;text-align:center;padding:2rem 1rem}
#no-results p{color:#888;font-size:.9rem;margin-bottom:1rem}

/* CTAボタン */
.btn-ask{display:inline-block;background:#1e3a5f;color:#fff;font-size:.95rem;font-weight:700;padding:.75rem 2rem;border-radius:30px;letter-spacing:.03em;transition:background .2s}
.btn-ask:hover{background:#2a5080}
#bottom-cta{text-align:center;padding:2rem 1rem 3rem}
#bottom-cta p{font-size:.85rem;color:#888;margin-bottom:.75rem}

/* ハイライト */
mark{background:#fff176;color:inherit;border-radius:2px}
</style>
</head>
<body>

<header>
  <h1>訳アリさん 過去Q&amp;A検索</h1>
  <p>全 {total_count} 件 ／ 最終更新 {updated_at}</p>
</header>

<div id="search-wrap">
  <input id="search" type="search" placeholder="キーワードで絞り込む（例：ボーナス、就活、監査法人）" autocomplete="off">
  <span id="search-count"></span>
</div>

<main>

  <!-- テーマ別まとめ -->
  <section id="summaries-section">
    <h2>テーマ別まとめ</h2>
    <div id="summaries-list">{summaries_html}</div>
  </section>

  <!-- Q&A一覧 -->
  <section id="qa-section">
    <h2>Q&amp;A一覧</h2>
    <div id="qa-list"></div>
    <div id="no-results">
      <p>「<span id="no-results-keyword"></span>」に一致する回答が見つかりませんでした。</p>
      <p style="font-size:.8rem;color:#aaa;margin-bottom:1rem">直接質問してみましょう！</p>
      <a class="btn-ask" href="{querie_url}" target="_blank" rel="noopener">訳アリさんに質問する →</a>
    </div>
  </section>

</main>

<div id="bottom-cta">
  <p>知りたい情報が見つからない場合は、直接質問できます。</p>
  <a class="btn-ask" href="{querie_url}" target="_blank" rel="noopener">訳アリさんに質問する →</a>
</div>

<script>
const QAS = {qa_json};

// id→インデックス、子質問マップを事前構築
const idSet = new Set(QAS.map(q => q.id));
const childrenOf = {};
QAS.forEach(q => {
  if (q.reply_to_question_id) {
    (childrenOf[q.reply_to_question_id] = childrenOf[q.reply_to_question_id] || []).push(q.id);
  }
});

function esc(s) {
  return (s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

function highlight(text, kw) {
  if (!kw) return esc(text);
  const re = new RegExp(kw.replace(/[.*+?^${}()|[\\]\\\\]/g,'\\\\$&'), 'gi');
  return esc(text).replace(re, m => `<mark>${m}</mark>`);
}

function fmtDate(ts) {
  if (!ts) return '';
  const d = new Date(ts * 1000);
  return d.getFullYear() + '/' + String(d.getMonth()+1).padStart(2,'0') + '/' + String(d.getDate()).padStart(2,'0');
}

function renderCard(q, kw) {
  const badges = [];
  if (q.reply_to_question_id) badges.push('<span class="badge badge-cont">続き質問</span>');
  if (q.liked) badges.push('<span class="badge badge-liked">いいね!</span>');

  let parentLink = '';
  if (q.reply_to_question_id) {
    if (idSet.has(q.reply_to_question_id)) {
      parentLink = `<div class="thread-link">↑ <a href="#qa-${q.reply_to_question_id}">元の質問を見る</a></div>`;
    } else {
      parentLink = '<div class="thread-link">↑ 元の質問は未取得です</div>';
    }
  }

  let childLinks = '';
  const children = childrenOf[q.id];
  if (children && children.length) {
    const links = children.map((cid, i) => `<a href="#qa-${cid}">${i+1}</a>`).join(' / ');
    childLinks = `<div class="thread-link">↓ 続きの質問(${children.length}件): ${links}</div>`;
  }

  return `<div class="qa-card" id="qa-${q.id}">
  <div class="qa-meta">
    <span class="qa-date">${fmtDate(q.asked_at)}</span>
    ${badges.join('')}
  </div>
  ${parentLink}
  <div class="qa-q-label">質問</div>
  <div class="qa-q">${highlight(q.question, kw)}</div>
  <div class="qa-a-label">回答</div>
  <div class="qa-a">${highlight(q.answer, kw)}</div>
  ${childLinks}
</div>`;
}

const qaList = document.getElementById('qa-list');
const noResults = document.getElementById('no-results');
const noResultsKw = document.getElementById('no-results-keyword');
const countEl = document.getElementById('search-count');

const summariesSection = document.getElementById('summaries-section');

function render(kw) {
  const q = (kw || '').trim();
  const filtered = q
    ? QAS.filter(x => (x.question + ' ' + x.answer).includes(q))
    : QAS;

  countEl.textContent = q ? `${filtered.length}件` : '';

  // 検索中はテーマまとめを隠してQ&Aリストを上に
  summariesSection.style.display = q ? 'none' : '';

  if (filtered.length === 0) {
    qaList.innerHTML = '';
    noResultsKw.textContent = q;
    noResults.style.display = 'block';
  } else {
    noResults.style.display = 'none';
    qaList.innerHTML = filtered.map(x => renderCard(x, q)).join('');
  }
}

render('');

let timer;
document.getElementById('search').addEventListener('input', e => {
  clearTimeout(timer);
  timer = setTimeout(() => render(e.target.value), 120);
});

// テーマ別アコーディオン
document.querySelectorAll('.topic-header').forEach(h => {
  h.addEventListener('click', () => h.closest('.topic-card').classList.toggle('open'));
});
</script>
</body>
</html>
"""


def esc(s: str) -> str:
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def truncate(text: str, limit: int) -> str:
    text = (text or "").replace("\n", " ").strip()
    return text[:limit] + "…" if len(text) > limit else text


def build_summaries_html(summaries: list, qas_by_id: dict) -> str:
    if not summaries:
        return '<p id="no-summaries">まだ生成されていません。</p>'
    parts = []
    for s in summaries:
        topic = esc(s.get("topic", ""))
        count = s.get("question_count", "")
        rep_ids = s.get("representative_ids", [])

        if rep_ids:
            # ── ミニQ&Aカード形式 ──
            cards = []
            for qid in rep_ids:
                qa = qas_by_id.get(qid)
                if not qa:
                    continue
                q_text = esc(truncate(qa.get("question", ""), 80))
                a_text = esc(truncate(qa.get("answer", ""), 150))
                cards.append(
                    f'<div class="topic-qa-item">'
                    f'<div class="topic-qa-q">{q_text}</div>'
                    f'<div class="topic-qa-a">{a_text}</div>'
                    f'<a class="topic-qa-link" href="#qa-{qid}">この質問を全文で見る →</a>'
                    f'</div>'
                )
            body = (
                f'<div class="topic-qa-list">{"".join(cards)}</div>'
                f'<p class="topic-more">他 {count - len(cards)} 件 → 下の検索で「{topic}」と入力</p>'
            )
        else:
            # Gemini生成のテキスト要約（フォールバック）
            body = f'<p style="font-size:.88rem;line-height:1.7;color:#333">{esc(s.get("summary",""))}</p>'

        parts.append(
            f'<div class="topic-card">'
            f'<div class="topic-header">'
            f'<span class="topic-name">{topic}</span>'
            f'<span class="topic-meta">{count}件</span>'
            f'<span class="topic-arrow">▼</span>'
            f'</div>'
            f'<div class="topic-body">{body}</div>'
            f'</div>'
        )
    return "\n".join(parts)


def main():
    qas = json.loads(QAS_FILE.read_text("utf-8")) if QAS_FILE.exists() else []
    summaries = (
        json.loads(SUMMARIES_FILE.read_text("utf-8"))
        if SUMMARIES_FILE.exists()
        else []
    )
    qas_by_id = {q["id"]: q for q in qas}

    html = HTML
    html = html.replace("{total_count}", str(len(qas)))
    html = html.replace("{updated_at}", datetime.now().strftime("%Y-%m-%d"))
    html = html.replace("{summaries_html}", build_summaries_html(summaries, qas_by_id))
    html = html.replace("{querie_url}", QUERIE_URL)
    html = html.replace("{qa_json}", json.dumps(qas, ensure_ascii=False))
    OUT_FILE.write_text(html, encoding="utf-8")
    print(f"生成完了: {OUT_FILE} ({len(qas)}件, {len(summaries)}テーマ)")


if __name__ == "__main__":
    main()

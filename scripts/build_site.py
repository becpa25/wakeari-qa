#!/usr/bin/env python3
"""data/qas.json と data/summaries.json から index.html と qa.html を生成する。"""
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent
QAS_FILE = ROOT / "data" / "qas.json"
SUMMARIES_FILE = ROOT / "data" / "summaries.json"
ARTICLES_FILE = ROOT / "data" / "articles.json"
QUERIE_URL = "https://querie.me/user/wakearikaikei"

# ── 共通CSS ───────────────────────────────────────────────────
COMMON_CSS = """
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,"Hiragino Sans",sans-serif;background:#f5f6fa;color:#1a1a2e;min-height:100vh}
a{color:inherit;text-decoration:none}
header{background:#1e3a5f;color:#fff;padding:1.2rem 1rem .9rem;text-align:center}
header h1{font-size:1.2rem;font-weight:700}
header p{font-size:.78rem;opacity:.7;margin-top:.25rem}
.nav-bar{background:#fff;border-bottom:1px solid #dde;padding:.5rem 1rem;display:flex;gap:.75rem;justify-content:center}
.nav-bar a{font-size:.82rem;color:#1e3a5f;font-weight:600;padding:.3rem .8rem;border-radius:6px;border:1.5px solid #c7d3e8;white-space:nowrap}
.nav-bar a.active,.nav-bar a:hover{background:#1e3a5f;color:#fff;border-color:#1e3a5f}
main{max-width:780px;margin:0 auto;padding:1rem}
h2.section-title{font-size:.95rem;font-weight:700;color:#1e3a5f;margin-bottom:.6rem;display:flex;align-items:center;gap:.4rem}
h2.section-title::before{content:"";display:block;width:4px;height:1em;background:#1e3a5f;border-radius:2px}
.btn-ask{display:inline-block;background:#1e3a5f;color:#fff;font-size:.95rem;font-weight:700;padding:.75rem 2rem;border-radius:30px;transition:background .2s}
.btn-ask:hover{background:#2a5080}
#bottom-cta{text-align:center;padding:2rem 1rem 3rem}
#bottom-cta p{font-size:.85rem;color:#888;margin-bottom:.75rem}
"""

# ── まとめページ CSS ──────────────────────────────────────────
INDEX_CSS = """
.topic-card{background:#fff;border-radius:10px;margin-bottom:.6rem;box-shadow:0 1px 4px rgba(0,0,0,.07);overflow:hidden}
.topic-header{display:flex;justify-content:space-between;align-items:center;padding:.8rem 1rem;cursor:pointer;user-select:none}
.topic-header:hover{background:#f0f4ff}
.topic-name{font-weight:600;font-size:.92rem}
.topic-meta{font-size:.75rem;color:#888;flex-shrink:0;margin-left:.5rem}
.topic-arrow{font-size:.8rem;color:#aaa;transition:transform .2s;flex-shrink:0;margin-left:.4rem}
.topic-body{display:none;padding:.7rem .9rem .9rem;border-top:1px solid #eee}
.topic-card.open .topic-arrow{transform:rotate(180deg)}
.topic-card.open .topic-body{display:block}
/* LLM要約テキスト */
.summary-text{font-size:.88rem;line-height:1.8;color:#222;white-space:pre-wrap}
/* ミニQ&Aカード */
.topic-qa-list{display:flex;flex-direction:column;gap:.5rem;margin-bottom:.5rem}
.topic-qa-item{background:#f8f9fc;border-radius:8px;padding:.6rem .8rem;border-left:3px solid #c7d3e8}
.topic-qa-q{font-size:.82rem;color:#444;margin-bottom:.3rem;line-height:1.55}
.topic-qa-q::before{content:"Q  ";font-weight:700;color:#1e3a5f;font-size:.74rem}
.topic-qa-a{font-size:.85rem;color:#222;line-height:1.6;background:#fff;border-radius:5px;padding:.35rem .55rem}
.topic-qa-a::before{content:"A  ";font-weight:700;color:#b45309;font-size:.74rem}
.topic-qa-link{display:block;font-size:.72rem;color:#2563eb;margin-top:.3rem;text-align:right}
.topic-qa-link:hover{text-decoration:underline}
.topic-search-link{display:block;font-size:.78rem;color:#2563eb;margin-top:.5rem;text-align:center;padding:.3rem;background:#eef2ff;border-radius:6px}
.topic-search-link:hover{background:#dbe4ff}
"""

# ── Q&Aページ CSS ─────────────────────────────────────────────
QA_CSS = """
#search-wrap{position:sticky;top:0;z-index:100;background:#fff;border-bottom:1px solid #dde;padding:.7rem 1rem;display:flex;gap:.5rem;align-items:center}
#search{flex:1;font-size:1rem;padding:.55rem .8rem;border:1.5px solid #b0b8d0;border-radius:8px;outline:none;transition:border-color .2s}
#search:focus{border-color:#1e3a5f}
#search-count{font-size:.78rem;color:#888;white-space:nowrap;min-width:4.5rem;text-align:right}
.qa-card{background:#fff;border-radius:10px;margin-bottom:.75rem;padding:.85rem 1rem;box-shadow:0 1px 4px rgba(0,0,0,.07)}
.qa-meta{display:flex;align-items:center;gap:.4rem;margin-bottom:.45rem;flex-wrap:wrap}
.qa-date{font-size:.75rem;color:#999}
.badge{font-size:.7rem;font-weight:700;padding:.1rem .45rem;border-radius:4px}
.badge-cont{background:#eef2ff;color:#4338ca}
.badge-liked{background:#fff1f2;color:#e11d48}
.qa-q-label,.qa-a-label{font-size:.72rem;font-weight:700;color:#888;margin-top:.45rem;margin-bottom:.2rem}
.qa-q{background:#f3f4f6;border-radius:6px;padding:.5rem .75rem;font-size:.88rem;line-height:1.65;white-space:pre-wrap;word-break:break-word}
.qa-a{background:#fff9ec;border-radius:6px;padding:.5rem .75rem;font-size:.88rem;line-height:1.65;white-space:pre-wrap;word-break:break-word}
.thread-link{font-size:.8rem;margin-top:.4rem}
.thread-link a{color:#2563eb;font-weight:600}
.thread-link a:hover{text-decoration:underline}
#no-results{display:none;text-align:center;padding:2rem 1rem}
#no-results p{color:#888;font-size:.9rem;margin-bottom:1rem}
mark{background:#fff176;color:inherit;border-radius:2px}
"""

# ── まとめページ HTML ─────────────────────────────────────────
INDEX_HTML = """\
<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>訳アリさん テーマ別まとめ</title>
<style>{common_css}{index_css}</style>
</head>
<body>
<header>
  <h1>訳アリさん テーマ別まとめ</h1>
  <p>全 {total_count} 件 ／ 最終更新 {updated_at}</p>
</header>
<nav class="nav-bar">
  <a href="index.html" class="active">テーマ別まとめ</a>
  <a href="articles.html">記事</a>
  <a href="qa.html">Q&A検索</a>
</nav>
<main>
  <h2 class="section-title">テーマ別まとめ</h2>
  {summaries_html}
</main>
<div id="bottom-cta">
  <p>知りたい情報が見つからない場合は直接質問できます。</p>
  <a class="btn-ask" href="{querie_url}" target="_blank" rel="noopener">訳アリさんに質問する →</a>
</div>
<script>
document.querySelectorAll('.topic-header').forEach(h => {{
  h.addEventListener('click', () => h.closest('.topic-card').classList.toggle('open'));
}});
</script>
</body>
</html>
"""

# ── Q&Aページ HTML ────────────────────────────────────────────
QA_HTML = """\
<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>訳アリさん Q&amp;A検索</title>
<style>{common_css}{qa_css}</style>
</head>
<body>
<header>
  <h1>訳アリさん Q&amp;A検索</h1>
  <p>全 {total_count} 件 ／ 最終更新 {updated_at}</p>
</header>
<nav class="nav-bar">
  <a href="index.html">テーマ別まとめ</a>
  <a href="articles.html">記事</a>
  <a href="qa.html" class="active">Q&A検索</a>
</nav>
<div id="search-wrap">
  <input id="search" type="search" placeholder="キーワードで絞り込む（例：ボーナス、就活、監査法人）" autocomplete="off">
  <span id="search-count"></span>
</div>
<main>
  <section id="qa-section">
    <h2 class="section-title">Q&amp;A一覧</h2>
    <div id="qa-list"></div>
    <div id="no-results">
      <p>「<span id="no-results-keyword"></span>」に一致する回答が見つかりませんでした。</p>
      <p style="font-size:.8rem;color:#aaa;margin-bottom:1rem">直接質問してみましょう！</p>
      <a class="btn-ask" href="{querie_url}" target="_blank" rel="noopener">訳アリさんに質問する →</a>
    </div>
  </section>
</main>
<div id="bottom-cta">
  <p>知りたい情報が見つからない場合は直接質問できます。</p>
  <a class="btn-ask" href="{querie_url}" target="_blank" rel="noopener">訳アリさんに質問する →</a>
</div>
<script>
const QAS = {qa_json};
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
      parentLink = '<div class="thread-link" style="color:#aaa">↑ 元の質問は未取得です</div>';
    }
  }

  let childLinks = '';
  const children = childrenOf[q.id];
  if (children && children.length) {
    if (children.length === 1) {
      childLinks = `<div class="thread-link">↓ <a href="#qa-${children[0]}">続きの質問を見る →</a></div>`;
    } else {
      const links = children.map((cid, i) => `<a href="#qa-${cid}">${i+1}件目</a>`).join(' ／ ');
      childLinks = `<div class="thread-link">↓ 続きの質問（${children.length}件）: ${links}</div>`;
    }
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

function render(kw) {
  const q = (kw || '').trim();
  const filtered = q ? QAS.filter(x => (x.question + ' ' + x.answer).includes(q)) : QAS;
  countEl.textContent = q ? `${filtered.length}件` : '';
  if (filtered.length === 0) {
    qaList.innerHTML = '';
    noResultsKw.textContent = q;
    noResults.style.display = 'block';
  } else {
    noResults.style.display = 'none';
    qaList.innerHTML = filtered.map(x => renderCard(x, q)).join('');
  }
}

// URLパラメータから初期キーワードを取得
const urlQ = new URLSearchParams(location.search).get('q') || '';
const searchEl = document.getElementById('search');
searchEl.value = urlQ;
render(urlQ);
if (urlQ) searchEl.focus();

let timer;
searchEl.addEventListener('input', e => {
  clearTimeout(timer);
  timer = setTimeout(() => render(e.target.value), 120);
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
        return '<p style="color:#999;text-align:center;padding:1rem">まだ生成されていません。</p>'
    parts = []
    for s in summaries:
        topic = esc(s.get("topic", ""))
        count = s.get("question_count", 0)
        rep_ids = s.get("representative_ids", [])
        summary_text = s.get("summary", "")

        if summary_text:
            # LLM生成の要約テキスト
            body = f'<div class="summary-text">{esc(summary_text)}</div>'
        elif rep_ids:
            # キーワードベースのミニQ&Aカード
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
                    f'<a class="topic-qa-link" href="qa.html#qa-{qid}">全文で見る →</a>'
                    f'</div>'
                )
            body = f'<div class="topic-qa-list">{"".join(cards)}</div>'
        else:
            body = '<p style="color:#aaa;font-size:.85rem">データなし</p>'

        search_link = (
            f'<a class="topic-search-link" href="qa.html?q={topic}">'
            f'「{topic}」の関連Q&A {count}件をすべて検索する →</a>'
        )

        parts.append(
            f'<div class="topic-card">'
            f'<div class="topic-header">'
            f'<span class="topic-name">{topic}</span>'
            f'<span class="topic-meta">{count}件</span>'
            f'<span class="topic-arrow">▼</span>'
            f'</div>'
            f'<div class="topic-body">{body}{search_link}</div>'
            f'</div>'
        )
    return "\n".join(parts)


ARTICLES_CSS = """
.article-list{display:flex;flex-direction:column;gap:1.5rem}
.article-card{background:#fff;border-radius:12px;box-shadow:0 1px 4px rgba(0,0,0,.08);overflow:hidden}
.article-card-header{padding:1rem 1.2rem .8rem;border-bottom:1px solid #eee;display:flex;justify-content:space-between;align-items:center;gap:.5rem;cursor:pointer;user-select:none}
.article-card-header:hover{background:#f8f9ff}
.article-topic{font-size:1rem;font-weight:700;color:#1e3a5f}
.article-meta{font-size:.75rem;color:#999;flex-shrink:0}
.article-arrow{font-size:.8rem;color:#aaa;transition:transform .2s;flex-shrink:0}
.article-card.open .article-arrow{transform:rotate(180deg)}
.article-body{display:none;padding:1.2rem 1.4rem 1.4rem}
.article-card.open .article-body{display:block}
.article-body h1{font-size:1.1rem;font-weight:700;color:#1a1a2e;margin-bottom:1rem;line-height:1.5}
.article-body h2{font-size:.95rem;font-weight:700;color:#1e3a5f;margin:1.4rem 0 .5rem;padding-left:.6rem;border-left:3px solid #1e3a5f}
.article-body p{font-size:.9rem;line-height:1.85;color:#222;margin-bottom:.8rem}
.article-body hr{border:none;border-top:1px solid #eee;margin:1rem 0}
.article-refs{margin-top:.6rem;padding:.5rem .75rem;background:#f5f6fa;border-radius:6px;font-size:.75rem}
.article-refs-label{font-weight:700;color:#666;margin-bottom:.3rem}
.article-refs a{color:#2563eb;display:block;margin:.2rem 0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.article-refs a:hover{text-decoration:underline}
.article-search-link{display:block;font-size:.78rem;color:#2563eb;margin-top:1rem;text-align:center;padding:.35rem;background:#eef2ff;border-radius:6px}
.article-search-link:hover{background:#dbe4ff}
"""

ARTICLES_HTML = """\
<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>訳アリさん テーマ別記事</title>
<style>{common_css}{articles_css}</style>
</head>
<body>
<header>
  <h1>訳アリさん テーマ別記事</h1>
  <p>全 {total_count} 件のQ&Aをもとに生成 ／ {updated_at}</p>
</header>
<nav class="nav-bar">
  <a href="index.html">テーマ別まとめ</a>
  <a href="articles.html" class="active">記事</a>
  <a href="qa.html">Q&A検索</a>
</nav>
<main>
  <div class="article-list">{articles_html}</div>
</main>
<div id="bottom-cta">
  <p>知りたい情報が見つからない場合は直接質問できます。</p>
  <a class="btn-ask" href="{querie_url}" target="_blank" rel="noopener">訳アリさんに質問する →</a>
</div>
<script>
document.querySelectorAll('.article-card-header').forEach(h => {{
  h.addEventListener('click', () => h.closest('.article-card').classList.toggle('open'));
}});
</script>
</body>
</html>
"""


def article_to_html(article: dict) -> str:
    import re
    text = article.get("article", "")
    topic = esc(article.get("topic", ""))
    refs = article.get("references", [])
    refs_by_id = {r["id"]: r for r in refs}

    html_parts = []
    ref_block_ids = []

    for line in text.split("\n"):
        # [参照Q&A]: id1, id2, ... → 参照ブロックに変換
        m = re.match(r'\[参照Q&A\]:\s*(.+)', line)
        if m:
            ids = [i.strip() for i in m.group(1).split(',')]
            ref_block_ids.extend(ids)
            # 参照ブロックを出力
            links = []
            for qid in ids:
                r = refs_by_id.get(qid)
                if r:
                    preview = esc(r.get("question_preview", qid))
                    url = r["url"]
                    links.append(f'<a href="{url}" target="_blank" rel="noopener">{preview}…</a>')
            if links:
                html_parts.append(
                    f'<div class="article-refs">'
                    f'<div class="article-refs-label">参照元 Q&A</div>'
                    + "".join(links)
                    + '</div>'
                )
            continue

        if line.startswith("# "):
            html_parts.append(f'<h1>{esc(line[2:])}</h1>')
        elif line.startswith("## "):
            html_parts.append(f'<h2>{esc(line[3:])}</h2>')
        elif line.strip() == "---":
            html_parts.append('<hr>')
        elif line.strip():
            html_parts.append(f'<p>{esc(line)}</p>')

    body_html = "\n".join(html_parts)
    search_link = (
        f'<a class="article-search-link" href="qa.html?q={topic}">'
        f'「{topic}」の関連Q&A {article.get("question_count", "")}件を全文検索 →</a>'
    )
    return body_html + search_link


def build_articles_html(articles: list) -> str:
    if not articles:
        return '<p style="color:#999;text-align:center;padding:2rem">記事がまだ生成されていません。</p>'
    parts = []
    for a in articles:
        topic = esc(a.get("topic", ""))
        count = a.get("question_count", "")
        date = a.get("generated_at", "")
        body = article_to_html(a)
        parts.append(
            f'<div class="article-card">'
            f'<div class="article-card-header">'
            f'<span class="article-topic">{topic}</span>'
            f'<span class="article-meta">{count}件参照 / {date}</span>'
            f'<span class="article-arrow">▼</span>'
            f'</div>'
            f'<div class="article-body">{body}</div>'
            f'</div>'
        )
    return "\n".join(parts)


def main():
    qas = json.loads(QAS_FILE.read_text("utf-8")) if QAS_FILE.exists() else []
    summaries = (
        json.loads(SUMMARIES_FILE.read_text("utf-8"))
        if SUMMARIES_FILE.exists() else []
    )
    articles = (
        json.loads(ARTICLES_FILE.read_text("utf-8"))
        if ARTICLES_FILE.exists() else []
    )
    qas_by_id = {q["id"]: q for q in qas}
    now = datetime.now().strftime("%Y-%m-%d")
    common = COMMON_CSS
    summaries_html = build_summaries_html(summaries, qas_by_id)
    qa_json = json.dumps(qas, ensure_ascii=False)

    # index.html（まとめページ）
    index = INDEX_HTML
    index = index.replace("{common_css}", common).replace("{index_css}", INDEX_CSS)
    index = index.replace("{total_count}", str(len(qas)))
    index = index.replace("{updated_at}", now)
    index = index.replace("{summaries_html}", summaries_html)
    index = index.replace("{querie_url}", QUERIE_URL)
    (ROOT / "index.html").write_text(index, encoding="utf-8")

    # qa.html（Q&A検索ページ）
    qa = QA_HTML
    qa = qa.replace("{common_css}", common).replace("{qa_css}", QA_CSS)
    qa = qa.replace("{total_count}", str(len(qas)))
    qa = qa.replace("{updated_at}", now)
    qa = qa.replace("{querie_url}", QUERIE_URL)
    qa = qa.replace("{qa_json}", qa_json)
    (ROOT / "qa.html").write_text(qa, encoding="utf-8")

    # articles.html（記事ページ）
    art = ARTICLES_HTML
    art = art.replace("{common_css}", common).replace("{articles_css}", ARTICLES_CSS)
    art = art.replace("{total_count}", str(len(qas)))
    art = art.replace("{updated_at}", now)
    art = art.replace("{articles_html}", build_articles_html(articles))
    art = art.replace("{querie_url}", QUERIE_URL)
    (ROOT / "articles.html").write_text(art, encoding="utf-8")

    print(f"生成完了: index.html + articles.html + qa.html ({len(qas)}件, {len(articles)}記事)")


if __name__ == "__main__":
    main()

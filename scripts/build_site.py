#!/usr/bin/env python3
"""data/articles.json から index.html（記事一覧）と個別記事ページを生成する。"""
import json
import re
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent
ARTICLES_FILE = ROOT / "data" / "articles.json"
QUERIE_URL = "https://querie.me/user/wakearikaikei"
SITE_TITLE = "訳アリさん質問箱非公式まとめ"

# ── 共通CSS ───────────────────────────────────────────────────
COMMON_CSS = """
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,"Hiragino Sans",sans-serif;background:#f5f6fa;color:#1a1a2e;min-height:100vh}
a{color:inherit;text-decoration:none}
header{background:#1e3a5f;color:#fff;padding:1.1rem 1rem .85rem;text-align:center;cursor:pointer}
header:hover{background:#162e4d}
header h1{font-size:1.15rem;font-weight:700;letter-spacing:.02em}
main{max-width:760px;margin:0 auto;padding:1rem}
.btn-ask{display:inline-block;background:#1e3a5f;color:#fff;font-size:.95rem;font-weight:700;padding:.7rem 1.8rem;border-radius:30px;transition:background .2s}
.btn-ask:hover{background:#2a5080}
#bottom-cta{text-align:center;padding:1.5rem 1rem 3rem}
#bottom-cta p{display:none}
"""

# ── 記事一覧ページ CSS ────────────────────────────────────────
LIST_CSS = """
.article-list{display:flex;flex-direction:column;gap:.6rem;margin-top:.5rem}
.article-item{background:#fff;border-radius:10px;box-shadow:0 1px 4px rgba(0,0,0,.07);display:flex;align-items:center;justify-content:space-between;padding:.9rem 1.1rem;cursor:pointer;transition:background .15s}
.article-item:hover{background:#f0f4ff}
.article-item-left{flex:1;min-width:0}
.article-topic{font-size:.95rem;font-weight:700;color:#1e3a5f}
.article-ref-count{font-size:.85rem;color:#999;flex-shrink:0;margin-left:1rem;white-space:nowrap;text-align:right}
"""

LIST_HTML = """\
<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{site_title}</title>
<style>{common_css}{list_css}</style>
</head>
<body>
<header onclick="location.href='index.html'">
  <h1>{site_title}</h1>
</header>
<main>
  <div class="article-list">{list_items}</div>
</main>
<div id="bottom-cta">
  <p>気になることがあれば訳アリさんに直接質問できます。</p>
  <a class="btn-ask" href="{querie_url}" target="_blank" rel="noopener">訳アリさんに質問する →</a>
</div>
</body>
</html>
"""

# ── 個別記事ページ CSS ────────────────────────────────────────
ARTICLE_CSS = """
.back-link{display:inline-block;font-size:.8rem;color:#2563eb;margin-bottom:1rem}
.back-link:hover{text-decoration:underline}
.article-header-meta{display:flex;justify-content:space-between;align-items:center;margin-bottom:1.2rem;flex-wrap:wrap;gap:.5rem}
.article-header-topic{font-size:1.1rem;font-weight:700;color:#1a1a2e}
.article-ref-badge{font-size:.75rem;color:#888;text-align:right}
.article-content h1{font-size:1.05rem;font-weight:700;color:#1a1a2e;margin-bottom:1rem;line-height:1.6}
.article-content h2{font-size:.95rem;font-weight:700;color:#1e3a5f;margin:1.5rem 0 .5rem;padding-left:.6rem;border-left:3px solid #1e3a5f;line-height:1.5}
.article-content p{font-size:.9rem;line-height:1.9;color:#222;margin-bottom:.75rem}
.article-content hr{border:none;border-top:1px solid #eee;margin:1rem 0}
.ref-block{margin:.1rem 0 1rem;padding:.5rem .75rem;background:#f5f6fa;border-radius:6px;border-left:2px solid #c7d3e8}
.ref-block-label{font-size:.7rem;font-weight:700;color:#999;margin-bottom:.25rem}
.ref-block a{font-size:.75rem;color:#2563eb;display:block;margin:.15rem 0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.ref-block a:hover{text-decoration:underline}
.article-footer{margin-top:2rem;padding-top:1rem;border-top:1px solid #eee;text-align:center}
.article-footer a{font-size:.8rem;color:#2563eb}
.article-footer a:hover{text-decoration:underline}
.qa-search-link{display:block;font-size:.8rem;margin-top:1.5rem;text-align:center;padding:.4rem;background:#eef2ff;border-radius:6px;color:#2563eb}
.qa-search-link:hover{background:#dbe4ff}
"""

ARTICLE_HTML = """\
<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{topic} | {site_title}</title>
<style>{common_css}{article_css}</style>
</head>
<body>
<header onclick="location.href='index.html'">
  <h1>{site_title}</h1>
</header>
<main>
  <div class="article-header-meta">
    <span class="article-header-topic">{topic}</span>
    <span class="article-ref-badge">{ref_count}件参照 / {generated_at}</span>
  </div>
  <div class="article-content">{article_body}</div>
  <div class="article-footer">
    <a href="index.html">← テーマ一覧に戻る</a>
  </div>
</main>
<div id="bottom-cta">
  <p>気になることがあれば訳アリさんに直接質問できます。</p>
  <a class="btn-ask" href="{querie_url}" target="_blank" rel="noopener">訳アリさんに質問する →</a>
</div>
</body>
</html>
"""


def esc(s: str) -> str:
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def article_to_html(article: dict) -> str:
    text = article.get("article", "")
    refs = article.get("references", [])
    refs_by_id = {r["id"]: r for r in refs}

    html_parts = []
    for line in text.split("\n"):
        # 参照Q&Aマーカー
        m = re.match(r'\[参照Q&A\]:\s*(.+)', line)
        if m:
            ids = [i.strip() for i in m.group(1).split(',')]
            links = []
            for qid in ids:
                r = refs_by_id.get(qid)
                if r:
                    preview = esc((r.get("question_preview") or qid)[:50])
                    url = r["url"]
                    links.append(f'<a href="{url}" target="_blank" rel="noopener">{preview}…</a>')
            if links:
                html_parts.append(
                    '<div class="ref-block">'
                    '<div class="ref-block-label">参照元 Q&A</div>'
                    + "".join(links)
                    + '</div>'
                )
            continue

        # 見出し（#, ##, ###, #### すべて対応）
        heading = re.match(r'^(#{1,4})\s+(.+)', line)
        if heading:
            level = len(heading.group(1))
            text_content = esc(heading.group(2))
            tag = "h1" if level == 1 else "h2"
            html_parts.append(f'<{tag}>{text_content}</{tag}>')
        elif line.strip() == "---":
            html_parts.append('<hr>')
        elif line.strip():
            html_parts.append(f'<p>{esc(line)}</p>')

    return "\n".join(html_parts)


def topic_to_filename(index: int) -> str:
    return f"article-{index:02d}.html"


def extract_excerpt(article_text: str) -> str:
    for line in article_text.split("\n"):
        line = line.strip()
        if line and not line.startswith("#") and not line.startswith("[") and line != "---":
            return line[:60] + ("…" if len(line) > 60 else "")
    return ""


def main():
    articles = (
        json.loads(ARTICLES_FILE.read_text("utf-8"))
        if ARTICLES_FILE.exists() else []
    )
    now = datetime.now().strftime("%Y-%m-%d")
    common = COMMON_CSS

    # 個別記事ページを生成
    list_items_html = []
    for i, a in enumerate(articles):
        topic = a.get("topic", "")
        filename = topic_to_filename(i + 1)
        qa_count = a.get("question_count", len(a.get("references", [])))
        article_body = article_to_html(a)
        excerpt = extract_excerpt(a.get("article", ""))

        page = ARTICLE_HTML
        page = page.replace("{common_css}", common).replace("{article_css}", ARTICLE_CSS)
        page = page.replace("{site_title}", SITE_TITLE)
        page = page.replace("{topic}", esc(topic))
        page = page.replace("{ref_count}", str(qa_count))
        page = page.replace("{generated_at}", a.get("generated_at", ""))
        page = page.replace("{article_body}", article_body)
        page = page.replace("{querie_url}", QUERIE_URL)
        (ROOT / filename).write_text(page, encoding="utf-8")

        date = a.get("generated_at", "")
        list_items_html.append(
            f'<a class="article-item" href="{filename}">'
            f'<div class="article-item-left">'
            f'<span class="article-topic">{esc(topic)}</span>'
            f'</div>'
            f'<span class="article-ref-count">{qa_count}件参照 / {date}</span>'
            f'</a>'
        )

    # トップ記事一覧ページ（index.html）
    index = LIST_HTML
    index = index.replace("{common_css}", common).replace("{list_css}", LIST_CSS)
    index = index.replace("{site_title}", SITE_TITLE)
    index = index.replace("{list_items}", "\n".join(list_items_html))
    index = index.replace("{querie_url}", QUERIE_URL)
    (ROOT / "index.html").write_text(index, encoding="utf-8")

    print(f"生成完了: index.html + {len(articles)}記事ページ")


if __name__ == "__main__":
    main()

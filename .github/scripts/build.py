#!/usr/bin/env python3
"""SFC 영역운동 홈페이지 생성기.

데이터:  _data/site.json      선언문, 18개 영역
         _data/areas.json     네 영역(색, 로고, 소개, 영역장 인사)
         _data/posts/*.json   게시물(스케치·홍보). 이슈 승인 시 publish.py가 만든다.
결과물:  index.html, <영역>/index.html, <영역>/<게시물>/index.html

실행:    python3 .github/scripts/build.py   (저장소 루트에서)
"""
import datetime as dt
import glob
import hashlib
import html
import json
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
IG = "https://www.instagram.com/{}/"
KST = dt.timezone(dt.timedelta(hours=9))
esc = html.escape


def load(path):
    with open(os.path.join(ROOT, path), encoding="utf-8") as f:
        return json.load(f)


SITE = load("_data/site.json")
AREAS = load("_data/areas.json")
POSTS = sorted((load(os.path.relpath(p, ROOT)) for p in glob.glob(os.path.join(ROOT, "_data/posts/*.json"))),
               key=lambda p: (p["date"], p.get("issue", 0)), reverse=True)
CSS_V = hashlib.md5(open(os.path.join(ROOT, "assets/field.css"), "rb").read()).hexdigest()[:8]
TODAY = dt.datetime.now(KST).date().isoformat()


def area_of(slug):
    return next(a for a in AREAS if a["slug"] == slug)


def date_label(d):
    y, m, day = d.split("-")
    return f"{int(y)}년 {int(m)}월 {int(day)}일"


def is_upcoming(p):
    return p["kind"] == "홍보" and p["date"] >= TODAY


SHAPES = """  <div class="hero-shapes" aria-hidden="true">
    <svg class="heart" viewBox="0 0 100 92"><path fill="#5f6db8" d="M50 90 C20 66 0 50 0 27 C0 11 12 0 27 0 C37 0 45 6 50 14 C55 6 63 0 73 0 C88 0 100 11 100 27 C100 50 80 66 50 90Z"/></svg>
    <svg class="circle" viewBox="0 0 100 100"><circle cx="50" cy="50" r="50" fill="#17269b"/></svg>
  </div>"""

IG_ICON = ('<svg class="ig" viewBox="0 0 24 24" aria-hidden="true"><rect x="3" y="3" width="18" height="18" rx="5" fill="none" '
           'stroke="currentColor" stroke-width="2"/><circle cx="12" cy="12" r="4" fill="none" stroke="currentColor" stroke-width="2"/>'
           '<circle cx="17.3" cy="6.7" r="1.2" fill="currentColor"/></svg>')


def ig_link(handle, cls="ig-link"):
    return f'<a class="{cls}" href="{IG.format(handle)}" rel="noopener">{IG_ICON}@{esc(handle)}</a>'


def head(title, desc, a, image=None):
    img = image or "https://sfc-movement.github.io/field/assets/img/field-logo.png"
    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc(title)}</title>
  <meta name="description" content="{esc(desc)}">
  <meta property="og:title" content="{esc(title)}">
  <meta property="og:description" content="{esc(desc)}">
  <meta property="og:image" content="{esc(img)}">
  <link rel="icon" href="{a}img/field-logo.png">
  <link rel="stylesheet" href="{a}field.css?v={CSS_V}">
</head>
<body>
"""


def foot(a):
    return f"""  <footer class="colophon">
    <img src="{a}img/field-logo.png" alt="" aria-hidden="true">
    <p><b>전국학생신앙운동 SFC · 영역협의체</b></p>
    <p><a href="{IG.format('sfc_yeongyeog')}" rel="noopener">@sfc_yeongyeog</a> · <a href="{a}../guide/">영역장 글쓰기 안내</a></p>
  </footer>
<div class="toast" role="status" aria-live="polite"></div>
<script>
{{
  const els = document.querySelectorAll('.reveal');
  if ('IntersectionObserver' in window) {{
    const io = new IntersectionObserver(es => es.forEach(e => {{ if (e.isIntersecting) {{ e.target.classList.add('in'); io.unobserve(e.target); }} }}), {{ threshold: .1 }});
    els.forEach(el => io.observe(el));
  }} else {{ els.forEach(el => el.classList.add('in')); }}
  if (window.matchMedia('(max-width: 640px)').matches) {{
    document.querySelectorAll('.decl').forEach((d, i) => {{ if (i > 0) d.removeAttribute('open'); }});
  }}
  const btn = document.querySelector('.copy-link');
  if (btn) btn.addEventListener('click', () => {{
    const t = document.querySelector('.toast');
    const show = m => {{ t.textContent = m; t.classList.add('show'); setTimeout(() => t.classList.remove('show'), 2400); }};
    try {{ navigator.clipboard.writeText(location.href).then(() => show('링크를 복사했어요'), () => show('주소창의 링크를 복사해 주세요')); }}
    catch (e) {{ show('주소창의 링크를 복사해 주세요'); }}
  }});
}}
</script>
</body>
</html>
"""


def thumb_of(p):
    if p.get("thumb"):
        return p["thumb"]
    return f"assets/img/shield-{p['area']}.png"


def post_card(p, prefix):
    a = area_of(p["area"])
    extra = f"<span>{esc(p['when'])}</span>" if p["kind"] == "홍보" and p.get("when") else f"<span>{date_label(p['date'])}</span>"
    return f"""    <a class="post reveal" href="{prefix}{p['path']}" style="--c:{a['color']}">
      <img class="post-thumb" src="{prefix}{thumb_of(p)}" alt="" loading="lazy">
      <span class="post-body">
        <span class="post-meta"><span class="chip">{a['name']}영역</span><span class="chip kind">{p['kind']}</span>{extra}</span>
        <span class="post-title">{esc(p['title'])}</span>
        <span class="post-sum">{esc(p['summary'])}</span>
      </span>
    </a>"""


# ───────────────────────── 홈 ─────────────────────────
def hub():
    o = [head("SFC 영역운동", "삶의 모든 영역이 하나님의 주권 아래 있음을 고백하며, 삶으로 드러내는 운동 — 의료·통일·환경·공학 영역의 소식", "assets/")]
    o.append(f"""  <header class="hero hub">
{SHAPES}
    <div class="hero-inner">
      <div class="hero-text">
        <p class="kicker">Student For Christ</p>
        <h1>영역운동</h1>
        <p class="lead">삶의 모든 영역이 하나님의 주권 아래 있음을 고백하며, 삶으로 드러내는 운동</p>
        <div class="links">{ig_link('sfc_yeongyeog', 'ig-link light')}<a class="ghost" href="#declaration">선언문 읽기 ↓</a></div>
      </div>
      <img class="hero-logo" src="assets/img/field-logo.png" alt="Student For Christ 영역운동 로고" width="414" height="420">
    </div>
  </header>
  <main>
  <section class="section">
    <div class="section-head"><h2>영역장이 세워진 네 영역</h2><p>카드를 눌러 각 영역으로 들어가 보세요</p></div>
    <div class="areas">""")
    for a in AREAS:
        n = sum(1 for p in POSTS if p["area"] == a["slug"])
        status = f"소식 {n}편" if n else "영역장 인사"
        o.append(f"""      <a class="area reveal" href="{a['slug']}/" style="--c:{a['color']}">
        <img class="area-shield" src="assets/img/shield-{a['slug']}.png" alt="" width="180" height="182" loading="lazy">
        <div class="area-body">
          <p class="area-title"><span class="area-name">{a['name']}영역</span><span class="area-code">{a['code']}</span></p>
          <p class="area-lead">{esc(a['lead'])}</p>
          <p class="area-people">{esc(a['leaders'])}</p>
          <p class="area-more">{status} →</p>
        </div>
      </a>""")
    o.append("""    </div>
  </section>""")
    upcoming = [p for p in POSTS if is_upcoming(p)]
    if upcoming:
        o.append("""  <section class="section">
    <div class="section-head"><h2>다가오는 모임</h2><p>모든 영역의 홍보</p></div>
    <div class="feed">""")
        o += [post_card(p, "") for p in sorted(upcoming, key=lambda p: p["date"])]
        o.append("    </div>\n  </section>")
    recent = [p for p in POSTS if not is_upcoming(p)][:8]
    o.append("""  <section class="section">
    <div class="section-head"><h2>최근 소식</h2><p>모든 영역의 홍보와 스케치</p></div>
    <div class="feed">""")
    if recent:
        o += [post_card(p, "") for p in recent]
    else:
        o.append('    <div class="empty"><b>아직 소식이 없어요</b>첫 글을 기다리고 있어요.</div>')
    o.append("""    </div>
  </section>
  <section class="section declaration reveal" id="declaration">
    <div class="decl-aside">
      <img src="assets/img/field-logo.png" alt="" aria-hidden="true" width="64" height="65">
      <h2>SFC 영역운동<br>선언문</h2>
      <p class="decl-sign">2025년, 영역협의체</p>
    </div>
    <div class="decl-list">""")
    for d in SITE["declaration"]:
        body = "".join(f"<p>{t}</p>" for t in d["paras"])
        o.append(f"""      <details class="decl" open>
        <summary><h3><span class="decl-num">{d['num']}.</span> {d['pre']}<mark>{d['key']}</mark>{d['post']}</h3></summary>
        <div class="decl-body">{body}</div>
      </details>""")
    o.append("""    </div>
  </section>""")
    active = {a["code"]: a for a in AREAS}
    chips = []
    for i, nm in enumerate(SITE["fields"], 1):
        code = f"F{i:02d}"
        if code in active:
            a = active[code]
            chips.append(f'<a class="fchip on" href="{a["slug"]}/" style="--c:{a["color"]}"><b>{code}</b>{nm}</a>')
        else:
            chips.append(f'<span class="fchip"><b>{code}</b>{nm}</span>')
    o.append(f"""  <section class="section">
    <div class="section-head"><h2>SFC의 열여덟 영역</h2><p>색이 있는 영역에 영역장이 세워져 있어요</p></div>
    <div class="fields reveal">{''.join(chips)}</div>
  </section>
  <section class="section">
    <div class="join reveal">
      <div>
        <h2>영역운동에 함께하고 싶다면</h2>
        <p>SFC 영역운동에 함께하고자 하는 운동원은 영역총무 대리 차수민 운동원에게 연락해 주세요. 영역협의체 인스타그램으로 메시지를 보내도 좋아요.</p>
      </div>
      <div class="links">{ig_link('sfc_yeongyeog', 'ig-link light')}</div>
    </div>
  </section>
  </main>""")
    o.append(foot("assets/"))
    return "\n".join(o)


# ───────────────────────── 영역 방 ─────────────────────────
def room(a):
    posts = [p for p in POSTS if p["area"] == a["slug"]]
    upcoming = sorted((p for p in posts if is_upcoming(p)), key=lambda p: p["date"])
    past = [p for p in posts if not is_upcoming(p)]
    o = [head(f"{a['name']}영역 · SFC 영역운동", a["lead"], "../assets/")]
    o.append(f"""  <header class="hero room" style="--band:{a['band']}">
    <div class="hero-inner">
      <img class="hero-shield" src="../assets/img/shield-{a['slug']}.png" alt="SFC {a['name']}영역 로고" width="180" height="182">
      <div class="hero-text">
        <nav class="crumb" aria-label="상위 페이지"><a href="../">영역운동</a><span aria-hidden="true">›</span><span>{a['code']} {a['name']}영역</span></nav>
        <h1>{a['name']}영역</h1>
        <p class="lead">{esc(a['lead'])}</p>
        <div class="links">{ig_link(a['ig'], 'ig-link light')}</div>
      </div>
    </div>
  </header>
  <main class="room-main" style="--c:{a['color']}">
  <aside class="room-side">
    <div class="side-card">
      <dl>
        <div><dt>영역 번호</dt><dd>{a['code']} {a['name']}영역</dd></div>
      </dl>
      <nav class="side-nav" aria-label="이 페이지 안에서 이동"><a href="#letter">영역장 인사</a><a href="#upcoming">다가오는 모임</a><a href="#past">지나온 기록</a><a href="../">← 영역운동 홈</a></nav>
    </div>
  </aside>
  <div class="room-content">""")
    msg = "\n".join(f"      <p>{t}</p>" for t in a["msg"])
    quote = ""
    if a.get("quote"):
        quote = f'\n      <blockquote><p>“{a["quote"]["text"]}”</p><cite>{a["quote"]["source"]}</cite></blockquote>'
    o.append(f"""  <section class="section" id="letter">
    <div class="section-head"><h2>영역장 인사</h2></div>
    <article class="letter reveal">
{msg}{quote}
    </article>
  </section>
  <section class="section" id="upcoming">
    <div class="section-head"><h2>다가오는 모임</h2></div>""")
    if upcoming:
        o.append('    <div class="feed">\n' + "\n".join(post_card(p, "../") for p in upcoming) + "\n    </div>")
    else:
        o.append('    <div class="empty reveal"><b>다음 모임 소식을 준비하고 있어요</b>홍보물이 올라오면 이곳에 먼저 보여요.</div>')
    o.append("""  </section>
  <section class="section" id="past">
    <div class="section-head"><h2>지나온 기록</h2></div>""")
    if past:
        o.append('    <div class="feed">\n' + "\n".join(post_card(p, "../") for p in past) + "\n    </div>")
    else:
        o.append('    <div class="empty reveal"><b>아직 기록이 없어요</b>모임이 끝나면 스케치가 이곳에 쌓여요.</div>')
    o.append("""  </section>
  <p class="back"><a href="../">← 영역운동 홈으로</a></p>
  </div>
  </main>""")
    o.append(foot("../assets/"))
    return "\n".join(o)


# ───────────────────────── 게시물 ─────────────────────────
def article_head(p, a, pre):
    kind_label = "모임 스케치" if p["kind"] == "스케치" else "모임 안내"
    return f"""  <header class="hero article" style="--band:{a['band']}">
    <div class="hero-inner">
      <div class="hero-text">
        <nav class="crumb" aria-label="상위 페이지"><a href="{pre}">영역운동</a><span aria-hidden="true">›</span><a href="{pre}{a['slug']}/">{a['name']}영역</a></nav>
        <p class="kicker">{kind_label} · {date_label(p['date'])}</p>
        <h1>{esc(p['title'])}</h1>
        <p class="lead">{esc(p['summary'])}</p>
      </div>
    </div>
  </header>"""


def article_end(p, a, pre):
    return f"""  <footer class="post-end reveal">
    <div class="links"><button type="button" class="copy-link">링크 복사</button><a class="ig-link" href="{IG.format(a['ig'])}" rel="noopener">{IG_ICON}@{esc(a['ig'])}</a></div>
    <p><a href="{pre}{a['slug']}/">← {a['name']}영역으로</a> · <a href="{pre}">영역운동 홈</a></p>
  </footer>"""


def sketch_page(p):
    a = area_of(p["area"])
    pre = "../../"
    o = [head(f"{p['title']} · {a['name']}영역", p["summary"], pre + "assets/")]
    o.append(article_head(p, a, pre))
    o.append(f'  <main class="post-main" style="--c:{a["color"]}">')
    if p.get("cover"):
        o.append(f'  <figure class="post-cover reveal"><img src="{esc(p["cover"])}" alt=""></figure>')
    for i, c in enumerate(p.get("cards", []), 1):
        o.append(f"""  <section class="pcard reveal">
    <span class="pcard-no">{i:02d}</span>
    {f'<h2>{esc(c["title"])}</h2>' if c.get("title") else ''}
    {c['html']}
  </section>""")
    if p.get("gallery"):
        imgs = "".join(f'<img src="{esc(g)}" alt="" loading="lazy">' for g in p["gallery"])
        o.append(f'  <section class="pcard gallery reveal"><h2>모임 사진</h2><div class="gallery-grid">{imgs}</div></section>')
    if p.get("share"):
        li = "".join(f"<li>{esc(q)}</li>" for q in p["share"])
        o.append(f'  <section class="pcard share reveal"><h2>함께 나눠요</h2><ol>{li}</ol></section>')
    if p.get("prayer"):
        li = "".join(f"<li>{esc(q)}</li>" for q in p["prayer"])
        o.append(f'  <section class="pcard prayer reveal"><h2>함께 기도해요</h2><ol>{li}</ol></section>')
    o.append(article_end(p, a, pre))
    o.append("  </main>")
    o.append(foot(pre + "assets/"))
    return "\n".join(o)


def promo_page(p):
    a = area_of(p["area"])
    pre = "../../"
    o = [head(f"{p['title']} · {a['name']}영역", p["summary"], pre + "assets/")]
    o.append(article_head(p, a, pre))
    o.append(f'  <main class="post-main promo" style="--c:{a["color"]}">')
    if p.get("poster"):
        o.append(f'  <figure class="post-poster reveal"><img src="{esc(p["poster"])}" alt="{esc(p["title"])} 포스터"></figure>')
    rows = []
    for label, key in (("일시", "when"), ("장소", "where"), ("문의", "contact")):
        if p.get(key):
            rows.append(f"<div><dt>{label}</dt><dd>{esc(p[key])}</dd></div>")
    apply = ""
    if p.get("apply"):
        apply = f'<a class="apply-btn" href="{esc(p["apply"])}" rel="noopener">신청하기 →</a>'
    o.append(f"""  <section class="pcard info reveal">
    <dl>{''.join(rows)}</dl>
    {apply}
  </section>""")
    if p.get("body_html"):
        o.append(f'  <section class="pcard reveal">{p["body_html"]}</section>')
    if p.get("gallery"):
        imgs = "".join(f'<img src="{esc(g)}" alt="" loading="lazy">' for g in p["gallery"])
        o.append(f'  <section class="pcard gallery reveal"><div class="gallery-grid">{imgs}</div></section>')
    o.append(article_end(p, a, pre))
    o.append("  </main>")
    o.append(foot(pre + "assets/"))
    return "\n".join(o)



# ───────────────────────── 글쓰기 안내 ─────────────────────────
NEW = "https://github.com/sfc-movement/field/issues/new?template="


def guide():
    o = [head("글 올리는 방법 · SFC 영역운동", "영역장이 홈페이지에 홍보와 스케치를 직접 올리는 방법", "../assets/")]
    o.append(f"""  <header class="hero article">
    <div class="hero-inner">
      <div class="hero-text">
        <nav class="crumb" aria-label="상위 페이지"><a href="../">영역운동</a></nav>
        <p class="kicker">영역장 안내</p>
        <h1>홈페이지에 글 올리는 방법</h1>
        <p class="lead">양식을 채우고 사진을 끌어다 놓으면, 간사님 승인 뒤 몇 분 안에 페이지가 만들어져요.</p>
      </div>
    </div>
  </header>
  <main class="post-main guide" style="--c:var(--navy)">
  <section class="pcard reveal">
    <span class="pcard-no">준비</span>
    <h2>GitHub 계정 하나만 있으면 돼요</h2>
    <p>글은 GitHub이라는 곳의 '이슈' 양식으로 올려요. 계정이 없다면 <a href="https://github.com/signup" rel="noopener">github.com/signup</a>에서 이메일로 무료 가입해 주세요. 휴대폰에서는 GitHub 앱을 깔면 더 편해요.</p>
  </section>
  <section class="pcard reveal">
    <span class="pcard-no">01</span>
    <h2>양식을 골라요</h2>
    <div class="guide-btns">
      <a class="apply-btn" href="{NEW}1-sketch.yml" rel="noopener">📸 모임 스케치 올리기</a>
      <a class="apply-btn alt" href="{NEW}2-promo.yml" rel="noopener">📣 모임 홍보 올리기</a>
      <a class="apply-btn ghosty" href="{NEW}3-greeting.yml" rel="noopener">✏️ 영역 소개·인사 바꾸기</a>
    </div>
    <ul>
      <li><strong>스케치</strong>: 이미 한 모임의 기록. 카드 여러 장으로 된 페이지가 돼요.</li>
      <li><strong>홍보</strong>: 앞으로 있을 모임. 모임 날짜가 지나면 자동으로 '지나온 기록'으로 옮겨져요.</li>
    </ul>
  </section>
  <section class="pcard reveal">
    <span class="pcard-no">02</span>
    <h2>칸을 채우고 사진을 넣어요</h2>
    <p>사진은 칸 안에 <strong>끌어다 놓거나 붙여 넣으면</strong> 돼요. 휴대폰에서는 칸을 누른 뒤 아래쪽 클립(📎) 버튼으로 사진을 고르세요.</p>
    <p>스케치의 <strong>내용 카드</strong>는 이렇게 써요. <code>##</code>으로 시작하는 줄마다 새 카드가 생겨요.</p>
    <pre>## 창조 세계는 우리의 이해를 넘어선다
하나님은 어떤 것도 똑같이 지으시지 않으셨어요.

&gt; 인상 깊은 문장은 이렇게 인용해요. (p.27)

## 우리가 할 수 있는 일
- 자가용 자제
- 텃밭 가꾸기</pre>
    <p>빈 줄은 문단 나누기, <code>- </code>는 목록, <code>**굵게**</code>는 강조예요.</p>
  </section>
  <section class="pcard reveal">
    <span class="pcard-no">03</span>
    <h2>제출하면 끝, 승인을 기다려요</h2>
    <p>맨 아래 <strong>Create</strong>(또는 Submit new issue)를 누르면 접수돼요. 간사님이 확인하고 승인하면 몇 분 안에 홈페이지에 올라가고, 이슈에 <strong>페이지 링크가 담긴 댓글</strong>이 달려요. GitHub 알림으로도 받을 수 있어요.</p>
  </section>
  <section class="pcard reveal">
    <span class="pcard-no">04</span>
    <h2>고치거나 내리고 싶을 때</h2>
    <ul>
      <li><strong>고치기</strong>: 내가 올린 이슈를 열어 본문 오른쪽 위 <code>···</code> → <strong>Edit</strong>로 고친 뒤, 간사님께 "다시 승인해 주세요"라고 댓글을 남겨요.</li>
      <li><strong>내리기</strong>: 이슈에 "내려 주세요"라고 댓글을 남기면 간사님이 내려 드려요.</li>
    </ul>
  </section>
  <section class="pcard prayer reveal" style="--c:#323c81">
    <h2>올리기 전에 꼭 확인해요</h2>
    <ol>
      <li>공개 웹페이지예요. 전화번호 같은 개인정보는 넣지 말아 주세요. 문의는 인스타그램이나 오픈채팅 링크로요.</li>
      <li>얼굴이 나온 사진은 본인 동의를 받은 것만 올려요.</li>
      <li>책 내용은 짧은 인용만, 나머지는 우리 말로 정리해요.</li>
    </ol>
  </section>
  <details class="pcard admin reveal">
    <summary><h2>관리자용: 승인하는 방법</h2></summary>
    <ul>
      <li>새 이슈가 오면 내용을 확인하고, 오른쪽 <strong>Labels</strong>에서 <code>승인</code>을 붙이면 자동으로 게시되고 이슈가 닫혀요.</li>
      <li>수정 후 다시 게시: 이슈를 다시 열고(Reopen) <code>승인</code> 라벨을 뗐다가 다시 붙여요.</li>
      <li>내리기: <code>삭제</code> 라벨을 붙여요.</li>
      <li>저장소 쓰기 권한이 있는 사람이 붙인 라벨만 처리돼요.</li>
    </ul>
  </details>
  <footer class="post-end reveal"><p><a href="../">← 영역운동 홈</a> · <a href="https://github.com/sfc-movement/field/issues" rel="noopener">올라온 글 목록(이슈)</a></p></footer>
  </main>""")
    o.append(foot("../assets/"))
    return "\n".join(o)


REDIRECT = """<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8"><title>이동 중…</title>
<link rel="canonical" href="{to}"><meta http-equiv="refresh" content="0; url={to}"></head>
<body><p><a href="{to}">새 주소로 이동합니다</a></p></body></html>
"""


def write(rel, text):
    path = os.path.join(ROOT, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def main():
    write("index.html", hub())
    write("guide/index.html", guide())
    for a in AREAS:
        write(f"{a['slug']}/index.html", room(a))
    for p in POSTS:
        if p.get("external"):
            continue
        write(p["path"] + "index.html", sketch_page(p) if p["kind"] == "스케치" else promo_page(p))
    for i in range(1, 5):  # 처음 공유된 책모임 주소 살려 두기
        write(f"environment/week{i}.html", REDIRECT.format(to=f"2026-11-bookclub/week{i}.html"))
    print(f"built: home, {len(AREAS)} areas, {len(POSTS)} posts")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""이슈에 '승인' 또는 '삭제' 라벨이 붙으면 실행된다.

- 스케치·홍보 이슈 + '승인'  → _data/posts/<slug>.json 과 사진을 만들고 사이트를 다시 생성
- 인사 수정 이슈 + '승인'    → _data/areas.json 의 소개·인사를 고치고 다시 생성
- 아무 이슈 + '삭제'          → 그 이슈로 만든 게시물을 지우고 다시 생성

라벨을 붙인 사람이 저장소 쓰기 권한(관리자)이 없으면 아무것도 하지 않는다.
결과는 GITHUB_OUTPUT(result, url, message)으로 워크플로에 넘긴다.
"""
import datetime as dt
import html
import io
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.request

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SITE_URL = "https://sfc-movement.github.io/field/"
TOKEN = os.environ.get("GITHUB_TOKEN", "")
REPO = os.environ.get("GITHUB_REPOSITORY", "sfc-movement/field")
AREA_BY_NAME = {"통일영역": "unification", "공학영역": "engineering", "의료영역": "medical", "환경영역": "environment"}
KST = dt.timezone(dt.timedelta(hours=9))
IMG_RE = re.compile(r'!\[[^\]]*\]\((https?://[^)\s]+)\)|<img[^>]*?src="(https?://[^"]+)"[^>]*>')


def out(**kv):
    path = os.environ.get("GITHUB_OUTPUT")
    lines = [f"{k}<<EOF_\n{v}\nEOF_" for k, v in kv.items()]
    if path:
        with open(path, "a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
    print("\n".join(lines))


def api(path):
    req = urllib.request.Request(f"https://api.github.com{path}",
                                 headers={"Authorization": f"Bearer {TOKEN}", "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def can_approve(user):
    if os.environ.get("SKIP_PERMISSION_CHECK") == "1":
        return True
    try:
        perm = api(f"/repos/{REPO}/collaborators/{user}/permission")["permission"]
    except Exception as e:  # noqa: BLE001
        print("permission check failed:", e)
        return False
    return perm in ("admin", "maintain", "write")


# ─────────────── 이슈 양식 읽기 ───────────────
def parse_form(body):
    fields, key, buf = {}, None, []
    for line in (body or "").replace("\r\n", "\n").split("\n"):
        m = re.match(r"^### (.+?)\s*$", line)
        if m:
            if key:
                fields[key] = "\n".join(buf).strip()
            key, buf = m.group(1).strip(), []
        else:
            buf.append(line)
    if key:
        fields[key] = "\n".join(buf).strip()
    return {k: ("" if v in ("_No response_", "None") else v) for k, v in fields.items()}


def norm_date(s, fallback):
    m = re.search(r"(\d{4})\s*[-./년]\s*(\d{1,2})\s*[-./월]\s*(\d{1,2})", s or "")
    if m:
        try:
            return dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3))).isoformat()
        except ValueError:
            pass
    return fallback


# ─────────────── 사진 받기 ───────────────
def fetch(url):
    for auth in (False, True):
        headers = {"User-Agent": "sfc-field-publisher"}
        if auth and TOKEN:
            headers["Authorization"] = f"Bearer {TOKEN}"
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=60) as r:
                return r.read()
        except Exception as e:  # noqa: BLE001
            print(f"fetch failed ({'auth' if auth else 'anon'}):", url, e)
    return None


class Images:
    """이슈 본문의 사진 주소를 받아 게시물 폴더의 img/ 에 저장하고, 새 주소를 돌려준다."""

    def __init__(self, post_dir):
        self.dir = os.path.join(post_dir, "img")
        self.n = 0
        self.map = {}

    def get(self, url):
        if url in self.map:
            return self.map[url]
        data = fetch(url)
        if not data:
            return None
        self.n += 1
        os.makedirs(self.dir, exist_ok=True)
        name = f"{self.n:02d}.jpg"
        try:
            from PIL import Image, ImageOps
            im = ImageOps.exif_transpose(Image.open(io.BytesIO(data)))
            if im.mode != "RGB":
                bg = Image.new("RGB", im.size, (255, 255, 255))
                bg.paste(im, mask=im.convert("RGBA").split()[-1] if "A" in im.getbands() else None)
                im = bg
            im.thumbnail((1600, 1600))
            im.save(os.path.join(self.dir, name), "JPEG", quality=85, optimize=True, progressive=True)
        except Exception as e:  # noqa: BLE001  (gif 등은 그대로 저장)
            print("image convert failed, saving raw:", e)
            name = f"{self.n:02d}.bin"
            open(os.path.join(self.dir, name), "wb").write(data)
        self.map[url] = f"img/{name}"
        return self.map[url]

    def all_in(self, text):
        res = []
        for m in IMG_RE.finditer(text or ""):
            p = self.get(m.group(1) or m.group(2))
            if p:
                res.append(p)
        return res


# ─────────────── 글 → HTML ───────────────
def inline(t):
    t = html.escape(t)
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"(https?://[^\s<>()\"']+)", r'<a href="\1" rel="noopener">\1</a>', t)
    return t


def blocks_to_html(text, images):
    """빈 줄로 문단을 나누고, '- ' 목록, '1. ' 번호 목록, '> ' 인용, 사진을 처리한다."""
    out_, para, lst, ltype = [], [], [], None

    def flush():
        nonlocal para, lst, ltype
        if para:
            out_.append("<p>" + "<br>".join(inline(x) for x in para) + "</p>")
            para = []
        if lst:
            tag = "ol" if ltype == "ol" else "ul"
            out_.append(f"<{tag}>" + "".join(f"<li>{inline(x)}</li>" for x in lst) + f"</{tag}>")
            lst, ltype = [], None

    for raw in (text or "").split("\n"):
        line = raw.strip()
        imgs = [m for m in IMG_RE.finditer(line)]
        if imgs:
            flush()
            for m in imgs:
                p = images.get(m.group(1) or m.group(2))
                if p:
                    out_.append(f'<img src="{p}" alt="" loading="lazy">')
            line = IMG_RE.sub("", line).strip()
            if not line:
                continue
        if not line:
            flush()
            continue
        m_ul = re.match(r"^[-*•]\s+(.*)", line)
        m_ol = re.match(r"^\d+[.)]\s+(.*)", line)
        if line.startswith(">"):
            flush()
            out_.append(f"<blockquote><p>{inline(line.lstrip('> ').strip())}</p></blockquote>")
        elif m_ul or m_ol:
            if para:
                flush()
            t = "ol" if m_ol else "ul"
            if ltype and ltype != t:
                flush()
            ltype = t
            lst.append((m_ol or m_ul).group(1))
        else:
            if lst:
                flush()
            para.append(line)
    flush()
    return "\n    ".join(out_)


def split_cards(text, images):
    cards, title, buf = [], None, []
    for line in (text or "").split("\n"):
        m = re.match(r"^\s*#{1,3}\s+(.+)$", line)
        if m:
            if title is not None or "".join(buf).strip():
                cards.append({"title": title, "html": blocks_to_html("\n".join(buf), images)})
            title, buf = m.group(1).strip(), []
        else:
            buf.append(line)
    if title is not None or "".join(buf).strip():
        cards.append({"title": title, "html": blocks_to_html("\n".join(buf), images)})
    return cards


def lines(text):
    res = []
    for l in (text or "").split("\n"):
        l = re.sub(r"^\s*(?:[-*•]|\d+[.)])\s*", "", l).strip()
        if l:
            res.append(l)
    return res


# ─────────────── 처리 ───────────────
def post_files_for(issue_no):
    d = os.path.join(ROOT, "_data/posts")
    for name in os.listdir(d):
        p = json.load(open(os.path.join(d, name), encoding="utf-8"))
        if p.get("issue") == issue_no:
            yield os.path.join(d, name), p


def remove_post(issue_no):
    removed = []
    for path, p in list(post_files_for(issue_no)):
        shutil.rmtree(os.path.join(ROOT, p["path"]), ignore_errors=True)
        os.remove(path)
        removed.append(p)
    return removed


def publish_post(issue, kind):
    f = parse_form(issue["body"])
    area = AREA_BY_NAME.get(f.get("영역", "").strip())
    if not area:
        return out(result="error", message="영역을 고르지 않아서 게시하지 못했어요. 이슈를 고친 뒤 다시 승인해 주세요.")
    title = f.get("제목", "").strip() or issue["title"]
    created = issue["created_at"][:10]
    date = norm_date(f.get("모임 날짜", ""), created)
    slug = f"{date}-{issue['number']}"
    rel = f"{area}/{slug}/"
    remove_post(issue["number"])  # 다시 승인하면 새로 만든다(수정 반영)
    post_dir = os.path.join(ROOT, rel)
    os.makedirs(post_dir, exist_ok=True)
    images = Images(post_dir)
    post = {"slug": slug, "area": area, "kind": kind, "date": date, "title": title,
            "summary": f.get("한 줄 요약", "").strip() or title, "path": rel,
            "issue": issue["number"], "author": issue["user"]["login"]}
    if kind == "스케치":
        cover = images.all_in(f.get("대표 사진", ""))
        post["cover"] = cover[0] if cover else None
        post["cards"] = split_cards(f.get("내용 카드", ""), images)
        post["gallery"] = images.all_in(f.get("모임 사진", ""))
        post["share"] = lines(f.get("나눔 질문", ""))
        post["prayer"] = lines(f.get("기도제목", ""))
        first = post["cover"] or (post["gallery"][0] if post["gallery"] else None)
    else:
        poster = images.all_in(f.get("포스터", ""))
        post["poster"] = poster[0] if poster else None
        post["when"] = f.get("일시", "").strip()
        post["where"] = f.get("장소", "").strip()
        post["apply"] = f.get("신청 링크", "").strip()
        post["contact"] = f.get("문의", "").strip()
        post["body_html"] = blocks_to_html(f.get("소개글", ""), images)
        post["gallery"] = images.all_in(f.get("추가 사진", ""))
        first = post["poster"]
    post["thumb"] = f"{rel}{first}" if first else None
    with open(os.path.join(ROOT, "_data/posts", f"{slug}.json"), "w", encoding="utf-8") as fp:
        json.dump(post, fp, ensure_ascii=False, indent=2)
    return post


def update_greeting(issue):
    f = parse_form(issue["body"])
    area = AREA_BY_NAME.get(f.get("영역", "").strip())
    if not area:
        return None
    path = os.path.join(ROOT, "_data/areas.json")
    areas = json.load(open(path, encoding="utf-8"))
    a = next(x for x in areas if x["slug"] == area)
    if f.get("한 줄 소개", "").strip():
        a["lead"] = f["한 줄 소개"].strip()
    if f.get("영역장 인사", "").strip():
        paras = [p.strip() for p in re.split(r"\n\s*\n", f["영역장 인사"]) if p.strip()]
        a["msg"] = [inline(p).replace("\n", "<br>") for p in paras]
        a.pop("quote", None)
    json.dump(areas, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    return a


def main():
    ev = json.load(open(os.environ["GITHUB_EVENT_PATH"], encoding="utf-8"))
    issue, label, sender = ev["issue"], ev["label"]["name"], ev["sender"]["login"]
    labels = {l["name"] for l in issue.get("labels", [])}
    if not can_approve(sender):
        return out(result="denied", message=f"@{sender} 님은 승인 권한이 없어서 처리하지 않았어요.")
    if label == "삭제":
        removed = remove_post(issue["number"])
        if not removed:
            return out(result="error", message="이 이슈로 만든 게시물을 찾지 못했어요.")
        subprocess.run([sys.executable, os.path.join(ROOT, ".github/scripts/build.py")], check=True)
        return out(result="deleted", url=SITE_URL, message="게시물을 내렸어요.")
    if "인사 수정" in labels:
        a = update_greeting(issue)
        if not a:
            return out(result="error", message="영역을 고르지 않아서 반영하지 못했어요.")
        subprocess.run([sys.executable, os.path.join(ROOT, ".github/scripts/build.py")], check=True)
        return out(result="updated", url=f"{SITE_URL}{a['slug']}/", message=f"{a['name']}영역 소개와 인사를 바꿨어요.")
    kind = "스케치" if "스케치" in labels else "홍보" if "홍보" in labels else None
    if not kind:
        return out(result="error", message="스케치·홍보 양식으로 만든 이슈가 아니에요.")
    post = publish_post(issue, kind)
    if not post or isinstance(post, type(None)):
        return
    subprocess.run([sys.executable, os.path.join(ROOT, ".github/scripts/build.py")], check=True)
    out(result="published", url=f"{SITE_URL}{post['path']}", message=f"「{post['title']}」을(를) 게시했어요.")


if __name__ == "__main__":
    main()

"""Pillow로 장면(PNG) 그리기. 콘텐츠는 Shorts UI에 가리지 않도록 y=220~1500 안에 배치.

화면에서 쓰는 말
  큰 글씨  = 한국어 (배우는 말)
  작은 글씨 = 가타카나 발음 / 일본어 뜻·번역 (설명하는 말)
"""
from functools import lru_cache

from PIL import Image, ImageDraw, ImageFont

from . import config as C

SAFE_TOP, SAFE_BOTTOM = 220, 1500
MARGIN = 90


@lru_cache(maxsize=64)
def font(size, bold=False):
    w, wb = ("Bold", "bd") if bold else ("Regular", "")
    for cand in C.FONT_CANDIDATES:
        if not cand:
            continue
        path = cand.format(w=w, wb=wb)
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    raise SystemExit("한글+가나를 모두 가진 폰트를 찾을 수 없습니다. fonts-noto-cjk 설치 또는 FONT_PATH 지정 필요")


def canvas():
    img = Image.new("RGB", (C.WIDTH, C.HEIGHT), C.BG)
    return img, ImageDraw.Draw(img)


def text_w(d, text, f):
    return d.textlength(text, font=f)


def wrap(d, text, f, max_w):
    """띄어쓰기가 있으면(한국어 문장) 단어 단위, 없으면(일본어·단어) 글자 단위 줄바꿈."""
    units = text.split(" ") if " " in text else list(text)
    sep = " " if " " in text else ""
    lines, cur = [], ""
    for u in units:
        trial = f"{cur}{sep}{u}" if cur else u
        if text_w(d, trial, f) <= max_w:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = u
    if cur:
        lines.append(cur)
    return lines


def center(d, text, y, f, fill=C.TEXT, max_w=None, spacing=1.25):
    """가운데 정렬로 쓰고 다음 y 반환."""
    max_w = max_w or C.WIDTH - MARGIN * 2
    for line in wrap(d, text, f, max_w):
        d.text(((C.WIDTH - text_w(d, line, f)) / 2, y), line, font=f, fill=fill)
        y += int(f.size * spacing)
    return y


def left(d, text, x, y, f, fill=C.TEXT, max_w=None, spacing=1.3):
    max_w = max_w or C.WIDTH - x - MARGIN
    for line in wrap(d, text, f, max_w):
        d.text((x, y), line, font=f, fill=fill)
        y += int(f.size * spacing)
    return y


def fit_font(d, text, max_w, start, bold=True, min_size=60):
    size = start
    while size > min_size and text_w(d, text, font(size, bold)) > max_w:
        size -= 6
    return font(size, bold)


def header(d, label, sub=None):
    d.text((MARGIN, SAFE_TOP - 90), label, font=font(44, True), fill=C.ACCENT)
    if sub:
        f = font(40)
        d.text((C.WIDTH - MARGIN - text_w(d, sub, f), SAFE_TOP - 86), sub, font=f, fill=C.SUB)
    d.line((MARGIN, SAFE_TOP - 20, C.WIDTH - MARGIN, SAFE_TOP - 20), fill=(225, 225, 225), width=3)


def progress(d, i, n, y=SAFE_BOTTOM + 10):
    gap, r = 26, 9
    total = (n - 1) * (gap + r * 2)
    x0 = (C.WIDTH - total) / 2
    for k in range(n):
        x = x0 + k * (gap + r * 2)
        fill = C.ACCENT if k < i else (C.TEXT if k == i else (215, 215, 215))
        d.ellipse((x - r, y - r, x + r, y + r), fill=fill)


# ---------------- 단어 쇼츠 ----------------

# 눈이 편한 저채도 파스텔 배경 + 같은 계열의 진한 포인트색 (Day마다 순환)
THUMB_PALETTE = [
    ((221, 233, 220), (62, 118, 88)),    # 세이지 그린
    ((220, 230, 241), (58, 98, 148)),    # 미스트 블루
    ((242, 233, 218), (160, 104, 48)),   # 샌드 베이지
    ((230, 225, 240), (106, 88, 156)),   # 라벤더 그레이
    ((243, 226, 223), (166, 82, 78)),    # 블러시 로즈
]
INK = (44, 52, 64)


def hook_word(data):
    """썸네일에 크게 걸 한국어 단어: 지정값(hook) 또는 가장 긴 단어."""
    if data.get("hook"):
        return data["hook"]
    return max((w["word"] for w in data["words"]), key=len)


BASIC_BG, BASIC_BADGE, BASIC_POINT = (225, 238, 248), (247, 201, 72), (52, 110, 170)


def is_basic(data):
    return data.get("series") == "basic"


def day_label(data):
    return f"初心者 Day {data['day']}" if is_basic(data) else f"Day {data['day']}"


def vocab_intro(data):
    """썸네일 겸 인트로. Day마다 색이 바뀌어 채널 그리드에서 구분되고, 레이아웃은 고정(브랜딩)."""
    if is_basic(data):
        return basic_intro(data)
    bg, point = THUMB_PALETTE[(data["day"] - 1) % len(THUMB_PALETTE)]
    white = (255, 255, 255)
    img = Image.new("RGB", (C.WIDTH, C.HEIGHT), bg)
    d = ImageDraw.Draw(img)
    # Day 배지
    f = font(64, True)
    label = f"Day {data['day']}"
    w = text_w(d, label, f)
    d.rounded_rectangle(((C.WIDTH - w) / 2 - 40, 380, (C.WIDTH + w) / 2 + 40, 490), 55, fill=point)
    d.text(((C.WIDTH - w) / 2, 392), label, font=f, fill=white)
    # 메인 카피 (일본어)
    copy = "韓国語の単語"
    y = center(d, copy, 550, fit_font(d, copy, C.WIDTH - MARGIN * 2, 130, min_size=90), INK)
    y = center(d, f"{len(data['words'])}個", y - 10, font(230, True), point)
    # 훅 단어 카드 (옅은 그림자)
    hw = hook_word(data)
    top = y + 40
    shadow = tuple(max(c - 14, 0) for c in bg)
    d.rounded_rectangle((MARGIN, top + 10, C.WIDTH - MARGIN, top + 510), 50, fill=shadow)
    d.rounded_rectangle((MARGIN, top, C.WIDTH - MARGIN, top + 500), 50, fill=white)
    hf = fit_font(d, hw, C.WIDTH - MARGIN * 2 - 80, 200)
    center(d, hw, top + 50 + (200 - hf.size) // 2, hf, INK)
    center(d, "読める？", top + 360, font(72, True), point)
    if data.get("theme"):
        center(d, f"#{data['theme']}", top + 560, font(60, True), point)
    return img


def basic_intro(data):
    """왕초보(初心者) 시리즈 썸네일 겸 인트로: 고정 색(하늘색 배경 + 노란 배지)으로 기존 시리즈와 구분."""
    white = (255, 255, 255)
    img = Image.new("RGB", (C.WIDTH, C.HEIGHT), BASIC_BG)
    d = ImageDraw.Draw(img)
    f = font(64, True)
    label = day_label(data)
    w = text_w(d, label, f)
    d.rounded_rectangle(((C.WIDTH - w) / 2 - 40, 380, (C.WIDTH + w) / 2 + 40, 490), 55, fill=BASIC_BADGE)
    d.text(((C.WIDTH - w) / 2, 392), label, font=f, fill=INK)
    copy = "はじめての韓国語"
    y = center(d, copy, 550, fit_font(d, copy, C.WIDTH - MARGIN * 2, 118, min_size=80), INK)
    y = center(d, f"{len(data['words'])}個", y - 10, font(230, True), BASIC_POINT)
    hw = hook_word(data)
    top = y + 40
    shadow = tuple(max(c - 14, 0) for c in BASIC_BG)
    d.rounded_rectangle((MARGIN, top + 10, C.WIDTH - MARGIN, top + 510), 50, fill=shadow)
    d.rounded_rectangle((MARGIN, top, C.WIDTH - MARGIN, top + 500), 50, fill=white)
    hf = fit_font(d, hw, C.WIDTH - MARGIN * 2 - 80, 200)
    center(d, hw, top + 50 + (200 - hf.size) // 2, hf, INK)
    center(d, "ひとつずつ ゆっくり！", top + 360, font(72, True), BASIC_POINT)
    if data.get("theme"):
        center(d, f"#{data['theme']}", top + 560, font(60, True), BASIC_POINT)
    return img


def _word_block(d, w, reveal, show_reading=False):
    """가타카나 발음(위, 작게) + 한국어 단어(아래, 크게)."""
    word_f = fit_font(d, w["word"], C.WIDTH - MARGIN * 2, 240)
    y = 640
    if (reveal or show_reading) and w["reading"] != w["word"]:
        center(d, w["reading"], y - 110, font(72), C.ACCENT)
    elif not reveal and not show_reading:
        center(d, "？？？", y - 110, font(72), (200, 200, 200))
    center(d, w["word"], y, word_f)
    return y + word_f.size + 90


def vocab_quiz(data, i, count):
    w = data["words"][i]
    img, d = canvas()
    header(d, f"{day_label(data)} 単語", f"{i + 1} / {len(data['words'])}")
    # 왕초보: 가타카나 발음을 처음부터 보여주고 뜻만 묻기
    y = _word_block(d, w, reveal=False, show_reading=is_basic(data))
    q = "意味は？" if (w["reading"] == w["word"] or is_basic(data)) else "読み方と意味は？"
    center(d, q, y, font(64, True), C.SUB)
    # 카운트다운 원
    cx, cy, r = C.WIDTH // 2, y + 300, 110
    d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=C.ACCENT, width=12)
    f = font(130, True)
    s = str(count)
    d.text((cx - text_w(d, s, f) / 2, cy - f.size * 0.62), s, font=f, fill=C.ACCENT)
    progress(d, i, len(data["words"]))
    return img


CTA_TEXT = "チャンネル登録で毎日韓国語を勉強できます"       # 구독 유도 (홀수 Day)
CTA_TEXT_ALT = "今日は何個わかった？コメントで教えてね"      # 댓글 유도 (짝수 Day)


def cta_text(data):
    """마지막 배너 문구. Day 홀짝으로 구독 유도 / 댓글 유도를 번갈아 쓴다."""
    return CTA_TEXT if data["day"] % 2 == 1 else CTA_TEXT_ALT


def cta_banner(d, y=SAFE_BOTTOM - 10, text=CTA_TEXT):
    """화면 하단 구독 유도 배너 (Shorts UI에 가리지 않는 위치)."""
    f = font(40, True)
    w = text_w(d, text, f)
    pad_x, h = 40, 86
    x0 = (C.WIDTH - w) / 2 - pad_x
    d.rounded_rectangle((x0, y, x0 + w + pad_x * 2, y + h), h // 2, fill=C.ACCENT)
    d.text(((C.WIDTH - w) / 2, y + (h - f.size) / 2 - 6), text, font=f, fill=(255, 255, 255))


def vocab_reveal(data, i, cta=False):
    w = data["words"][i]
    img, d = canvas()
    header(d, f"{day_label(data)} 単語", f"{i + 1} / {len(data['words'])}")
    y = _word_block(d, w, reveal=True)
    y = center(d, w["meaning"], y, font(84, True))
    if w.get("example"):
        box_top = y + 60
        d.rounded_rectangle((MARGIN - 20, box_top, C.WIDTH - MARGIN + 20, box_top + 300), 30, fill=C.CARD)
        yy = center(d, w["example"], box_top + 50, font(54), max_w=C.WIDTH - MARGIN * 2 - 40)
        center(d, w.get("example_ja", ""), yy + 10, font(42), C.SUB, max_w=C.WIDTH - MARGIN * 2 - 40)
    if cta:
        cta_banner(d)
    else:
        progress(d, i + 1, len(data["words"]))
    return img


def vocab_review(data, cta=False):
    """마지막 복습 화면: 한 장에 전부. 캡처/일시정지 유도."""
    img, d = canvas()
    header(d, f"{day_label(data)} 復習", "スクショして覚える")
    words = data["words"]
    row_h = min(120, (SAFE_BOTTOM - SAFE_TOP) // max(len(words), 1))
    y = SAFE_TOP + 20
    fw, fr, fm = font(int(row_h * 0.46), True), font(int(row_h * 0.30)), font(int(row_h * 0.36))
    for k, w in enumerate(words, 1):
        d.text((MARGIN, y), f"{k:>2}", font=fr, fill=C.ACCENT)
        d.text((MARGIN + 70, y - 4), w["word"], font=fw, fill=C.TEXT)
        if w["reading"] != w["word"]:
            d.text((MARGIN + 70, y + fw.size + 8), w["reading"], font=fr, fill=C.SUB)
        m, fm_row = w["meaning"], fm
        # 긴 뜻은 먼저 글자를 줄여서 끼워 넣고, 그래도 안 되면 그때 잘라낸다
        while text_w(d, m, fm_row) > 420 and fm_row.size > int(row_h * 0.26):
            fm_row = font(fm_row.size - 2)
        while text_w(d, m, fm_row) > 420 and len(m) > 1:
            m = m[:-2] + "…"
        d.text((C.WIDTH - MARGIN - text_w(d, m, fm_row), y + 6), m, font=fm_row, fill=C.TEXT)
        y += row_h
    if cta:
        cta_banner(d, y=SAFE_BOTTOM - 20, text=cta_text(data))
    else:
        center(d, f"明日は Day {data['day'] + 1} · 登録して毎日復習！", SAFE_BOTTOM + 10, font(44, True), C.ACCENT)
    return img


# ---------------- 문법 쇼츠 (예비: content/queue/grammar_*.json) ----------------

def grammar_title(data):
    img, d = canvas()
    header(d, f"今日の文法 Day {data['day']}", data.get("level", C.LEVEL))
    y = 560
    y = center(d, data["title"], y, fit_font(d, data["title"], C.WIDTH - MARGIN * 2, 200))
    y = center(d, data["meaning"], y + 50, font(72, True), C.ACCENT)
    box = y + 70
    d.rounded_rectangle((MARGIN - 20, box, C.WIDTH - MARGIN + 20, box + 200), 30, fill=C.CARD)
    center(d, "接続", box + 30, font(40), C.SUB)
    center(d, data["form"], box + 90, font(54, True), max_w=C.WIDTH - MARGIN * 2 - 40)
    return img


def grammar_example(data, i):
    ex = data["examples"][i]
    img, d = canvas()
    header(d, data["title"], f"例文 {i + 1} / {len(data['examples'])}")
    y = 620
    if ex.get("reading"):
        y = center(d, ex["reading"], y, font(44), C.SUB)
    y = center(d, ex["ko"], y + 20, fit_font(d, ex["ko"], C.WIDTH - MARGIN * 2, 84, min_size=60))
    center(d, ex["ja"], y + 60, font(58), C.ACCENT)
    return img


def grammar_summary(data):
    """흰 배경 한 장 요약 (참고사항 포함). 마지막에 오래 보여주고 저장 유도."""
    img, d = canvas()
    header(d, f"今日の文法 Day {data['day']}", "保存して復習")
    y = SAFE_TOP + 40
    y = left(d, data["title"], MARGIN, y, font(96, True))
    y = left(d, data["meaning"], MARGIN, y + 10, font(54, True), C.ACCENT)
    y = left(d, f"接続 | {data['form']}", MARGIN, y + 20, font(44), C.SUB)
    y += 40
    for k, ex in enumerate(data["examples"], 1):
        y = left(d, f"{k}. {ex['ko']}", MARGIN, y, font(56, True))
        y = left(d, ex["ja"], MARGIN + 56, y, font(46), C.SUB) + 24
    if data.get("note"):
        y += 10
        d.rounded_rectangle((MARGIN - 20, y, C.WIDTH - MARGIN + 20, min(y + 360, SAFE_BOTTOM + 60)), 30, fill=C.CARD)
        yy = left(d, "ポイント", MARGIN + 10, y + 25, font(46, True), C.ACCENT)
        left(d, data["note"], MARGIN + 10, yy, font(46), max_w=C.WIDTH - MARGIN * 2 - 20)
    return img

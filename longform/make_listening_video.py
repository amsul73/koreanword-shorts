"""한국어 단어 듣기 반복 롱폼 영상 생성 (1920x1080) — 일본인 학습자용.

흐름
  1. 타이틀 카드 + 일본어 인트로 음성
  2. 단어마다: 단어 카드(한국어 → 일본어 뜻 → 한국어 느리게) → 예문 3개
  3. 예문마다: [화면1] 일본어 문장 + 일본어 음성 → 생각할 시간(카운트다운)
              → [화면2] 한국어 문장(hl 노란 형광펜) + 가타카나 발음 → 선희(보통) → 1초 → 인준(-15%)
  4. 아웃트로: 10단어 복습 화면 + 단어/뜻 음성

사용법
  python make_listening_video.py days/day01.json              # mp4 + description.txt
  python make_listening_video.py days/                         # 폴더 안 json 전부 (배치)
  python make_listening_video.py days/day01.json --preview     # 화면 이미지만
  python make_listening_video.py days/day01.json --tts dummy   # 무음 테스트
  python make_listening_video.py days/day01.json --check       # JSON 검증만
  python make_listening_video.py days/ --daily --history ../data/history.json   # 다음 Day 1개만 (자동화용)
  옵션: --loops N (단어+예문 파트 N회 반복), --think 초 (생각 시간, 기본 3), --out 폴더
"""
import argparse
import asyncio
import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
import re
import wave
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H, FPS, SR = 1920, 1080, 30, 44100
LAST_ENGINE = "edge"
SAMPLES_PER_FRAME = SR // FPS  # 1470 → 장면 길이를 프레임 단위로 맞춰 싱크 밀림 방지

# 색상: 눈이 편한 오프화이트 배경
BG = (246, 244, 239)
INK = (38, 42, 50)
SUB = (122, 126, 134)
ACCENT = (58, 98, 148)
MARK = (255, 222, 122)       # hl 형광펜
CARD = (255, 255, 255)
LINE = (226, 222, 214)

VOICE_KO = "ko-KR-SunHiNeural"     # 배우는 말(한국어) 메인
VOICE_KO2 = "ko-KR-InJoonNeural"   # 한국어 두 번째 목소리(남성) — 반복용
VOICE_JA = "ja-JP-NanamiNeural"    # 설명하는 말(일본어)

# 한글 + 가나/한자를 모두 가진 폰트가 필요 (Noto Sans CJK 권장)
_NOTO = {
    True: ["/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
           "/usr/share/fonts/noto-cjk/NotoSansCJK-Bold.ttc"],
    False: ["/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc"],
}
FONTS = {
    ("ko", True): _NOTO[True] + ["C:/Windows/Fonts/malgunbd.ttf", "/System/Library/Fonts/AppleSDGothicNeo.ttc"],
    ("ko", False): _NOTO[False] + ["C:/Windows/Fonts/malgun.ttf", "/System/Library/Fonts/AppleSDGothicNeo.ttc"],
    ("ja", True): _NOTO[True] + ["C:/Windows/Fonts/YuGothB.ttc", "C:/Windows/Fonts/meiryob.ttc",
                                 "/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc"],
    ("ja", False): _NOTO[False] + ["C:/Windows/Fonts/YuGothM.ttc", "C:/Windows/Fonts/meiryo.ttc",
                                   "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc"],
}
KO_MIN, KO_MAX = 56, 92      # 한국어 예문 폰트 범위 (최소까지 줄어들면 검증 경고)

# reading 필드는 가타카나(+장음 ー, 중점 ・, 공백)만 허용
KATAKANA_RE = re.compile(r"^[\u30A0-\u30FF\u31F0-\u31FF ]+$")


@lru_cache(maxsize=None)
def font(lang, size, bold=True):
    for p in FONTS[(lang, bold)]:
        try:
            return ImageFont.truetype(p, size)
        except OSError:
            continue
    sys.exit(f"{lang} 폰트를 찾을 수 없습니다: {FONTS[(lang, bold)]}")


# ---------------------------------------------------------------- 화면

def canvas():
    img = Image.new("RGB", (W, H), BG)
    return img, ImageDraw.Draw(img)


def tw(d, t, f):
    return d.textlength(t, font=f)


def center(d, text, y, f, fill=INK, max_w=W - 240):
    """가운데 정렬(줄바꿈 포함), 다음 y 반환."""
    units, sep = (text.split(" "), " ") if " " in text else (list(text), "")
    lines, cur = [], ""
    for u in units:
        t = f"{cur}{sep}{u}" if cur else u
        if tw(d, t, f) <= max_w or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = u
    lines.append(cur)
    for ln in lines:
        d.text(((W - tw(d, ln, f)) / 2, y), ln, font=f, fill=fill)
        y += int(f.size * 1.3)
    return y


def header(d, left, right=""):
    d.text((90, 56), left, font=font("ko", 40), fill=ACCENT)
    if right:
        f = font("ja", 36, False)
        d.text((W - 90 - tw(d, right, f), 60), right, font=f, fill=SUB)
    d.line((90, 124, W - 90, 124), fill=LINE, width=3)


def ko_size(text, max_w=W - 260):
    """한국어 예문을 한 줄에 넣을 수 있는 폰트 크기. 최소 크기면 2줄로 나눔."""
    d = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    s = KO_MAX
    while s > KO_MIN and tw(d, text, font("ko", s)) > max_w:
        s -= 4
    return s


def draw_highlighted(d, text, hl, y, size, max_w=W - 260):
    """hl 부분에 노란 형광펜을 칠해 가운데 정렬로 그림. 다음 y 반환.
    한국어는 띄어쓰기 단위로 줄을 나눠 단어가 중간에 끊기지 않게 한다."""
    f = font("ko", size)
    start = text.find(hl) if hl else -1
    pairs = [(c, start <= i < start + len(hl) if start >= 0 else False) for i, c in enumerate(text)]
    if " " in text:
        tokens, cur = [], []
        for p in pairs:
            cur.append(p)
            if p[0] == " ":
                tokens.append(cur)
                cur = []
        if cur:
            tokens.append(cur)
    else:
        tokens = [[p] for p in pairs]
    lines, cur = [], []
    for tk in tokens:
        trial = cur + tk
        if cur and tw(d, "".join(c for c, _ in trial).rstrip(), f) > max_w:
            lines.append(cur)
            cur = tk
        else:
            cur = trial
    if cur:
        lines.append(cur)
    for ln in lines:
        while ln and ln[-1][0] == " ":
            ln = ln[:-1]
        s = "".join(c for c, _ in ln)
        x = (W - tw(d, s, f)) / 2
        for ch, fl in ln:
            cw = tw(d, ch, f)
            if fl:
                d.rectangle((x - 1, y + size * 0.55, x + cw + 1, y + size * 1.22), fill=MARK)
            x += cw
        d.text(((W - tw(d, s, f)) / 2, y), s, font=f, fill=INK)
        y += int(size * 1.45)
    return y


def scr_title(data):
    img, d = canvas()
    y = center(d, f"Day {data['day']}", 320, font("ja", 72), ACCENT)
    y = center(d, data["theme"], y + 10, font("ja", 120))
    n_w = len(data["words"])
    n_s = sum(len(w["examples"]) for w in data["words"])
    y = center(d, f"韓国語リスニング反復 · 単語{n_w}個 · 例文{n_s}文", y + 30, font("ja", 48, False), SUB)
    center(d, "流しながら 一緒に 声に出してみましょう", y + 90, font("ja", 44), ACCENT)
    return img


def scr_word(data, i):
    """단어 카드: 가타카나 발음(위) + 한국어 단어(크게) + 일본어 뜻."""
    w = data["words"][i]
    img, d = canvas()
    header(d, f"Day {data['day']} · {data['theme']}", f"単語 {i + 1} / {len(data['words'])}")
    if w["reading"] != w["word"]:
        center(d, w["reading"], 300, font("ja", 64, False), ACCENT)
    center(d, w["word"], 390, font("ko", 200))
    center(d, w["meaning"], 680, font("ja", 80), INK)
    return img


def scr_prompt(data, i, k, count=None, think=3):
    """문제 화면: 일본어 문장을 보여주고 한국어로 말해 보게 한다."""
    w, ex = data["words"][i], data["words"][i]["examples"][k]
    img, d = canvas()
    header(d, f"{w['word']}  {w['meaning']}", f"例文 {k + 1} / {len(w['examples'])}")
    center(d, ex["ja"], 440, font("ja", 76))
    if count is None:
        center(d, "韓国語でどう言いますか？", 680, font("ja", 44, False), SUB)
    else:
        center(d, "考えてみましょう", 660, font("ja", 44, False), SUB)
        # 남은 시간 점
        r, gap = 16, 30
        x0 = (W - (think - 1) * (2 * r + gap)) / 2
        for n in range(think):
            x = x0 + n * (2 * r + gap)
            fill = ACCENT if n < count else LINE
            d.ellipse((x - r, 770 - r, x + r, 770 + r), fill=fill)
    return img


def scr_answer(data, i, k):
    """정답 화면: 가타카나 발음 + 한국어 문장(형광펜) + 일본어 번역."""
    w, ex = data["words"][i], data["words"][i]["examples"][k]
    img, d = canvas()
    header(d, f"{w['word']}  {w['meaning']}", f"例文 {k + 1} / {len(w['examples'])}")
    size = ko_size(ex["ko"])
    y = 400 if size > KO_MIN else 340
    y = center(d, ex["reading"], y, font("ja", 44, False), SUB)
    y = draw_highlighted(d, ex["ko"], ex.get("hl", ""), y + 30, size)
    center(d, ex["ja"], y + 50, font("ja", 48, False), SUB)
    return img


def scr_review(data):
    img, d = canvas()
    header(d, f"Day {data['day']} 復習 · {data['theme']}", "今日の単語")
    words = data["words"]
    rows = math.ceil(len(words) / 2)
    row_h = min(150, (H - 220) // rows)
    for n, w in enumerate(words):
        col, row = divmod(n, rows)
        x = 130 + col * 860
        y = 170 + row * row_h
        d.text((x, y + 8), f"{n + 1}", font=font("ja", 36), fill=ACCENT)
        d.text((x + 70, y), w["word"], font=font("ko", 56), fill=INK)
        if w["reading"] != w["word"]:
            d.text((x + 70, y + 72), w["reading"], font=font("ja", 30, False), fill=SUB)
        f = font("ja", 42, False)
        d.text((x + 780 - tw(d, w["meaning"], f), y + 10), w["meaning"], font=f, fill=INK)
    return img


# ---------------------------------------------------------------- 음성

class TTS:
    def __init__(self, mode, cache_dir):
        self.mode, self.cache = mode, Path(cache_dir)
        self.cache.mkdir(parents=True, exist_ok=True)
        self.files = {}   # (text, voice, rate) -> wav path (음성 점검 목록용)

    def wav(self, text, voice, rate="+0%"):
        key = hashlib.md5(f"{self.mode}|{voice}|{rate}|{text}".encode()).hexdigest()[:16]
        out = self.cache / f"{key}.wav"
        if not out.exists():
            if self.mode == "dummy":
                dur = max(0.6, 0.11 * len(text))
                subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                                f"anullsrc=r={SR}:cl=stereo", "-t", f"{dur:.2f}", str(out)], check=True)
            else:
                mp3 = out.with_suffix(".mp3")
                self._edge(text, voice, rate, mp3)
                # 첫소리(모음 시작 단어)가 잘리지 않게 낮은 기준 + 0.08초 여유 유지
                trim = "silenceremove=start_periods=1:start_threshold=-60dB:start_silence=0.08"
                subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(mp3), "-af",
                                f"{trim},areverse,{trim},areverse", "-ar", str(SR), "-ac", "2",
                                "-sample_fmt", "s16", str(out)], check=True)
        self.files[(text, voice, rate)] = out
        return out

    def _edge(self, text, voice, rate, path, tries=3):
        """edge-tts로 시도 → 계속 실패하면 이 영상은 끝까지 gTTS(무료 구글 음성)로 전환."""
        if getattr(self, "engine", "edge") == "edge":
            import time
            import edge_tts
            for t in range(tries):
                try:
                    asyncio.run(edge_tts.Communicate(text, voice, rate=rate).save(str(path)))
                    return
                except Exception as e:
                    err = e
                    time.sleep(2 * (t + 1))
            if os.environ.get("TTS_STRICT") == "1":   # 재생성 모드: 대체 음성 금지
                raise RuntimeError(f"edge-tts 실패: {err}")
            print(f"::warning::edge-tts 실패({type(err).__name__}: {str(err)[:80]}) → 이 영상은 gTTS 음성으로 대체합니다")
            self.engine = "gtts"
        from gtts import gTTS
        slow = rate.startswith("-") and int(rate.strip("-%") or 0) >= 15
        gTTS(text, lang=voice[:2], slow=slow).save(str(path))


def read_pcm(path):
    with wave.open(str(path), "rb") as w:
        assert w.getframerate() == SR and w.getnchannels() == 2 and w.getsampwidth() == 2, path
        return w.readframes(w.getnframes())


def silence(sec):
    return b"\x00\x00\x00\x00" * int(SR * sec)


# ---------------------------------------------------------------- 조립

def build(data, think=3, loops=1):
    """[(image, [audio items]), ...] 와 챕터 목록 생성. item: ('tts', text, voice, rate) | ('sil', sec)"""
    segs, chapters = [], []

    def add(img, items, chapter=None):
        if chapter:
            chapters.append((len(segs), chapter))
        segs.append((img, items))

    n = len(data["words"])
    add(scr_title(data), [("sil", 0.5),
        ("tts", f"Day {data['day']}、{data['theme']}。今日の韓国語の単語{n}個を、例文と一緒に聞いてみましょう。"
                "日本語の文を聞いて、韓国語で先に言ってみてください。", VOICE_JA, "+0%"), ("sil", 1.0)], "イントロ")

    for loop in range(loops):
        for i, w in enumerate(data["words"]):
            label = f"{i + 1}. {w['word']} ({w['meaning']})"
            if loops > 1:
                label = f"[{loop + 1}回目] " + label
            # 단어 카드: 한글은 표음문자라 word를 그대로 읽는다 (가타카나로 읽히지 않게)
            add(scr_word(data, i), [("sil", 0.4), ("tts", w["word"], VOICE_KO, "+0%"), ("sil", 0.7),
                                    ("tts", w["meaning"], VOICE_JA, "+0%"), ("sil", 0.7),
                                    ("tts", w["word"], VOICE_KO, "-30%"), ("sil", 1.0)], label)
            for k, ex in enumerate(w["examples"]):
                add(scr_prompt(data, i, k), [("sil", 0.3), ("tts", ex["ja"], VOICE_JA, "+0%"), ("sil", 0.3)])
                for c in range(think, 0, -1):
                    add(scr_prompt(data, i, k, count=c, think=think), [("sil", 1.0)])
                add(scr_answer(data, i, k), [("sil", 0.2), ("tts", ex["ko"], VOICE_KO, "+0%"), ("sil", 1.0),
                                             ("tts", ex["ko"], VOICE_KO2, "-15%"), ("sil", 1.2)])

    items = [("sil", 0.5), ("tts", "今日覚えた単語をもう一度聞いてみましょう。", VOICE_JA, "+0%"), ("sil", 0.8)]
    for w in data["words"]:
        items += [("tts", w["word"], VOICE_KO, "+0%"), ("sil", 0.4),
                  ("tts", w["meaning"], VOICE_JA, "+0%"), ("sil", 0.9)]
    add(scr_review(data), items + [("sil", 1.5)], "復習")
    return segs, chapters


def fmt_ts(sec):
    sec = int(sec)
    h, m, s = sec // 3600, sec % 3600 // 60, sec % 60
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def render(data, out_dir, tts_mode="edge", think=3, loops=1, preview=False):
    stem = f"day{data['day']:02d}_listening"
    work = out_dir / f"{stem}_work"
    work.mkdir(parents=True, exist_ok=True)
    tts = TTS(tts_mode, out_dir / "tts_cache")
    global LAST_ENGINE
    segs, chapters = build(data, think, loops)

    if preview:
        # 장면 종류별 대표 이미지만 저장
        pv = out_dir / f"{stem}_preview"
        pv.mkdir(parents=True, exist_ok=True)
        seen = set()
        for n, (img, _) in enumerate(segs):
            sig = img.tobytes()[::9973]
            if sig in seen:
                continue
            seen.add(sig)
            img.save(pv / f"{n:03d}.png")
        print(f"미리보기 이미지 {len(seen)}장: {pv}")
        return pv

    pcm, starts, lst = bytearray(), [], []
    for n, (img, items) in enumerate(segs):
        starts.append(len(pcm) // 4 / SR)
        seg = bytearray()
        for it in items:
            seg += silence(it[1]) if it[0] == "sil" else read_pcm(tts.wav(*it[1:]))
        frames = math.ceil(len(seg) / 4 / SAMPLES_PER_FRAME)
        seg += b"\x00" * (frames * SAMPLES_PER_FRAME * 4 - len(seg))
        pcm += seg
        p = work / f"s{n:04d}.png"
        img.save(p)
        lst.append(f"file '{p.name}'\nduration {frames / FPS:.6f}\n")
        if n % 20 == 0:
            print(f"  장면 {n + 1}/{len(segs)}")
    lst.append(f"file 's{len(segs) - 1:04d}.png'\n")
    (work / "list.txt").write_text("".join(lst), encoding="utf-8")
    with wave.open(str(work / "audio.wav"), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(bytes(pcm))

    mp4 = out_dir / f"{stem}.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
                    "-i", str(work / "list.txt"), "-i", str(work / "audio.wav"),
                    "-c:v", "libx264", "-tune", "stillimage", "-preset", "medium", "-r", str(FPS),
                    "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-shortest",
                    "-movflags", "+faststart", str(mp4)], check=True)
    total = len(pcm) / 4 / SR

    # description.txt (유튜브 챕터) — 일본인 시청자용이라 일본어
    lines = [f"韓国語リスニング反復 Day {data['day']} | {data['theme']} | 流して覚える韓国語", "",
             "[チャプター]"]
    lines += [f"{fmt_ts(starts[i])} {label}" for i, label in chapters]
    lines += ["", "[今日の単語]"] + [f"{w['word']} ({w['reading']}) - {w['meaning']}" for w in data["words"]]
    lines += ["", "#韓国語 #韓国語リスニング #韓国語単語 #TOPIK #韓国語勉強"]
    (out_dir / f"{stem}_description.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

    # 음성 점검용: 숫자(수사 읽기)·단어 카드 음성 파일 모음
    if tts_mode == "edge":
        chk = out_dir / f"{stem}_tts_check"
        chk.mkdir(exist_ok=True)
        rows = []
        for (text, voice, rate), path in tts.files.items():
            if voice == VOICE_JA:
                continue
            reasons = []
            if any(c.isdigit() for c in text):
                reasons.append("숫자")
            if any(text == w["word"] for w in data["words"]):
                reasons.append("단어카드")
            if reasons:
                name = f"{len(rows) + 1:02d}_{voice.split('-')[2][:-6]}{'' if rate == '+0%' else rate}.wav"
                shutil.copy(path, chk / name)
                rows.append(f"{name}\t{'/'.join(reasons)}\t{text}")
        (chk / "list.txt").write_text("파일\t확인 이유\t문장\n" + "\n".join(rows) + "\n", encoding="utf-8")

    shutil.rmtree(work, ignore_errors=True)
    LAST_ENGINE = getattr(tts, "engine", "edge") if tts_mode == "edge" else tts_mode
    print(f"완성: {mp4}  ({fmt_ts(total)}, 장면 {len(segs)}개, 챕터 {len(chapters)}개)")
    return mp4


# ---------------------------------------------------------------- 검증

def validate(data, name=""):
    """문제 목록 반환 (빈 목록이면 통과)."""
    issues = []
    for k in ("day", "theme", "words"):
        if k not in data:
            issues.append(f"필수 필드 없음: {k}")
    for i, w in enumerate(data.get("words", []), 1):
        for k in ("word", "reading", "meaning", "examples"):
            if not w.get(k):
                issues.append(f"단어 {i}: {k} 없음")
        if w.get("reading") and not KATAKANA_RE.match(w["reading"]):
            issues.append(f"단어 {i}({w.get('word')}): reading이 가타카나가 아님 → {w['reading']}")
        for j, ex in enumerate(w.get("examples", []), 1):
            tag = f"단어 {i}({w.get('word')}) 예문 {j}"
            for k in ("ko", "reading", "ja", "hl"):
                if not ex.get(k):
                    issues.append(f"{tag}: {k} 없음")
            if ex.get("reading") and not KATAKANA_RE.match(ex["reading"]):
                issues.append(f"{tag}: reading이 가타카나가 아님 → {ex['reading']}")
            if ex.get("hl") and ex.get("ko") and ex["hl"] not in ex["ko"]:
                issues.append(f"{tag}: hl '{ex['hl']}'이 한국어 문장에 없음")
            if ex.get("ko") and ko_size(ex["ko"]) <= KO_MIN:
                issues.append(f"{tag}: 문장이 길어 최소 폰트로 줄어듦/줄바꿈 ({len(ex['ko'])}자)")
    return [f"{name}: {m}" if name else m for m in issues]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src", help="day JSON 파일 또는 JSON이 든 폴더")
    ap.add_argument("--out", default="output")
    ap.add_argument("--tts", choices=["edge", "dummy"], default="edge")
    ap.add_argument("--think", type=int, default=3)
    ap.add_argument("--loops", type=int, default=1)
    ap.add_argument("--preview", action="store_true")
    ap.add_argument("--check", action="store_true", help="JSON 검증만")
    ap.add_argument("--daily", action="store_true", help="history의 다음 Day 하나만 렌더하고 기록")
    ap.add_argument("--history", default="data/history.json")
    a = ap.parse_args()

    src = Path(a.src)
    files = sorted(src.glob("*.json")) if src.is_dir() else [src]
    if a.daily:
        hist_path = Path(a.history)
        hist = json.loads(hist_path.read_text(encoding="utf-8")) if hist_path.exists() else {}
        nxt = hist.get("longform_day", 0) + 1
        f = src / f"day{nxt:02d}.json"
        left = len([p for p in files if int(p.stem[3:] or 0) >= nxt])
        if not f.exists():
            print(f"::warning::롱폼 Day {nxt} JSON이 없습니다 ({f}). Claude에게 다음 롱폼 예문을 요청하세요.")
            return
        if left - 1 <= 3:
            print(f"::warning::롱폼 JSON이 {left - 1}일치 남았습니다. Claude에게 다음 배치를 요청하세요.")
        files = [f]
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    bad = False
    for f in files:
        data = json.loads(f.read_text(encoding="utf-8"))
        issues = validate(data, f.name)
        for m in issues:
            print("  ⚠", m)
        bad |= bool(issues)
        if a.check:
            continue
        print(f"▶ {f.name}")
        render(data, out, a.tts, a.think, a.loops, a.preview)
        if a.daily and not a.preview:
            hist["longform_day"] = data["day"]
            from datetime import date
            hist.setdefault("rendered", []).append(
                {"date": date.today().isoformat(), "type": "longform", "day": data["day"], "file": f.name,
                 "tts": LAST_ENGINE})
            hist_path.write_text(json.dumps(hist, ensure_ascii=False, indent=2), encoding="utf-8")
    if a.check:
        print("검증 완료" + (" (경고 있음)" if bad else ": 문제 없음"))
        sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()

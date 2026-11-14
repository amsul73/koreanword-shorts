"""오늘의 콘텐츠(JSON) 준비.

content/queue/ 의 JSON을 이름순으로 하나씩 소비한다.
큐 파일은 Claude(또는 ChatGPT)에게 만들어 달라고 해서 넣는다 → API 키 불필요.

단어 JSON 한 항목의 형식
  word       한국어 단어      (예: "주문")
  reading    가타카나 발음    (예: "チュムン")
  meaning    일본어 뜻        (예: "注文")
  example    한국어 예문      (예: "커피를 주문할게요.")
  example_ja 일본어 번역      (예: "コーヒーを注文します。")
"""
import json
import re
import shutil
from datetime import date

from . import config

# reading 필드는 가타카나(+장음 ー, 중점 ・, 공백)만 허용 → 히라가나/한글 섞여 들어가는 실수 차단
KATAKANA_RE = re.compile(r"^[\u30A0-\u30FF\u31F0-\u31FF ]+$")


def load_history():
    if config.HISTORY_FILE.exists():
        return json.loads(config.HISTORY_FILE.read_text(encoding="utf-8"))
    return {"vocab_day": 0, "grammar_day": 0, "basic_day": 0, "longform_day": 0,
            "words": [], "grammar": [], "basic_words": [], "rendered": []}


def save_history(h):
    config.HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    config.HISTORY_FILE.write_text(json.dumps(h, ensure_ascii=False, indent=2), encoding="utf-8")


def queue_files(kind):
    return sorted(config.QUEUE_DIR.glob(f"{kind}_*.json"))


def validate(kind, data):
    if kind in ("vocab", "basic"):
        assert data.get("words"), "words가 비어있음"
        for w in data["words"]:
            for k in ("word", "reading", "meaning"):
                assert w.get(k), f"단어 항목에 {k} 없음: {w}"
            assert KATAKANA_RE.match(w["reading"]), \
                f"reading은 가타카나로 적어야 합니다: {w['word']} → {w['reading']}"
    else:
        for k in ("title", "meaning", "form", "examples"):
            assert data.get(k), f"문법에 {k} 없음"
        for e in data["examples"]:
            assert e.get("ko") and e.get("ja"), f"예문 형식 오류: {e}"


def check_queue(kind="vocab"):
    """큐 전체 검증: 형식 오류 + 이미 쓴/큐 안에서 겹치는 단어. 문제 목록 반환."""
    h = load_history()
    hist_words = {"vocab": h.get("words", []), "basic": h.get("basic_words", [])}.get(kind, [])
    seen = {w: "history" for w in hist_words}
    problems = []
    for f in queue_files(kind):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            validate(kind, data)
        except Exception as e:
            problems.append(f"{f.name}: {e}")
            continue
        if kind in ("vocab", "basic"):
            for w in data["words"]:
                if w["word"] in seen:
                    problems.append(f"{f.name}: '{w['word']}' 중복 (이미 {seen[w['word']]})")
                seen.setdefault(w["word"], f.name)
    return problems


def get_content(kind):
    """(data, queue_file) 반환. data에는 day 번호가 채워진다."""
    files = queue_files(kind)
    if not files:
        raise SystemExit(f"큐가 비었습니다: {config.QUEUE_DIR}/{kind}_*.json 를 추가하세요 (Claude에게 요청)")
    data = json.loads(files[0].read_text(encoding="utf-8"))
    validate(kind, data)
    history = load_history()
    data["type"] = "vocab" if kind == "basic" else kind   # 왕초보도 단어 쇼츠 구조 그대로
    if kind == "basic":
        data["series"] = "basic"
    data["day"] = history.get(f"{kind}_day", 0) + 1
    data.setdefault("date", date.today().isoformat())
    return data, files[0]


def commit(kind, data, qfile, tts="edge"):
    """렌더 성공 후 히스토리 기록 + 큐 파일을 used/로 이동."""
    h = load_history()
    h[f"{kind}_day"] = max(h.get(f"{kind}_day", 0), data["day"])
    if kind == "vocab":
        h["words"].extend(w["word"] for w in data["words"])
    elif kind == "basic":
        h.setdefault("basic_words", []).extend(w["word"] for w in data["words"])
    else:
        h["grammar"].append(data["title"])
    h.setdefault("rendered", []).append({"date": data["date"], "type": kind, "day": data["day"],
                                        "file": qfile.name, "tts": tts})
    save_history(h)
    config.USED_DIR.mkdir(parents=True, exist_ok=True)
    shutil.move(str(qfile), config.USED_DIR / qfile.name)

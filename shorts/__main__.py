"""사용법:
  python -m shorts vocab                    # 큐에서 하나 꺼내 렌더 → output/
  python -m shorts vocab --count 7          # 7일치 한꺼번에 렌더
  python -m shorts basic                    # 왕초보(初心者) 시리즈
  python -m shorts check                    # 큐 검증 (형식/중복 단어)
  python -m shorts voices                   # 선희(한)/나나미(일) 음성 샘플 mp3
  python -m shorts vocab --file content/samples/vocab_sample.json   # 테스트 렌더 (기록 안 함)
"""
import argparse
import json
import sys
from pathlib import Path

from . import config, content
from .meta import write_upload_info
from .video import render_video


def render_one(kind, data):
    prefix = data.get("series") or kind   # 왕초보 시리즈는 basic_dayNNN
    out = config.OUTPUT_DIR / f"{prefix}_day{data['day']:03d}.mp4"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.with_suffix(".json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    write_upload_info(data, out.with_suffix(".txt"))
    render_video(data, out)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("kind", choices=["vocab", "basic", "grammar", "check", "voices"])
    ap.add_argument("--file", help="이 JSON으로 테스트 렌더 (히스토리 기록 안 함)")
    ap.add_argument("--count", type=int, default=1, help="큐에서 몇 개 렌더할지")
    ap.add_argument("--day", type=int, help="--file과 함께: Day 번호 지정 (재생성용)")
    a = ap.parse_args()

    if a.kind == "voices":
        from .video import tts
        config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        ko = "주문. 지하철. 커피를 주문할게요. 매일 아침 6시에 일어나요."
        ja = "今日の韓国語の単語10個。今日は何個わかるかな？ 注文。"
        # 무료 edge-tts가 제공하는 한국어 3 / 일본어 2를 전부 뽑아 비교해 볼 수 있게 한다
        for name, text, voice in [
            ("ko_1_sunhi", ko, "ko-KR-SunHiNeural"),
            ("ko_2_injoon", ko, "ko-KR-InJoonNeural"),
            ("ko_3_hyunsu", ko, "ko-KR-HyunsuMultilingualNeural"),
            ("ja_1_nanami", ja, "ja-JP-NanamiNeural"),
            ("ja_2_keita", ja, "ja-JP-KeitaNeural"),
        ]:
            tts(text, voice, config.OUTPUT_DIR / f"voice_{name}.mp3")
            print(f"  {voice} → output/voice_{name}.mp3")
        return

    if a.kind == "check":
        problems = content.check_queue("vocab") + content.check_queue("basic") + content.check_queue("grammar")
        for p in problems:
            print("  ✗", p)
        print(f"큐: 단어 {len(content.queue_files('vocab'))}일치, 왕초보 {len(content.queue_files('basic'))}일치, "
              f"문법 {len(content.queue_files('grammar'))}일치")
        sys.exit(1 if problems else 0)

    if a.file:
        data = json.loads(Path(a.file).read_text(encoding="utf-8"))
        content.validate(a.kind, data)
        data.update(type="vocab" if a.kind == "basic" else a.kind, date="sample")
        if a.kind == "basic":
            data["series"] = "basic"
        data["day"] = a.day or data.get("day", 1)
        render_one(a.kind, data)
        return

    for _ in range(a.count):
        if not content.queue_files(a.kind):
            break
        data, qfile = content.get_content(a.kind)
        render_one(a.kind, data)
        from .video import _engine
        content.commit(a.kind, data, qfile, _engine["name"])
    left = len(content.queue_files(a.kind))
    print(f"큐 남은 일수: {left}")
    if left <= config.QUEUE_WARN_DAYS:
        print(f"::warning::{a.kind} 큐가 {left}일치 남았습니다. Claude에게 다음 배치를 요청하세요.")


if __name__ == "__main__":
    main()

"""gTTS(대체 음성)로 만들어진 영상을 edge-tts(선희·나나미)로 다시 렌더.

  python scripts/retts.py --probe     # edge-tts가 되는지만 확인 (exit 0 = 됨)
  python scripts/retts.py             # 대상 재렌더 → output/, out/ 에 결과, history 갱신, 요약을 retts_summary.md 로
"""
import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HIST = ROOT / "data" / "history.json"
REPO = os.getenv("GITHUB_REPOSITORY", "amsul73/koreanword-shorts")


def probe():
    import edge_tts
    out = ROOT / "probe.mp3"
    try:
        for text, voice in (("테스트입니다.", "ko-KR-SunHiNeural"), ("テストです。", "ja-JP-NanamiNeural")):
            asyncio.run(edge_tts.Communicate(text, voice).save(str(out)))
        print("edge-tts OK")
        return True
    except Exception as e:
        print(f"edge-tts 아직 안 됨: {type(e).__name__}: {str(e)[:120]}")
        return False
    finally:
        out.unlink(missing_ok=True)


def main():
    if "--probe" in sys.argv:
        sys.exit(0 if probe() else 1)
    h = json.loads(HIST.read_text(encoding="utf-8"))
    todo = [r for r in h.get("rendered", []) if r.get("tts") == "gtts"]
    if not todo:
        print("재생성할 영상 없음")
        return
    env = dict(os.environ, TTS_STRICT="1")
    done = []
    for r in todo:
        if r["type"] in ("vocab", "basic"):
            src = ROOT / "content" / "used" / r["file"]
            cmd = [sys.executable, "-m", "shorts", r["type"], "--file", str(src), "--day", str(r["day"])]
            tag = f"{r['type']}_day{r['day']:03d}"
        else:
            src = ROOT / "longform" / "days" / r["file"]
            cmd = [sys.executable, "longform/make_listening_video.py", str(src), "--out", "out"]
            tag = f"longform_day{r['day']:02d}"
        print("▶", " ".join(cmd))
        subprocess.run(cmd, check=True, cwd=ROOT, env=env)
        r["tts"] = "edge"
        r["retts"] = True
        done.append((r["type"], r["day"], tag))
    HIST.write_text(json.dumps(h, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = ["@amsul73 Microsoft 음성(edge-tts)이 다시 동작해서, 대체 음성(gTTS)으로 만들었던 영상을 "
             "**선희·나나미 음성으로 다시 만들었습니다.** 기존 Release를 교체했으니 다시 받아주세요.", ""]
    for kind, day, tag in done:
        name = {"vocab": f"쇼츠 Day {day}", "basic": f"왕초보 쇼츠 Day {day}"}.get(kind, f"롱폼 Day {day}")
        lines.append(f"- {name}: https://github.com/{REPO}/releases/tag/{tag}")
    lines += ["", "PC 다운로드 스크립트는 이미 받은 폴더를 건너뛰므로, 위 Day 폴더를 지운 뒤 실행하거나 링크에서 직접 받아주세요."]
    (ROOT / "retts_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()

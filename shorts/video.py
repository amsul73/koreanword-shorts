"""장면 목록 → TTS 음성 → ffmpeg로 mp4 합성.

음성 배치: 한국어 단어는 VOICE_KO(선희)가 읽고, 일본어 뜻·인트로·구독 멘트는 VOICE_JA(나나미)가 읽는다.
"""
import asyncio
import math
import os
import re
import shutil
import subprocess
from pathlib import Path

from . import config as C
from . import render as R


class Scene:
    def __init__(self, image, duration, tts=None, pad=0.6, lead=0.0):
        self.image = image          # PIL.Image
        self.lead = lead            # 화면이 뜬 뒤 음성 시작까지 대기(초)
        self.duration = duration    # 최소 길이(초)
        self.tts = tts              # [(text, voice[, 뒤 간격초]), ...] 순서대로 읽음 (간격 기본 0.2초)
        self.pad = pad              # 음성 뒤 여유


def build_scenes(data):
    if data["type"] == "vocab":
        s = [Scene(R.vocab_intro(data), 2.5,
                   [(f"今日の韓国語の単語{len(data['words'])}個。今日は何個わかるかな？", C.VOICE_JA)], pad=0.3)]
        for i, w in enumerate(data["words"]):
            for n in (3, 2, 1):
                s.append(Scene(R.vocab_quiz(data, i, n), 0.5))
            # 한글은 표음문자라 word를 그대로 읽어도 정확하다 → 가타카나(reading)로 읽히지 않게 word 사용
            say = [(w["word"], C.VOICE_KO, C.MEANING_GAP)]
            if C.READ_MEANING:
                say.append((w["meaning"], C.VOICE_JA))
            s.append(Scene(R.vocab_reveal(data, i), 2.2, say, pad=0.5, lead=0.3))
        # 마지막 단어가 끝나면 복습표. END_CTA=1이면 복습표 하단에 구독 배너 + 페이드아웃 종료
        if C.END_CTA:
            # 복습표가 나오는 동안 나나미(일본어) 음성으로 구독 문구 읽기 (최소 4.5초, 음성이 길면 그만큼 + 1초)
            s.append(Scene(R.vocab_review(data, cta=True), 4.5, [(R.cta_text(data), C.VOICE_JA)], pad=1.0))
        else:
            s.append(Scene(R.vocab_review(data), 4.5))
        return s
    title_reading = re.sub(r"[-~～〜/]", " ", data["title"]).strip()
    s = [Scene(R.grammar_title(data), 3.0,
               [(title_reading, C.VOICE_KO), (data["meaning"], C.VOICE_JA)], pad=0.8)]
    for i, ex in enumerate(data["examples"]):
        s.append(Scene(R.grammar_example(data, i), 3.0, [(ex["ko"], C.VOICE_KO)], pad=1.2))
    s.append(Scene(R.grammar_summary(data), 6.0))
    return s


def _ffprobe_duration(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "default=nw=1:nk=1", str(path)], capture_output=True, text=True)
    return float(out.stdout.strip() or 0)


async def _edge_tts(text, voice, path):
    import edge_tts
    await edge_tts.Communicate(text, voice, rate=C.TTS_RATE).save(str(path))


_engine = {"name": "edge"}


def tts(text, voice, path):
    """edge-tts(고품질) → 계속 실패하면 이 영상은 끝까지 gTTS로 대체 (음성이 섞이지 않게)."""
    if _engine["name"] == "edge":
        import time
        for t in range(3):
            try:
                asyncio.run(_edge_tts(text, voice, path))
                return
            except Exception as e:
                err = e
                time.sleep(2 * (t + 1))
        if os.getenv("TTS_STRICT") == "1":   # 재생성 모드: 대체 음성 금지
            raise RuntimeError(f"edge-tts 실패: {err}")
        print(f"::warning::edge-tts 실패({type(err).__name__}) → 이 영상은 gTTS 음성으로 대체합니다")
        _engine["name"] = "gtts"
    from gtts import gTTS
    gTTS(text, lang=voice[:2]).save(str(path))


def make_audio(scene, idx, work):
    """여러 문장을 하나의 오디오로 이어 붙여 경로 반환. TTS 실패 시 None(무음)."""
    if not (scene.tts and C.TTS_ENABLED):
        return None
    parts = []
    try:
        for k, (text, voice, *gap) in enumerate(scene.tts):
            p = work / f"tts_{idx:03d}_{k}.mp3"
            tts(text, voice, p)
            parts.append((p, gap[0] if gap else 0.2))
    except Exception as e:  # 네트워크 문제 등 → 무음으로 진행 (재생성 모드에선 중단)
        if os.getenv("TTS_STRICT") == "1":
            raise
        print(f"  [warn] TTS 실패, 무음 처리: {e}")
        return None
    out = work / f"audio_{idx:03d}.m4a"
    inputs = sum((["-i", str(p)] for p, _ in parts), [])
    # TTS 앞뒤 무음 제거 후 문장 사이 간격(기본 0.2초).
    # 첫소리(아·어 등 부드럽게 시작하는 모음)가 잘리지 않게 낮은 기준(-60dB) + 앞뒤 0.08초 여유 유지
    trim = "silenceremove=start_periods=1:start_threshold=-60dB:start_silence=0.08"
    chain = "".join(f"[{k}:a]{trim},areverse,{trim},areverse,apad=pad_dur={g}[a{k}];"
                    for k, (_, g) in enumerate(parts))
    chain += "".join(f"[a{k}]" for k in range(len(parts))) + f"concat=n={len(parts)}:v=0:a=1"
    if scene.lead:
        chain += f",adelay={int(scene.lead * 1000)}:all=1"
    chain += "[out]"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", chain,
                    "-map", "[out]", "-c:a", "aac", str(out)], check=True)
    return out


def _bgm_filter(duration):
    """저작권 걱정 없는 합성 배경음(두 화음이 4초마다 바뀌는 부드러운 패드). ffmpeg 필터 문자열 반환."""
    a = "0.5*sin(2*PI*220*t)+0.35*sin(2*PI*277.18*t)+0.3*sin(2*PI*329.63*t)"      # A
    f = "0.5*sin(2*PI*174.61*t)+0.35*sin(2*PI*220*t)+0.3*sin(2*PI*261.63*t)"      # F
    expr = f"(if(lt(mod(t\\,8)\\,4)\\,{a}\\,{f}))*(0.75+0.25*sin(2*PI*0.25*t))"
    return (f"aevalsrc='{expr}':s=44100:c=stereo:d={duration:.2f},lowpass=f=900,"
            f"afade=t=in:d=1,volume={C.BGM_DB}dB[bgm]")


def render_video(data, out_path: Path):
    work = out_path.parent / (out_path.stem + "_work")
    work.mkdir(parents=True, exist_ok=True)
    scenes = build_scenes(data)
    segs = []
    for i, sc in enumerate(scenes):
        img = work / f"scene_{i:03d}.png"
        sc.image.save(img)
        audio = make_audio(sc, i, work)
        dur = sc.duration
        if audio:
            dur = max(dur, _ffprobe_duration(audio) + sc.pad)
        dur = math.ceil(dur * C.FPS - 1e-6) / C.FPS   # 프레임 단위로 맞춰 영상·소리 길이 일치
        # 장면 조각의 소리는 무압축(PCM)으로 → 이어 붙일 때 AAC 경계 잡음/타임스탬프 겹침이 생기지 않음
        seg = work / f"seg_{i:03d}.mov"
        a_in = ["-i", str(audio)] if audio else ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo"]
        subprocess.run([
            "ffmpeg", "-y", "-loglevel", "error",
            "-loop", "1", "-framerate", str(C.FPS), "-i", str(img), *a_in,
            "-t", f"{dur:.2f}", "-af", "apad", "-c:v", "libx264", "-tune", "stillimage",
            "-pix_fmt", "yuv420p", "-r", str(C.FPS), "-c:a", "pcm_s16le", "-ar", "44100", "-ac", "2",
            str(seg)], check=True)
        segs.append(seg)
    lst = work / "list.txt"
    lst.write_text("".join(f"file '{p.name}'\n" for p in segs))
    if C.END_CTA:
        # 끝 0.6초 화면·소리 페이드아웃으로 자연스럽게 종료
        joined = work / "joined.mov"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
                        "-i", str(lst), "-c", "copy", str(joined)], check=True)
        d = _ffprobe_duration(joined)
        st = max(d - 0.6, 0)
        afade = f"afade=t=out:st={st:.2f}:d=0.6"
        if C.BGM:
            fc = (f"{_bgm_filter(d)};[0:a][bgm]amix=inputs=2:duration=first:normalize=0,{afade}[a];"
                  f"[0:v]fade=t=out:st={st:.2f}:d=0.6:color=white[v]")
            maps = ["-filter_complex", fc, "-map", "[v]", "-map", "[a]"]
        else:
            maps = ["-vf", f"fade=t=out:st={st:.2f}:d=0.6:color=white", "-af", afade]
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(joined), *maps,
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart",
                        str(out_path)], check=True)
    else:
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
                        "-i", str(lst), "-c:v", "copy", "-c:a", "aac", "-b:a", "160k",
                        "-movflags", "+faststart", str(out_path)], check=True)
    # 썸네일 = 첫 장면(인트로)과 같은 디자인 → 앱에서 프레임 선택해도 동일
    thumb = out_path.with_name(out_path.stem + "_thumb.jpg")
    scenes[0].image.save(thumb, quality=95)
    shutil.rmtree(work, ignore_errors=True)
    total = _ffprobe_duration(out_path)
    print(f"  영상 생성: {out_path} ({total:.1f}s, {len(scenes)} scenes)")
    return out_path

"""채널/영상 공통 설정. 대부분 환경변수로 덮어쓸 수 있다.

이 저장소는 '일본인 학습자에게 한국어 단어를 가르치는' 쇼츠를 만든다.
  - 배우는 말(main)  = 한국어  → 화면 큰 글씨, 메인 음성(VOICE_KO)
  - 설명하는 말(sub) = 일본어  → 뜻/인트로/자막, 설명 음성(VOICE_JA)
"""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "output"
QUEUE_DIR = ROOT / "content" / "queue"      # Claude로 만든 JSON을 여기에 넣으면 우선 사용
USED_DIR = ROOT / "content" / "used"        # 사용한 큐 파일은 여기로 이동
HISTORY_FILE = ROOT / "data" / "history.json"

# 영상 규격 (Shorts: 9:16)
WIDTH, HEIGHT = 1080, 1920
FPS = 30

# 색상
BG = (255, 255, 255)
TEXT = (25, 25, 25)
SUB = (110, 110, 110)
ACCENT = (230, 70, 70)
CARD = (246, 246, 246)

# 폰트 (한글 + 가나/한자를 모두 가진 폰트가 필요: Noto Sans CJK 권장 → apt install fonts-noto-cjk)
#   {w} → Bold / Regular,  {wb} → bd / (빈칸)
FONT_CANDIDATES = [
    os.getenv("FONT_PATH", ""),
    "/usr/share/fonts/opentype/noto/NotoSansCJK-{w}.ttc",
    "/usr/share/fonts/noto-cjk/NotoSansCJK-{w}.ttc",
    "/System/Library/Fonts/AppleSDGothicNeo.ttc",
    "C:/Windows/Fonts/malgun{wb}.ttf",
]

# TTS (edge-tts, 무료)
# 주의: 무료 edge-tts endpoint가 주는 음성은 한국어 3개 / 일본어 2개뿐이다 (전체 318개 중, 2026-11 확인).
#   한국어: ko-KR-SunHiNeural(여, 기본) · ko-KR-InJoonNeural(남) · ko-KR-HyunsuMultilingualNeural(남)
#   일본어: ja-JP-NanamiNeural(여, 기본) · ja-JP-KeitaNeural(남)
# ja-JP-AoiNeural, ko-KR-JiMinNeural 같은 음성은 유료 Azure Speech 전용이라 여기서 지정하면 실패한다.
# 현재 쓸 수 있는 음성을 전부 들어보려면: python -m shorts voices
TTS_ENABLED = os.getenv("TTS_ENABLED", "1") == "1"
VOICE_KO = os.getenv("VOICE_KO", "ko-KR-SunHiNeural")   # 배우는 말 = 한국어
VOICE_JA = os.getenv("VOICE_JA", "ja-JP-NanamiNeural")  # 설명하는 말 = 일본어
TTS_RATE = os.getenv("TTS_RATE", "+0%")
READ_MEANING = os.getenv("READ_MEANING", "1") == "1"   # 정답 화면에서 일본어 뜻도 읽기
END_CTA = os.getenv("END_CTA", "1") == "1"   # 마지막 복습표 하단에 구독 배너 + 페이드아웃 종료
# 배경음: 완전 무음 구간이 없도록 아주 작은 잔잔한 화음을 깔아 유튜브 자동 볼륨이 첫소리를 줄이는 문제 완화
BGM = os.getenv("BGM", "0") == "1"
BGM_DB = float(os.getenv("BGM_DB", "-30"))   # 배경음 크기(dB). 목소리보다 훨씬 작게
MEANING_GAP = float(os.getenv("MEANING_GAP", "1.2"))   # 한국어 단어 → 일본어 뜻 사이 간격(초)

LEVEL = os.getenv("TOPIK_LEVEL", "初級")   # 태그/표기용 (TOPIK 1~2급 = 初級)
QUEUE_WARN_DAYS = 3   # 큐 남은 일수가 이 이하면 경고

# 채널 표기 (일본어 시청자에게 보이는 이름)
CHANNEL_NAME = os.getenv("CHANNEL_NAME", "毎日韓国語")

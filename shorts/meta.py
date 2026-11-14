"""수동 업로드용 제목/설명/태그 텍스트 생성 (일본인 시청자용 = 일본어)."""
from . import config as C


def metadata(data):
    if data["type"] == "vocab":
        theme = f"（{data['theme']}）" if data.get("theme") else ""
        n = len(data["words"])
        if data.get("series") == "basic":
            title = f"はじめての韓国語 ハングル単語{n}個 Day {data['day']}{theme} #shorts"
        else:
            title = f"韓国語の単語{n}個 Day {data['day']}{theme} #shorts"
        lines = [f"{w['word']} ({w['reading']}) - {w['meaning']}" for w in data["words"]]
        tags = (["韓国語", "韓国語初心者", "ハングル", "ハングル読み方", "韓国語勉強", "TOPIK", "韓国語単語"]
                if data.get("series") == "basic" else
                ["韓国語", "韓国語単語", "TOPIK", C.LEVEL, "韓国語勉強", "ハングル", "한국어"])
    else:
        title = f"韓国語文法 {data['title']} をまとめて整理 | Day {data['day']} #shorts"
        lines = [f"{data['title']} : {data['meaning']}", f"接続: {data['form']}", ""]
        lines += [f"・{e['ko']}\n  {e['ja']}" for e in data["examples"]]
        if data.get("note"):
            lines += ["", f"ポイント: {data['note']}"]
        tags = ["韓国語", "韓国語文法", "TOPIK", C.LEVEL, "韓国語勉強", data["title"]]
    desc = ("\n".join(lines) + f"\n\n{C.CHANNEL_NAME} 🇰🇷 毎日更新中！いくつ分かりましたか？コメントで教えてください！"
            "\n#韓国語 #韓国語勉強 #韓国語単語 #ハングル #shorts")
    return title[:100], desc[:4900], tags


def write_upload_info(data, path):
    title, desc, tags = metadata(data)
    text = f"[제목]\n{title}\n\n[설명]\n{desc}\n\n[태그]\n{', '.join(tags)}\n"
    path.write_text(text, encoding="utf-8")
    return text

# ===================== 声线档案（v17.12） =====================
# 每个角色卡一套声纹：基础音色 + 基频/语速/音量偏移。
#
#     personas/<名字>/voice.json
#     {
#       "voice": "zh-CN-XiaoxiaoNeural",
#       "pitch_base": 0,
#       "rate_base": 0,
#       "volume": 0,
#       "notes": "偏软、尾音略上扬"
#     }
#
# 缺失就返回默认档案，不报错——配音是锦上添花，不能挡住启动。

import io
import json
import os

from ..log import log_api

DEFAULT = {
    "voice": os.getenv("NAO_VOICE", "zh-CN-XiaoxiaoNeural"),
    "pitch_base": 0,
    "rate_base": 0,
    "volume": 0,
    "notes": "",
}

FIELDS = ("voice", "pitch_base", "rate_base", "volume")


def profile_path(persona=None):
    """声纹文件路径；persona 不传就用当前角色卡"""
    from ..ai import persona_loader

    if persona:
        return os.path.join(persona_loader.CARD_ROOT, persona, "voice.json")
    return os.path.join(persona_loader.card_dir(), "voice.json")


def load_profile(persona=None):
    """读声纹档案；文件不存在/坏掉都回落默认（返回新 dict，调用方可改）"""
    prof = dict(DEFAULT)
    try:
        path = profile_path(persona)
        if path and os.path.exists(path):
            with io.open(path, encoding="utf-8") as f:
                raw = json.load(f)
            for k in FIELDS:
                if raw.get(k) is not None:
                    prof[k] = raw[k]
            if raw.get("notes"):
                prof["notes"] = str(raw["notes"])[:80]
    except Exception as e:
        log_api(f"[声线] 读取失败，用默认：{e}")
    return prof


def save_profile(data, persona=None):
    """写回声纹（!voice 改完用）；失败返回 False，不抛"""
    prof = dict(DEFAULT)
    for k in FIELDS:
        if (data or {}).get(k) is not None:
            prof[k] = data[k]
    prof["notes"] = str((data or {}).get("notes") or "")[:80]
    try:
        path = profile_path(persona)
        d = os.path.dirname(path)
        if d:
            os.makedirs(d, exist_ok=True)
        with io.open(path, "w", encoding="utf-8") as f:
            json.dump(prof, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        log_api(f"[声线] 保存失败：{e}")
        return False


def describe(persona=None):
    """给 !voice 看的一行"""
    prof = load_profile(persona)

    def sign(v):
        return f"{int(v):+d}" if isinstance(v, (int, float)) else str(v)

    text = (f"🎙️ 声线：{prof['voice']}"
            f"｜音高 {sign(prof['pitch_base'])}Hz"
            f"｜语速 {sign(prof['rate_base'])}%"
            f"｜音量 {sign(prof['volume'])}%")
    if prof.get("notes"):
        text += f"\n   {prof['notes']}"
    return text


# ===================== 情绪 → 语气（U1/U2） =====================
# 五档。edge-tts 不支持 Azure 的 style 参数，
# 所以「风格」用 rate/pitch/volume 的组合近似，不假装支持。

EMOTIONS = {
    "平静": {"rate": 0, "pitch": 0, "volume": 0},
    "开心": {"rate": 8, "pitch": 30, "volume": 3},
    "撒娇": {"rate": -5, "pitch": 40, "volume": 0},
    "难过": {"rate": -12, "pitch": -20, "volume": -3},
    "生气": {"rate": 10, "pitch": 10, "volume": 5},
}
DEFAULT_EMOTION = "平静"


def emotion_params(emotion=None, profile=None):
    """情绪 + 声纹 → 给 edge-tts 的参数"""
    prof = profile or load_profile()
    emo = emotion if emotion in EMOTIONS else DEFAULT_EMOTION
    delta = EMOTIONS[emo]
    return {
        "voice": prof.get("voice") or DEFAULT["voice"],
        "rate": int(prof.get("rate_base") or 0) + delta["rate"],
        "pitch": int(prof.get("pitch_base") or 0) + delta["pitch"],
        "volume": int(prof.get("volume") or 0) + delta["volume"],
        "emotion": emo,
    }

# ===================== 情绪从哪来（U5） =====================
# 不新增探测，只用现有状态：
#   mood（0~1）     → 开心 / 难过 / 平静
#   关系亲密度      → 撒娇
#   摩擦值          → 生气

def detect_emotion(tid=None):
    """读现有状态推断当前情绪；任何一项读不到都退回平静"""
    mood, fric, close = None, 0.0, 0.0

    try:
        from ..life import state as life_state

        mood = float((life_state.current(tid=tid) or {}).get("mood"))
    except Exception:
        mood = None

    try:
        from ..life import friction as life_friction

        st = life_friction.load(tid) if tid else {}
        disappoint = float((st or {}).get("disappoint") or 0)
        cold = 1.0 if (st or {}).get("cold_ts") else 0.0
        fric = max(cold, min(1.0, disappoint / 5.0))
    except Exception:
        fric = 0.0

    try:
        from ..life import relation as life_relation

        close = float(life_relation.get(tid) or 0) if tid else 0.0
        if close > 1.0:                     # 有些实现返回百分制
            close = close / 100.0
    except Exception:
        close = 0.0

    return emotion_from(mood, fric, close)


def emotion_from(mood=None, fric=0.0, close=0.0):
    """纯函数，方便测试：状态数字 → 五个情绪之一

    基线 mood 是 0.10（见 life/state.py 的 BASE），所以「平静」区间
    要包住基线，不能把默认状态判成难过。
    """
    if fric is not None and fric >= 0.6:
        return "生气"
    if mood is not None:
        if mood <= -0.05:
            return "难过"
        if mood >= 0.45:
            return "开心"
    if close is not None and close >= 0.7:
        return "撒娇"
    return DEFAULT_EMOTION

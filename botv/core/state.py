# ===================== 运行时状态 =====================
# 唯一可变的全局状态（v5-R2 从 config.py 拆出）
# 规则：只放会被运行时修改的值；常量在 core/constants.py
# 用法：from botv.core import state as cfg

import asyncio
from collections import defaultdict, deque
from datetime import date

from .constants import *  # noqa: F401,F403  让 state 也能读到常量（cfg.MASTER_QQ 等）

# ===================== 连接状态 =====================
active_ws_qq = None  # 当前活跃的QQ WebSocket连接
active_ws_lock = asyncio.Lock()  # WebSocket连接锁（防止多连接冲突）
send_lock = asyncio.Lock()  # 消息发送锁（防止WebSocket发送冲突）
last_online_notice_ts = 0.0  # 上次发送「上线通知」的时间戳（v5-F5 防重发）
self_qq = 0  # 机器人自己的QQ号（从 OneBot 事件的 self_id 取，v6-E29 判断被@）

# ===================== 群聊节奏（v6-E29） =====================
group_last_reply_ts = {}  # {群号: 上次回复时间戳}
group_msg_window = {}  # {群号: deque[时间戳]} 最近发言时间窗
group_streak = {}  # {群号: 连续说了几句没人接}（v10）

# ===================== 消息处理 =====================
PROCESSED_MSG_IDS = deque(maxlen=80)  # 已处理消息ID缓存（去重，最多80条）
PROCESS_LOCK = None  # 旧的全局锁（bootstrap 中初始化，已不再用于消息处理）
pending_outbox = deque(maxlen=50)  # 断线期间待补发的消息（v5-F6）
target_locks = {}  # {target_id: asyncio.Lock} 按对象分片锁（v6-E26）

# ===================== API 密钥（运行时从数据库加载） =====================
DS_API_KEY = ""
DOUBAO_API_KEY = ""
STICKER_API_ALAPI_TOKEN = ""

# ===================== 定时任务状态 =====================
daily_trigger = set()  # 今日已触发的定时任务key集合
today = date.today()  # 当前日期
daily_chat_trigger_times = []  # 今日闲聊触发时间点列表
triggered_today = set()  # 今日已触发的闲聊时间点
task_trigger_minute = {}  # 定时任务触发分钟映射 {key: minute}

# ===================== 记忆与图片 =====================
user_memory_pool = {}  # 用户对话记忆池 {target_id: deque}
global_keyword_set = set()  # 公共关键词（v8-B12：只放公共库）
target_keyword_sets = {}  # {target_id: set} 每个对象自己的关键词

# ===================== 她的状态（v9-U4） =====================
bot_state = {}      # mood / energy / lonely
bot_state_ts = 0.0  # 上次推进的时间戳
life_last_date = {}  # {target_id: 'YYYY-MM-DD'} 生活事件生成日期（v9-U7）
habit_counters = {}  # {target_id: Counter} 口头禅计数（v12-A17）
pending_echo = {}  # {echo: Future} 等待 NapCat 回包（v12-A13）
typo_history = []  # 打错字撤回的时间戳（v12-A13，控制频率）
friction_states = {}  # {target_id: dict} 摩擦状态（v13-U20）

# ===================== 主动消息（v10-U9） =====================
last_user_msg_ts = 0.0      # 最近一次收到消息的时间
last_proactive_ts = 0.0     # 最近一次主动发消息的时间
proactive_count_today = 0   # 今天主动发了几条
proactive_unanswered = 0    # 连续几条主动没被回应
USER_STICKER_CACHE = defaultdict(list)  # 用户最近使用的QQ表情缓存
USER_STICKER_ARCHIVE = defaultdict(list)  # 用户旧表情包存档
STICKER_DATA = {}  # 表情包数据 {hash: info_dict}
CLIP_ENABLED = False  # CLIP 是否可用（clip.init_clip_model 中设置）

# ===================== 代码模式 =====================
CODE_MODE = False  # 代码模式：知识正确性优先于角色人设
CODE_MODE_LAST_MSG_TIME = 0  # 上次收到消息的时间戳（秒），用于30分钟超时自动退出
CODE_MODE_TIMEOUT = 1800  # 代码模式自动退出超时（秒）= 30分钟

# ===================== 退出程序 =====================
shutdown_event = None  # 退出事件（bootstrap 中初始化为 asyncio.Event()）

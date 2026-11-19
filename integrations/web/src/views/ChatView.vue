<script setup lang="ts">
const messages = [
  { who: 'bot', text: '你回来啦。今天外面有点冷，先喝点热的吧。', meta: '20:58 · 已读' },
  { who: 'me', text: '刚到家。今天那个方案终于过了。', meta: '21:00 · 已读' },
  { who: 'bot', text: '那很好啊。你上次说怕过不了，我还记着呢。要不要把这件事记进“今天值得高兴的事”？', meta: '21:01 · 记忆已更新', mem: '关联记忆 · 方案汇报 · 11 月 19 日' },
  { who: 'me', text: '好。顺便帮我看下这个月还剩多少。', meta: '21:03 · 已读' },
  { who: 'bot', text: '本月收入 ¥8,000，支出 ¥3,200，存钱 ¥1,500，结余 ¥3,300。旅行目标已经 60% 了。', meta: '21:03 · 财务摘要（仅主人私聊）' },
]
</script>
<template>
  <div class="chat">
    <div class="top">
      <div class="who">
        <span class="avatar">奈</span><div>
          <div class="nm">
            友利奈绪
          </div><div class="sub">
            私聊 · 记忆同步 <span class="pill">在线</span>
          </div>
        </div>
      </div><button class="tbtn">
        ⌕ 聊天内搜索
      </button><button class="tbtn">
        ⋯
      </button>
    </div>
    <div class="msgs">
      <div class="day">
        <b>今天</b> · 20:58
      </div>
      <div
        v-for="(m, i) in messages"
        :key="i"
        class="msg"
        :class="{ me: m.who === 'me' }"
      >
        <span
          v-if="m.who !== 'me'"
          class="avatar"
        >奈</span>
        <div>
          <div class="bubble">
            {{ m.text }}
          </div><div
            v-if="m.mem"
            class="memchip"
          >
            ✦ {{ m.mem }}
          </div><div class="meta">
            {{ m.meta }}
          </div>
        </div>
        <span
          v-if="m.who === 'me'"
          class="avatar mea"
        >你</span>
      </div>
    </div>
    <div class="composer">
      <div class="tools">
        <span>＋ 图片</span><span>◌ 语音</span><span>◇ 表情</span><span>⌕ 搜图</span><span>✦ 记忆</span>
      </div><div class="inputbox">
        <textarea placeholder="和奈绪说点什么……" /><button class="send">
          发送
        </button>
      </div><div class="hint">
        <span>Enter 发送 · Shift+Enter 换行</span><span>MOCK · Web v35.5</span>
      </div>
    </div>
  </div>
</template>
<style scoped>
.chat{display:flex;flex-direction:column;min-height:0;flex:1}.top{height:66px;flex:none;border-bottom:1px solid var(--line);display:flex;align-items:center;padding:0 20px;gap:8px;background:#fff}.who{display:flex;align-items:center;gap:11px;min-width:0}.avatar{width:33px;height:33px;border-radius:10px;background:#dbeafe;color:#1d4ed8;display:grid;place-items:center;font-size:11px;font-weight:700;flex:none}.nm{font-size:14px;font-weight:650}.sub{font-size:10px;color:#7d8ca3;margin-top:2px}.pill{font-size:9px;color:#1d4ed8;border:1px solid #dbe8ff;background:#eef4ff;border-radius:20px;padding:2px 7px}.top .tbtn{margin-left:auto;height:30px;padding:0 10px;border-radius:9px;border:1px solid #e3ebf7;background:#fff;color:#5f7189;font-size:10.5px}.top .tbtn + .tbtn{margin-left:0}
.msgs{flex:1;overflow:auto;padding:20px 22px 16px;min-height:0}.day{text-align:center;font-size:9px;color:#93a3b8;margin:2px 0 18px}.day b{font-weight:500;color:#7d8ca3}.msg{display:flex;gap:9px;margin-bottom:14px;max-width:92%}.bubble{padding:9px 12px;border-radius:13px 13px 13px 4px;background:#eef4ff;border:1px solid #e3ebf7;font-size:12.5px;line-height:1.65;color:#243b55}.meta{font-size:9px;color:#93a3b8;margin:4px 2px 0}.msg.me{margin-left:auto;flex-direction:row-reverse}.msg.me .bubble{background:#2563eb;border-color:#2563eb;color:#fff;border-radius:13px 13px 4px 13px}.msg.me .meta{text-align:right}.msg.me .mea{background:#2563eb;color:#fff}.memchip{display:inline-block;margin-top:6px;padding:5px 8px;border-radius:8px;border:1px solid #e4dcff;background:#f3efff;font-size:9.5px;color:#6d4fd6}
.composer{flex:none;border-top:1px solid var(--line);padding:11px 18px 13px;background:#fff}.tools{display:flex;gap:6px;margin-bottom:7px}.tools span{font-size:10px;color:#8a9bb0;padding:4px 8px;border-radius:7px}.tools span:hover{background:#eef4ff;color:#1d4ed8}.inputbox{display:flex;align-items:flex-end;gap:9px;border:1px solid #dbe8ff;border-radius:12px;background:#f8fbff;padding:9px 10px}.inputbox:focus-within{border-color:#93b7fa;box-shadow:0 0 0 3px rgba(37,99,235,.08)}textarea{flex:1;resize:none;border:0;outline:0;background:none;color:#243b55;font:12.5px/1.5 inherit;height:22px}.send{height:30px;padding:0 14px;border-radius:8px;background:#2563eb;color:#fff;font-size:11px;font-weight:700;border:0}.hint{display:flex;justify-content:space-between;font-size:9px;color:#9aabbe;margin-top:6px}
</style>

<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Hoshinoumi Mobile · v35.7 页面细稿</title>
<style>
*{box-sizing:border-box}
body{margin:0;background:radial-gradient(800px 500px at 10% 0%,rgba(56,189,248,.14),transparent 60%),radial-gradient(800px 500px at 90% 15%,rgba(139,92,246,.10),transparent 60%),linear-gradient(180deg,#edf4ff,#e8f0fd);color:#17263b;font:13px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI","Microsoft YaHei",sans-serif}
.board{max-width:1320px;margin:0 auto;padding:36px 30px 60px}
header{display:flex;align-items:flex-end;justify-content:space-between;gap:20px;margin-bottom:26px}
.kicker{font-size:10px;letter-spacing:.2em;font-weight:800;color:#2563eb;margin-bottom:7px}
h1{margin:0 0 7px;font-size:28px;letter-spacing:-.03em}
header p{margin:0;color:#7c8da6;font-size:11px;max-width:620px}
.meta{display:flex;gap:7px;flex-wrap:wrap;justify-content:flex-end}.pill{border:1px solid #d7e5ff;background:#fff;border-radius:20px;padding:5px 10px;font-size:9px;color:#58739a}
.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:28px 26px;justify-content:center;align-items:start}
.item{width:100%;max-width:390px;margin:0 auto}.label{display:flex;align-items:center;gap:6px;margin:0 0 8px 8px;font-size:10px;font-weight:700;color:#526a88}.label span{font:8px ui-monospace,monospace;color:#93a5bb;border:1px solid #d7e5ff;background:#fff;border-radius:4px;padding:1px 5px}
.frame{width:100%;aspect-ratio:390/844;border-radius:34px;background:#f7faff;border:8px solid #0c1728;box-shadow:0 20px 48px rgba(20,45,80,.18);overflow:hidden;position:relative}
.view{height:100%;overflow:hidden;display:flex;flex-direction:column;background:#f7faff;position:relative}
.pg{flex:1;min-height:0;overflow:auto;padding:12px 14px 64px;scrollbar-width:none}.pg::-webkit-scrollbar{display:none}
.status{flex:none;height:28px;display:flex;align-items:flex-end;justify-content:space-between;padding:0 16px 2px;font-size:8px;color:#5b728d;font-weight:700}
/* page primitives */
.ph{display:flex;align-items:flex-end;justify-content:space-between;margin:2px 0 10px}.ph h2{margin:0;font-size:21px;line-height:1.15;letter-spacing:-.03em}.ph h2 small{display:block;font-size:7px;letter-spacing:.16em;color:#97a8bc;font-weight:650;margin-top:3px}.ph .act{display:flex;gap:5px}.ph .act i{width:29px;height:29px;border:1px solid #e1ebf9;background:#fff;border-radius:9px;display:grid;place-items:center;color:#5e748f;font-style:normal;font-size:13px}
.search{height:34px;border:1px solid #e3ebf7;border-radius:10px;background:#fff;display:flex;align-items:center;gap:6px;padding:0 9px;color:#9aabc0;font-size:9px;margin-bottom:8px}
.chips{display:flex;gap:5px;overflow:auto;padding-bottom:3px;margin-bottom:9px;scrollbar-width:none}.chips::-webkit-scrollbar{display:none}.chip{flex:none;height:26px;padding:0 11px;border:1px solid #e3ebf7;background:#fff;border-radius:8px;color:#71859d;font-size:8.5px;display:flex;align-items:center}.chip.on{background:#eef4ff;border-color:#bcd4ff;color:#2563eb;font-weight:700}
.card{background:#fff;border:1px solid #e3ebf7;border-radius:12px;padding:11px;margin-bottom:8px;box-shadow:0 2px 8px rgba(37,99,235,.025)}
.section-title{display:flex;align-items:center;justify-content:space-between;margin:11px 2px 7px;font-size:8.5px;font-weight:750;color:#536b86}.section-title span{font-size:7.5px;font-weight:400;color:#8fa2b8}
.rowline{display:flex;align-items:center;gap:8px;padding:8px 0;border-bottom:1px solid #f0f5fd;font-size:9px;color:#405873}.rowline:last-child{border-bottom:0}.rowline .grow{flex:1;min-width:0}.rowline b{display:block;font-size:9.5px;color:#314a65}.rowline small{display:block;font-size:7.5px;color:#9aabc0;margin-top:1px}.rowline .val{font-size:8px;color:#9aabc0}.rowline .chev{color:#aab8c9;font-size:13px}
.avatar{width:30px;height:30px;border-radius:9px;background:#eef4ff;color:#2563eb;display:grid;place-items:center;font-size:10px;font-weight:800;flex:none}.avatar.bot{background:linear-gradient(145deg,#60a5fa,#2563eb);color:#fff}
.conv{display:flex;gap:9px;align-items:center;padding:8px;border-radius:10px;margin-bottom:2px}.conv.on{background:#fff;border:1px solid #e7efff;box-shadow:0 4px 12px rgba(37,99,235,.05)}.conv .copy{flex:1;min-width:0}.conv .copy b{display:block;font-size:10.5px;color:#2c4560}.conv .copy span{display:block;font-size:8px;color:#8b9bb0;margin-top:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.conv .end{display:flex;flex-direction:column;align-items:flex-end;gap:4px}.conv .when{font-size:7px;color:#a2b2c6}.badge{min-width:15px;height:15px;border-radius:8px;background:#2563eb;color:#fff;font-size:7px;display:grid;place-items:center;padding:0 4px}
.bottom{position:absolute;left:0;right:0;bottom:0;z-index:3;padding:9px 12px 12px;border-top:1px solid #edf2fa;background:#fff}.btn{height:33px;border:1px solid #dbe8ff;background:#fff;color:#2563eb;border-radius:8px;font:9px inherit;display:flex;align-items:center;justify-content:center;gap:5px}.btn.primary{background:#2563eb;border-color:#2563eb;color:#fff;font-weight:700}.btn.danger{color:#b91c1c;border-color:#fecaca;background:#fff5f5}
.two{display:grid;grid-template-columns:1fr 1fr;gap:7px}.three{display:grid;grid-template-columns:repeat(3,1fr);gap:6px}
.tag{display:inline-flex;align-items:center;border:1px solid #dbe8ff;background:#f4f9ff;color:#5f7da2;border-radius:5px;padding:2px 5px;font-size:7px}
.notice{border:1px dashed #d7e6ff;background:#f4f9ff;border-radius:9px;padding:8px 9px;color:#7890aa;font-size:8px;line-height:1.6;margin-bottom:8px}
.note{color:#9aabc0;font-size:7.5px;line-height:1.6;margin-top:7px}
/* chat */
.msg{display:flex;gap:6px;margin-bottom:8px}.msg .b{max-width:78%;padding:7px 9px;border-radius:10px 10px 10px 3px;background:#fff;border:1px solid #e4edfa;font-size:10px;color:#344b64;line-height:1.55}.msg.me{justify-content:flex-end}.msg.me .b{background:#2563eb;border-color:#2563eb;color:#fff;border-radius:10px 10px 3px 10px}.composer{display:flex;gap:5px;align-items:center;border-top:1px solid #e5edf9;padding-top:7px}.composer .inp{flex:1;height:31px;border:1px solid #e1ebf9;border-radius:9px;background:#fff;color:#aab7c8;font-size:9px;display:flex;align-items:center;padding:0 8px}.composer .ic{width:29px;height:29px;border:1px solid #e1ebf9;border-radius:8px;background:#fff;display:grid;place-items:center;color:#6f86a2;font-size:12px}.composer .send{width:31px;height:31px;border:0;border-radius:9px;background:#2563eb;color:#fff;font-size:13px}
/* memory */
.mem-hero{border-radius:14px;padding:13px;background:linear-gradient(135deg,#2563eb,#3b82f6 65%,#38bdf8);color:#fff;margin-bottom:8px;position:relative;overflow:hidden}.mem-hero:after{content:"";position:absolute;width:110px;height:110px;border-radius:50%;right:-30px;top:-45px;background:rgba(255,255,255,.14)}.mem-hero small{font-size:7px;opacity:.8;letter-spacing:.1em}.mem-hero h3{margin:5px 0 3px;font-size:14px;line-height:1.4}.mem-hero p{margin:0;font-size:8px;opacity:.8}.mem-stat{display:flex;gap:13px;margin-top:10px;position:relative;z-index:1}.mem-stat b{display:block;font-size:12px}.mem-stat span{font-size:6.5px;opacity:.7}
.tiles{display:grid;grid-template-columns:1fr 1fr;gap:7px}.tile{background:#fff;border:1px solid #e3ebf7;border-radius:11px;padding:9px}.tile i{display:grid;place-items:center;width:23px;height:23px;border-radius:7px;background:#eef4ff;color:#2563eb;font-style:normal;font-size:11px;margin-bottom:5px}.tile b{display:block;font-size:9px;color:#314a65}.tile span{font-size:7px;color:#9aabc0}
/* relation */
.rel-card{display:flex;gap:10px;align-items:center}.rel-av{width:48px;height:48px;border-radius:14px;background:linear-gradient(145deg,#dbeafe,#eef4ff);display:grid;place-items:center;font-weight:850;color:#2563eb;font-size:15px;flex:none}.rel-name b{display:block;font-size:13px;color:#223b56}.rel-name small{display:block;font-size:7.5px;color:#94a6bb;margin-top:2px}.tier{display:flex;align-items:center;gap:5px;margin-top:5px;font-size:7.5px;color:#6f8299}.tier em{font-style:normal;color:#1f9d6b;border:1px solid #cdeee0;background:#eefbf5;border-radius:4px;padding:1px 4px;font-size:6.5px}.progress{height:6px;border-radius:6px;background:#edf2fa;margin-top:6px;overflow:hidden}.progress i{display:block;height:100%;width:58%;background:linear-gradient(90deg,#60a5fa,#38bdf8)}.event{display:flex;gap:7px;align-items:center;border-bottom:1px solid #f0f5fd;padding:7px 0}.event:last-child{border-bottom:0}.event .dot{width:6px;height:6px;border-radius:50%;background:#60a5fa;flex:none}.event p{margin:0;flex:1;font-size:8.5px;color:#4a6079}.event small{font-size:7px;color:#9dabbd}
/* savings */
.money-hero{border-radius:14px;padding:13px;background:linear-gradient(135deg,#0f172a,#1e3a8a);color:#fff;margin-bottom:8px}.money-hero small{font-size:7px;letter-spacing:.1em;color:#bfdbfe}.money-hero .amt{font-size:20px;font-weight:850;letter-spacing:.08em;margin:4px 0 2px}.money-hero .hint{font-size:7.5px;color:#93c5fd}.money-row{display:flex;align-items:center;gap:8px;padding:8px 0;border-bottom:1px solid #f0f5fd}.money-row:last-child{border-bottom:0}.money-row .t{flex:1}.money-row b{display:block;font-size:9px;color:#334b65}.money-row small{font-size:7px;color:#9aabc0}.money-row em{font-style:normal;font-size:8px;color:#2563eb}
/* weekly */
.week{display:flex;gap:5px;overflow:auto;padding-bottom:3px;margin-bottom:8px;scrollbar-width:none}.week::-webkit-scrollbar{display:none}.day{flex:none;width:42px;border:1px solid #e3ebf7;background:#fff;border-radius:9px;text-align:center;padding:5px 3px}.day.on{background:#2563eb;border-color:#2563eb;color:#fff}.day b{display:block;font-size:8px}.day small{font-size:6px;opacity:.7}.period{display:flex;align-items:center;gap:6px;border:1px solid #e3ebf7;background:#fff;border-radius:9px;padding:7px 8px;margin-bottom:5px}.period .idx{font:7px ui-monospace,monospace;color:#9aabc0;width:18px}.period b{flex:1;font-size:8.5px;color:#405873;font-weight:600}.period small{font-size:7px;color:#9aabc0}.period .dot{width:6px;height:6px;border-radius:50%;background:#cbd5e1}.period.on .dot{background:#2563eb}
/* info */
.stat-grid{display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-bottom:8px}.stat{background:#fff;border:1px solid #e3ebf7;border-radius:10px;padding:8px}.stat small{font-size:7px;color:#9aabc0}.stat b{display:block;font-size:10px;color:#2d4864;margin-top:2px}
/* commands */
.cmd{display:flex;align-items:center;gap:7px;border:1px solid #e3ebf7;background:#fff;border-radius:9px;padding:7px 8px;margin-bottom:5px}.cmd code{font:7.5px ui-monospace,monospace;color:#2563eb;background:#eef4ff;border-radius:4px;padding:2px 5px;min-width:58px}.cmd span{flex:1;font-size:8.5px;color:#405873}.cmd em{font-style:normal;color:#aab8c9;font-size:11px}
/* logs */
.log{display:flex;gap:6px;background:#fff;border:1px solid #e3ebf7;border-radius:8px;padding:6px 7px;margin-bottom:4px;font:7px ui-monospace,monospace;color:#5a7089}.log .lv{flex:none;border-radius:3px;padding:1px 4px;font-size:6.5px;font-weight:700}.log .ok{background:#eefbf5;color:#1f9d6b}.log .warn{background:#fff8e8;color:#b7791f}.log .err{background:#fff0f0;color:#d33}.log span{flex:1;min-width:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
/* home */
.modules{display:grid;grid-template-columns:1fr 1fr;gap:6px}.module{display:flex;align-items:center;gap:7px;border:1px solid #e3ebf7;background:#fff;border-radius:10px;padding:8px}.module i{width:23px;height:23px;border-radius:7px;background:#eef4ff;color:#2563eb;display:grid;place-items:center;font-style:normal;font-size:10px}.module b{font-size:8.5px;color:#314a65}.module small{display:block;font-size:6.5px;color:#9aabc0}
</style>
</head>
<body>
<div class="board">
<header><div><div class="kicker">HOSHINOUMI · MOBILE PAGE DETAIL</div><h1>手机页面细稿 <span style="font-size:12px;color:#8da0b8;font-weight:500">v35.7 返工中</span></h1><p>逐页画到可实现的区块级别：页头、筛选、列表、表单、操作、空状态。先确认页面细稿，再恢复 Vue 实现。</p></div><div class="meta"><span class="pill">设计返工中</span><span class="pill">浏览器视口内</span><span class="pill">非最终数据</span></div></header>
<div class="grid">

<!-- 01 CHATS -->
<div class="item"><div class="label"><b>聊天列表</b><span>01 CHATS</span></div><div class="frame"><div class="view"><div class="status"><span>9:41</span><span>5G ▮</span></div><div class="pg">
<div class="ph"><h2>聊天<small>CHATS</small></h2><div class="act"><i>⌕</i><i>＋</i></div></div>
<div class="search">⌕ 搜索会话 / 记忆 / 命令</div>
<div class="chips"><span class="chip on">全部</span><span class="chip">私聊</span><span class="chip">群聊</span><span class="chip">未读 2</span></div>
<div class="section-title">最近<span>已同步</span></div>
<div class="conv on"><span class="avatar bot">奈</span><span class="copy"><b>奈绪</b><span>你回来啦。今天外面有点冷，先喝点热的吧。</span></span><span class="end"><span class="when">刚刚</span><span class="badge">2</span></span></div>
<div class="conv"><span class="avatar">学</span><span class="copy"><b>星之海学生会</b><span>友利：下午的会议改到三点。</span></span><span class="end"><span class="when">12:40</span><span class="badge">5</span></span></div>
<div class="conv"><span class="avatar">猫</span><span class="copy"><b>猫咪投喂提醒</b><span>今天还没喂猫。</span></span><span class="end"><span class="when">昨天</span></span></div>
<div class="conv"><span class="avatar">记</span><span class="copy"><b>记忆本 · 新增 1 条</b><span>“她记得你不喜欢香菜。”</span></span><span class="end"><span class="when">昨天</span></span></div>
<div class="notice">空状态：暂无会话时显示“后端有消息后会出现在这里”，不伪造会话。</div>
</div></div></div></div>

<!-- 02 PRIVATE CHAT -->
<div class="item"><div class="label"><b>私聊</b><span>02 PRIVATE CHAT</span></div><div class="frame"><div class="view"><div class="status"><span>9:41</span><span>5G ▮</span></div><div class="pg" style="display:flex;flex-direction:column">
<div class="ph" style="align-items:center"><h2 style="font-size:15px">‹ 奈绪<small>在线 · 正在输入…</small></h2><div class="act"><i>⌕</i><i>☰</i></div></div>
<div class="chips"><span class="chip on">关系 · 熟悉</span><span class="chip">记忆已开启</span></div>
<div style="flex:1;overflow:auto">
<div class="msg"><span class="avatar bot" style="width:24px;height:24px">奈</span><span><span class="b">早呀。昨天你睡得很晚，今天要不要把节奏放慢一点？</span><span class="note">09:38</span></span></div>
<div class="msg me"><span><span class="b">嗯，今天没什么安排。</span><span class="note" style="text-align:right">09:40 · 已读</span></span><span class="avatar" style="width:24px;height:24px">你</span></div>
<div class="msg"><span class="avatar bot" style="width:24px;height:24px">奈</span><span><span class="b">那我把下午留给你。想去图书馆，还是就在学生会室待着？</span><span class="note">09:41</span></span></div>
<div class="msg"><span class="avatar bot" style="width:24px;height:24px">奈</span><span><span class="b">学生会室吧。窗外那棵树下，猫应该又会来。</span><span class="tag" style="margin-top:3px">✦ 来自记忆 · 喜欢安静的下午</span><span class="note">09:42</span></span></div>
<div class="note">长按自己消息：撤回 / 复制。图片、语音、表情在输入栏“＋”里。</div>
</div>
<div class="composer"><span class="ic">＋</span><span class="inp">和奈绪说点什么…</span><span class="ic">◉</span><span class="send">↑</span></div>
</div></div></div></div>

<!-- 03 GROUP CHAT -->
<div class="item"><div class="label"><b>群聊</b><span>03 GROUP CHAT</span></div><div class="frame"><div class="view"><div class="status"><span>9:41</span><span>5G ▮</span></div><div class="pg" style="display:flex;flex-direction:column">
<div class="ph" style="align-items:center"><h2 style="font-size:15px">‹ 星之海学生会<small>群聊 · 3 人 · 已同步</small></h2><div class="act"><i>⌕</i><i>☰</i></div></div>
<div class="chips"><span class="chip on">群聊</span><span class="chip">友利 / 奈绪 / 你</span><span class="chip">未读 5</span></div>
<div style="flex:1;overflow:auto">
<div class="msg"><span class="avatar" style="width:24px;height:24px">友</span><span><span class="b">下午的会议改到三点，别迟到。</span><span class="note">12:38</span></span></div>
<div class="msg"><span class="avatar bot" style="width:24px;height:24px">奈</span><span><span class="b">收到。我把资料整理好带过去。</span><span class="note">12:40</span></span></div>
<div class="msg me"><span><span class="b">我也去。需要我带投影仪吗？</span><span class="note" style="text-align:right">12:41 · 已读</span></span><span class="avatar" style="width:24px;height:24px">你</span></div>
<div class="msg"><span class="avatar" style="width:24px;height:24px">友</span><span><span class="b">不用，学生会室有。你人来就行。</span><span class="note">12:42</span></span></div>
<div class="notice">群聊显示成员昵称、@提醒、群公告；不暴露非主人私密记忆。</div>
</div>
<div class="composer"><span class="ic">＋</span><span class="inp">和群友说点什么…</span><span class="ic">@</span><span class="send">↑</span></div>
</div></div></div></div>

<!-- 04 MEMORY -->
<div class="item"><div class="label"><b>记忆</b><span>04 MEMORY</span></div><div class="frame"><div class="view"><div class="status"><span>9:41</span><span>5G ▮</span></div><div class="pg">
<div class="ph"><h2>记忆<small>MEMORY BOOK</small></h2><div class="act"><i>⌕</i><i>⋯</i></div></div>
<div class="mem-hero"><small>最近一条 · 今天</small><h3>“她记得你不喜欢香菜。”</h3><p>从会话里记下的生活偏好，已归入画像。</p><div class="mem-stat"><div><b>28</b><span>记忆本</span></div><div><b>6</b><span>本周新增</span></div><div><b>4</b><span>待确认</span></div></div></div>
<div class="chips"><span class="chip on">记忆本</span><span class="chip">最近事件</span><span class="chip">画像</span><span class="chip">关系记忆</span></div>
<div class="tiles"><div class="tile"><i>▤</i><b>记忆本</b><span>按主题浏览</span></div><div class="tile"><i>◷</i><b>最近事件</b><span>上周 · 学生会</span></div><div class="tile"><i>◉</i><b>她的画像</b><span>偏好 / 习惯</span></div><div class="tile"><i>♡</i><b>关系记忆</b><span>一起经历过</span></div></div>
<div class="section-title">最近记忆<span>全部 ›</span></div>
<div class="card"><div class="rowline"><span class="avatar" style="width:24px;height:24px">记</span><span class="grow"><b>不喜欢香菜</b><small>饮食习惯 · 今天</small></span><span class="tag">偏好</span></div><div class="rowline"><span class="avatar" style="width:24px;height:24px">记</span><span class="grow"><b>喜欢安静的下午</b><small>生活 · 昨天</small></span><span class="tag">生活</span></div><div class="rowline"><span class="avatar" style="width:24px;height:24px">记</span><span class="grow"><b>那棵树下有猫</b><small>学生会室 · 上周</small></span><span class="tag">场景</span></div></div>
<div class="notice">点击记忆进入详情：来源会话 / 时间 / 删除 / 标记重要。非主人 403。</div>
</div></div></div></div>

<!-- 05 RELATION -->
<div class="item"><div class="label"><b>关系</b><span>05 RELATION</span></div><div class="frame"><div class="view"><div class="status"><span>9:41</span><span>5G ▮</span></div><div class="pg">
<div class="ph"><h2>关系<small>RELATION</small></h2><div class="act"><i>⋯</i></div></div>
<div class="card"><div class="rel-card"><span class="rel-av">奈</span><span class="rel-name"><b>奈绪</b><small>认识 286 天 · 最近联系 5 分钟前</small><span class="tier"><em>熟悉</em>还没到下一档</span><span class="progress"><i></i></span></span></div><div class="note">亲近程度只显示档位，不显示具体数值。</div></div>
<div class="section-title">最近的变化</div>
<div class="card"><div class="event"><span class="dot"></span><p>一起准备了学生会周会</p><small>2 天前</small></div><div class="event"><span class="dot" style="background:#a78bfa"></span><p>你记住了她喜欢安静的地方</p><small>昨天</small></div><div class="event"><span class="dot" style="background:#34d399"></span><p>她主动问你今天累不累</p><small>5 分钟前</small></div></div>
<div class="notice">🔒 关系与记忆仅主人可见；非主人访问返回 403，不展示金额或私密内容。</div>
<div class="section-title">关系设置</div>
<div class="card"><div class="rowline"><span class="grow">显示范围</span><span class="val">仅自己</span></div><div class="rowline"><span class="grow">关系变化提醒</span><span class="val">开启</span></div></div>
</div></div></div></div>

<!-- 06 SAVINGS -->
<div class="item"><div class="label"><b>存钱</b><span>06 SAVINGS</span></div><div class="frame"><div class="view"><div class="status"><span>9:41</span><span>5G ▮</span></div><div class="pg">
<div class="ph"><h2>存钱<small>SAVINGS</small></h2><div class="act"><i>＋</i></div></div>
<div class="money-hero"><small>总余额 · 仅主人可见</small><div class="amt">••••••</div><div class="hint">金额默认隐藏，点按可切换显示</div></div>
<div class="chips"><span class="chip on">总览</span><span class="chip">账户</span><span class="chip">目标</span><span class="chip">定期</span><span class="chip">基金</span><span class="chip">冻结</span></div>
<div class="section-title">账户<span>4 个</span></div>
<div class="card"><div class="money-row"><span class="avatar" style="width:24px;height:24px">银</span><span class="t"><b>银行卡</b><small>日常账户</small></span><em>••••</em></div><div class="money-row"><span class="avatar" style="width:24px;height:24px">现</span><span class="t"><b>现金</b><small>钱包</small></span><em>••••</em></div></div>
<div class="section-title">目标 / 定期<span>查看全部</span></div>
<div class="card"><div class="money-row"><span class="avatar" style="width:24px;height:24px">目</span><span class="t"><b>旅行目标</b><small>进度 60%</small></span><em>进行中</em></div><div class="money-row"><span class="avatar" style="width:24px;height:24px">冻</span><span class="t"><b>冻结记录</b><small>不计入余额</small></span><em>查看</em></div></div>
<div class="bottom"><div class="two"><button class="btn primary">＋ 记一笔</button><button class="btn">切换金额显示</button></div></div>
</div></div></div></div>

<!-- 07 WEEKLY -->
<div class="item"><div class="label"><b>周计划</b><span>07 WEEKLY</span></div><div class="frame"><div class="view"><div class="status"><span>9:41</span><span>5G ▮</span></div><div class="pg">
<div class="ph"><h2>周计划<small>WEEKLY PLAN</small></h2><div class="act"><i>＋</i><i>⋯</i></div></div>
<div class="week"><div class="day"><b>一</b><small>16</small></div><div class="day on"><b>二</b><small>17</small></div><div class="day"><b>三</b><small>18</small></div><div class="day"><b>四</b><small>19</small></div><div class="day"><b>五</b><small>20</small></div><div class="day"><b>六</b><small>21</small></div><div class="day"><b>日</b><small>22</small></div></div>
<div class="section-title">节次<span>点击切换完成</span></div>
<div class="period on"><span class="idx">01</span><b>学生会例会</b><small>08:30–09:15</small><span class="dot"></span></div>
<div class="period on"><span class="idx">02</span><b>英语</b><small>10:00–11:35</small><span class="dot"></span></div>
<div class="period"><span class="idx">03</span><b>午休</b><small>12:00–13:00</small><span class="dot"></span></div>
<div class="period"><span class="idx">04</span><b>自习</b><small>15:00–17:00</small><span class="dot"></span></div>
<div class="notice">新增节次：名称 / 开始结束 / 备注。空状态提示“本周还没有计划”。</div>
</div><div class="bottom"><button class="btn primary">＋ 新增节次</button></div></div></div></div>

<!-- 08 INFO -->
<div class="item"><div class="label"><b>信息</b><span>08 INFO</span></div><div class="frame"><div class="view"><div class="status"><span>9:41</span><span>5G ▮</span></div><div class="pg">
<div class="ph"><h2>信息<small>INFO</small></h2><div class="act"><i>↻</i></div></div>
<div class="stat-grid"><div class="stat"><small>版本</small><b>v35.7</b></div><div class="stat"><small>连接</small><b>已连接</b></div><div class="stat"><small>数据库</small><b>SQLite</b></div><div class="stat"><small>延迟</small><b>—</b></div></div>
<div class="section-title">运行</div>
<div class="card"><div class="rowline"><span class="grow">运行状态</span><span class="tag">正常</span></div><div class="rowline"><span class="grow">定时任务</span><span class="val">3 个</span><span class="chev">›</span></div><div class="rowline"><span class="grow">运行日志</span><span class="chev">›</span></div></div>
<div class="section-title">数据 / 阅读</div>
<div class="card"><div class="rowline"><span class="grow">数据库 / schema</span><span class="val">schema 35</span></div><div class="rowline"><span class="grow">记忆 / 关系</span><span class="val">已连接</span></div><div class="rowline"><span class="grow">阅读 / 小说</span><span class="chev">›</span></div></div>
<div class="notice">所有耗时、版本、schema 从 /api/status 拉取，不写死；失败显示错误。</div>
</div></div></div></div>

<!-- 09 PERSONA -->
<div class="item"><div class="label"><b>人设</b><span>09 PERSONA</span></div><div class="frame"><div class="view"><div class="status"><span>9:41</span><span>5G ▮</span></div><div class="pg">
<div class="ph"><h2>人设<small>PERSONA</small></h2><div class="act"><i>⇧</i><i>⇩</i></div></div>
<div class="card"><div class="rel-card"><span class="rel-av">奈</span><span class="rel-name"><b>奈绪 · 默认</b><small>星之海学生会 · 友利奈绪</small><span class="tier"><em>使用中</em>当前人设</span></span></div></div>
<div class="section-title">其他人设</div>
<div class="card"><div class="rowline"><span class="avatar">夏</span><span class="grow"><b>暑假奈绪</b><small>更放松 / 日常</small></span><span class="tag">切换</span></div><div class="rowline"><span class="avatar">会</span><span class="grow"><b>学生会长</b><small>正式 / 工作模式</small></span><span class="tag">切换</span></div></div>
<div class="notice">切换只更新当前人设，记忆与关系复用后端；导入人设卡需确认覆盖。</div>
<div class="bottom"><div class="two"><button class="btn">导入</button><button class="btn">导出当前</button></div></div>
</div></div></div></div>

<!-- 10 COMMANDS -->
<div class="item"><div class="label"><b>命令</b><span>10 COMMANDS</span></div><div class="frame"><div class="view"><div class="status"><span>9:41</span><span>5G ▮</span></div><div class="pg">
<div class="ph"><h2>命令<small>COMMANDS</small></h2><div class="act"><i>?</i></div></div>
<div class="search">⌕ 搜索命令 / 参数</div>
<div class="chips"><span class="chip on">全部</span><span class="chip">聊天</span><span class="chip">记忆</span><span class="chip">存钱</span><span class="chip">系统</span></div>
<div class="section-title">常用<span>51 个命令</span></div>
<div class="cmd"><code>!help</code><span>查看全部命令</span><em>›</em></div>
<div class="cmd"><code>!memory</code><span>搜索记忆</span><em>›</em></div>
<div class="cmd"><code>!savings</code><span>记录收支</span><em>›</em></div>
<div class="cmd"><code>!run</code><span>执行工具</span><em>›</em></div>
<div class="cmd"><code>!status</code><span>运行状态</span><em>›</em></div>
<div class="notice">点命令打开详情：用法 / 参数 / 二级命令 / 权限；执行结果不伪造。</div>
</div></div></div></div>

<!-- 11 CRON -->
<div class="item"><div class="label"><b>定时任务</b><span>11 CRON</span></div><div class="frame"><div class="view"><div class="status"><span>9:41</span><span>5G ▮</span></div><div class="pg">
<div class="ph"><h2>定时任务<small>CRON</small></h2><div class="act"><i>＋</i></div></div>
<div class="card"><div class="rowline"><span class="grow"><b>早安问候</b><small>每天 07:30 · 下次 明天</small></span><span class="tag">启用</span></div><div class="rowline"><span class="grow"><b>每周计划提醒</b><small>周日 20:00</small></span><span class="tag">启用</span></div><div class="rowline"><span class="grow"><b>猫粮提醒</b><small>每天 18:00</small></span><span class="tag" style="color:#9aabc0">暂停</span></div></div>
<div class="notice">新增：名称 / cron 表达式 / 时区 / 动作 / 是否启用。危险操作需确认。</div>
<div class="bottom"><div class="two"><button class="btn primary">新增任务</button><button class="btn">立即执行一次</button></div></div>
</div></div></div></div>

<!-- 12 LOGS -->
<div class="item"><div class="label"><b>运行日志</b><span>12 LOGS</span></div><div class="frame"><div class="view"><div class="status"><span>9:41</span><span>5G ▮</span></div><div class="pg">
<div class="ph"><h2>运行日志<small>LOGS</small></h2><div class="act"><i>⌕</i></div></div>
<div class="chips"><span class="chip on">全部</span><span class="chip">INFO</span><span class="chip">WARN</span><span class="chip">ERROR</span></div>
<div class="log"><span class="lv ok">INFO</span><span>gateway started · 127.0.0.1:27005</span></div>
<div class="log"><span class="lv ok">INFO</span><span>/api/history 200 · 82ms</span></div>
<div class="log"><span class="lv warn">WARN</span><span>memory recall empty fallback</span></div>
<div class="log"><span class="lv ok">INFO</span><span>/api/chat 200 · 1.2s</span></div>
<div class="log"><span class="lv err">ERR</span><span>weather provider timeout (fallback)</span></div>
<div class="log"><span class="lv ok">INFO</span><span>weekly plan refreshed</span></div>
<div class="notice">日志一行一条，支持级别筛选和搜索；失败不隐藏。</div>
</div></div></div></div>

<!-- 13 SETTINGS -->
<div class="item"><div class="label"><b>设置</b><span>13 SETTINGS</span></div><div class="frame"><div class="view"><div class="status"><span>9:41</span><span>5G ▮</span></div><div class="pg">
<div class="ph"><h2>设置<small>SETTINGS</small></h2></div>
<div class="card"><div class="rowline"><span class="avatar">徐</span><span class="grow"><b>徐梓腾</b><small>主人账号 · 已连接</small></span><span class="chev">›</span></div></div>
<div class="section-title">连接与界面</div>
<div class="card"><div class="rowline"><span class="grow">底部快捷栏</span><span class="val">聊天 / 记忆 / 关系 / 设置</span><span class="chev">›</span></div><div class="rowline"><span class="grow">后端连接</span><span class="val">已连接</span></div><div class="rowline"><span class="grow">外观</span><span class="val">跟随系统</span></div><div class="rowline"><span class="grow">消息通知</span><span class="val">开启</span></div></div>
<div class="section-title">隐私与数据</div>
<div class="card"><div class="rowline"><span class="grow">记忆</span><span class="val">开启</span></div><div class="rowline"><span class="grow">关系显示范围</span><span class="val">仅自己</span></div><div class="rowline"><span class="grow">数据导出</span><span class="chev">›</span></div></div>
<div class="bottom"><button class="btn danger">退出登录</button></div>
</div></div></div></div>

<!-- 14 HOME -->
<div class="item"><div class="label"><b>主页</b><span>14 HOME</span></div><div class="frame"><div class="view"><div class="status"><span>9:41</span><span>5G ▮</span></div><div class="pg">
<div class="ph"><h2>主页<small>HOME</small></h2><div class="act"><i>⚙</i></div></div>
<div class="mem-hero"><small>下午好 · 学生会长</small><h3>今天也慢慢来。</h3><p>10 个功能模块入口，数据来自后端。</p></div>
<div class="modules">
<div class="module"><i>◉</i><span><b>聊天</b><small>会话 / 消息</small></span></div><div class="module"><i>◇</i><span><b>记忆</b><small>记忆本 / 事件</small></span></div><div class="module"><i>♡</i><span><b>关系</b><small>档位 / 变化</small></span></div><div class="module"><i>¥</i><span><b>存钱</b><small>账户 / 目标</small></span></div><div class="module"><i>▦</i><span><b>周计划</b><small>节次 / 时间</small></span></div><div class="module"><i>i</i><span><b>信息</b><small>运行 / 数据库</small></span></div><div class="module"><i>◈</i><span><b>人设</b><small>导入 / 激活</small></span></div><div class="module"><i>⌘</i><span><b>命令</b><small>51 个命令</small></span></div><div class="module"><i>◷</i><span><b>定时任务</b><small>启停 / 执行</small></span></div><div class="module"><i>≡</i><span><b>运行日志</b><small>筛选 / 搜索</small></span></div>
</div>
</div></div></div></div>

</div>
<div style="max-width:1320px;margin:20px auto 0;padding:12px 16px;border:1px dashed #cfdfff;background:rgba(255,255,255,.55);border-radius:10px;color:#7188a3;font-size:9.5px;line-height:1.7">细稿说明：本页只画浏览器视口内页面内容；顶部地址栏、底部浏览器工具栏由真实手机浏览器提供。所有金额默认隐藏，仅主人可见；非主人不展示私密记忆、关系和财务数据。</div>
</div>
</body>
</html>

// Hoshinoumi Web v35.5 · MOCK 交互演示（无后端）
(() => {
  const CHATS = {
    nao: { name: '友利奈绪', sub: '私聊 · 记忆同步', msgs: [
      { r: 'bot', t: '你回来啦。今天外面有点冷，先喝点热的吧。', m: '20:58 · 已读' },
      { r: 'me', t: '刚到家。今天那个方案终于过了。', m: '21:00 · 已读' },
      { r: 'bot', t: '那很好啊。你上次说怕过不了，我还记着呢。要不要把这件事记进“今天值得高兴的事”？', m: '21:01 · 记忆已更新', mem: '关联记忆 · 方案汇报 · 11 月 19 日' },
      { r: 'me', t: '好。顺便帮我看下这个月还剩多少。', m: '21:03 · 已读' },
      { r: 'bot', t: '本月收入 ¥8,000，支出 ¥3,200，存钱 ¥1,500，结余 ¥3,300。旅行目标已经 60% 了。', m: '21:03 · 财务摘要（仅主人私聊）' },
      { r: 'bot', t: '不过我想先听你说说方案过的时候，是什么感觉。', m: '21:04 · 已读' }
    ] },
    seagroup: { name: '星之海学园', sub: 'QQ 群 · 12 人 · 已同步', msgs: [
      { r: 'bot', a: '星', t: '晚上的教室灯又没关。谁最后走的？', m: '20:41 · 星之海学园' },
      { r: 'me', t: '我走的时候关了，可能后来又有人进去。', m: '20:43 · 已读' },
      { r: 'bot', a: '奈', t: '我去看看吧。你们先回去，别在楼下等。', m: '20:44 · 已读' }
    ] },
    student: { name: '学生会室', sub: 'QQ 群 · 8 人 · 已同步', msgs: [
      { r: 'bot', a: '学', t: '明天放学后开个短会，十分钟。', m: '19:58 · 学生会室' },
      { r: 'me', t: '收到，我会到。', m: '19:59 · 已读' },
      { r: 'bot', a: '奈', t: '那我把上次的活动记录带过去。', m: '20:00 · 已读' }
    ] },
    photo: { name: '摄影部', sub: 'QQ 群 · 6 人 · 已同步', msgs: [
      { r: 'bot', a: '摄', t: '周末去海边拍吗？天气看起来不错。', m: '昨天 · 摄影部' },
      { r: 'me', t: '可以，早上几点？', m: '昨天 · 已读' },
      { r: 'bot', a: '摄', t: '七点校门口，带长焦。', m: '昨天 · 已读' }
    ] },
    test: { name: 'NapCat 测试群', sub: 'QQ 群 · 3 人 · 已同步', msgs: [
      { r: 'bot', a: '测', t: '消息同步测试：收到请回复。', m: '昨天 · NapCat 测试群' },
      { r: 'me', t: '收到。', m: '昨天 · 已读' },
      { r: 'bot', a: '奈', t: '收到。同步正常。', m: '昨天 · 已读' }
    ] }
  };

  const PAGES = {
    home: [['运行状态', 'running · schema 35'], ['记忆账号', '2 个 target'], ['本周课程', '3 门'], ['快捷', '聊天 / 记忆 / 存钱 / 周计划']],
    info: [['后端', '127.0.0.1:27004 · 42ms'], ['数据库', '已连接 · schema 35'], ['记忆 / 事件', '4 / 7'], ['学习计划', '已读取']],
    commands: [['!ping', '在线测试'], ['!status', '运行状态'], ['!memory', '记忆查询'], ['!logs', '最近日志']],
    cron: [['每日早报', '08:00 · 启用'], ['日记提醒', '22:30 · 启用'], ['健康检查', '每小时 · 停用'], ['下一次', '明天 08:00']],
    logs: [['09:13 INFO chat', 'len=18'], ['09:12 INFO command', 'status'], ['09:04 WARN search_images', 'timeout'], ['08:58 INFO memory', 'append']],
    memory: [['记忆本', '最近 7 天 · 4 条'], ['今天值得高兴的事', '方案通过 · 已写入长期记忆'], ['你不喜欢太吵的地方', '偏好安静 · 来自对话'], ['正在读', '《十日终焉》 · 窗边']],
    savings: [['总余额', '¥3,300.00'], ['本月收入', '¥8,000'], ['本月支出', '¥3,200'], ['旅行目标', '60% · 还差 ¥2,200']],
    weekly: [['本周', '3 门课'], ['周一 1-2 节', '高等数学 · 教三 201'], ['周三 3-4 节', '大学英语 · 文科楼 104'], ['周五 5-6 节', '数据结构 · 实验楼 302']],
    persona: [['当前人设', 'nao · 友利奈绪'], ['风格', '口语 · 简短 · 行动回复'], ['文件', 'prompt / life / supplement / state / voice'], ['状态', '只读预览 · 仅 owner']],
    relation: [['关系档位', '熟'], ['最近变化', '有更新 · 聊天'], ['可见范围', '仅 owner 全量；普通用户只看自己']],
    settings: [['后端地址', 'http://127.0.0.1:27004'], ['连接状态', '已连接 · schema 35'], ['主人 QQ', '未配置'], ['视觉', '深色 · 动画默认关闭']],
    plugins: [['已安装', '0 个'], ['权限', '只读优先'], ['审批', '安装前确认'], ['状态', 'MOCK 演示']]
  };
  const COMMAND_META = {
    '!memory': { usage: '!memory <me|QQ号> [页码]', args: 'me / QQ号 / 页码', required: true },
    '!memorybook': { usage: '!memorybook [页码]', args: '页码（可选）', required: false },
    '!event': { usage: '!event <today|week|all>', args: 'today / week / all', required: true },
    '!persona': { usage: '!persona <list|activate|import> [名字]', args: 'list / activate / import', sub: ['list', 'activate', 'import'], required: true },
    '!backup': { usage: '!backup run', args: 'run', required: true },
    '!update': { usage: '!update <status|latest|apply>', args: 'status / latest / apply', sub: ['status', 'latest', 'apply'], required: true },
    '!config': { usage: '!config <get|set> [键] [值]', args: 'get / set / 键 / 值', sub: ['get', 'set'], required: true },
    '!say': { usage: '!say <内容>', args: '文本内容', required: true },
    '!sayg': { usage: '!sayg <群号> <内容>', args: '群号 / 内容', required: true },
    '!adduser': { usage: '!adduser <QQ号>', args: 'QQ号', required: true },
    '!route': { usage: '!route <status|reset>', args: 'status / reset', required: false }
  };

  function currentIsoWeek() {
    const d = new Date(Date.UTC(new Date().getFullYear(), new Date().getMonth(), new Date().getDate()))
    const day = d.getUTCDay() || 7
    d.setUTCDate(d.getUTCDate() + 4 - day)
    const start = new Date(Date.UTC(d.getUTCFullYear(), 0, 1))
    return Math.ceil((((d.getTime() - start.getTime()) / 86400000) + 1) / 7)
  }

  const COMMAND_GROUPS = {
    '基础': ['!help','!ping','!status','!version','!uptime','!meta','!usage','!log','!db','!stats','!history','!reload','!set','!exit','!quit'],
    '记忆': ['!memory','!memorybook','!event','!keywords','!clear','!profile','!growth','!relation'],
    '媒体': ['!img','!acg','!sticker','!clip','!voice','!vision','!say','!sayg'],
    '日常': ['!diary','!todo','!cron','!hooks','!backup','!update','!task'],
    '阅读': ['!books','!book'],
    '计划': ['!plan'],
    '插件': ['!plugin'],
    '账号': ['!adduser','!persona'],
    '多端': ['!doing','!presence','!route','!gw','!config','!code','!apikeys']
  };

  const TITLES = { home: '主页', memory: '记忆', savings: '存钱', weekly: '周计划表', persona: '人设', relation: '关系', info: '信息', commands: '命令', cron: '定时任务', logs: '运行日志', diary: '日记', settings: '设置', plugins: '插件' };

  // 注入演示用样式
  const css = document.createElement('style');
  css.textContent = `
    .chat-hide{display:none!important}
    .page-view{display:none;flex:1;min-height:0;max-height:100%;overflow-y:auto;overflow-x:hidden;overscroll-behavior:contain;padding:22px 24px;background:#fff;color:#17263b}
    .page-view.on{display:block}
    .page-head{display:flex;align-items:center;gap:12px;margin-bottom:16px}
    .page-head h2{font-size:17px;margin:0;font-weight:650;color:#17263b}
    .page-head p{font-size:10.5px;color:#6b7c95;margin:3px 0 0}
    .back{margin-left:auto;font-size:10px;color:#2563eb;border:1px solid #dbe8ff;border-radius:8px;padding:5px 9px;background:#fff;cursor:pointer;transition:background .18s}
    .mem-stats{display:grid;grid-template-columns:repeat(4,1fr);gap:9px;margin-bottom:11px}.mem-stat{border:1px solid #e3ebf7;border-radius:10px;background:#fff;padding:10px 12px}.mem-stat .k{font-size:8.5px;color:#8a9bb0}.mem-stat .v{font-size:16px;font-weight:700;color:#2563eb;margin-top:2px}.mem-layout{display:grid;grid-template-columns:1.45fr 1fr;gap:10px}.mem-list{display:grid;gap:7px}.mem-card{border:1px solid #e3ebf7;border-radius:10px;background:#fff;padding:10px 12px}.mem-top{display:flex;align-items:center;gap:6px}.mem-top b{font-size:10.5px;color:#1e3a5f}.mem-top .mem-date{margin-left:auto;font-size:8px;color:#8a9bb0}.mem-text{font-size:10px;color:#405872;line-height:1.65;margin:5px 0}.mem-meta{display:flex;align-items:center;gap:5px;flex-wrap:wrap}.mem-tag{font-size:7.5px;color:#2563eb;background:#eef4ff;border:1px solid #dbe8ff;border-radius:4px;padding:1px 4px}.mem-tag.long{color:#168b63;background:#edfbf4;border-color:#d4f2e5}.mem-tag.lock{color:#b23b52;background:#fff5f7;border-color:#f0d7dd}.mem-src{font-size:8px;color:#8a9bb0}.mem-side{display:grid;gap:10px}.mem-panel{border:1px solid #e3ebf7;border-radius:10px;background:#fff;padding:11px 12px}.mem-panel h3{font-size:10px;color:#1e3a5f;margin:0 0 7px}.mem-event{display:flex;gap:7px;padding:6px 0;border-bottom:1px solid #f1f5fb;font-size:9px;color:#405872}.mem-event:last-child{border-bottom:0}.mem-event i{width:5px;height:5px;border-radius:50%;background:#2563eb;margin-top:4px;flex:none}.mem-event small{display:block;color:#8a9bb0;font-size:8px;margin-top:1px}.mem-chips{display:flex;flex-wrap:wrap;gap:4px}.mem-chips span{font-size:8px;color:#4d6683;background:#f8fbff;border:1px solid #dbe8ff;border-radius:10px;padding:2px 6px}.mem-profile{font-size:9px;color:#405872;line-height:1.7}.mem-profile b{color:#1e3a5f}.rel-page{display:grid;grid-template-columns:1.6fr 1fr;gap:10px}.rel-card{border:1px solid #e3ebf7;border-radius:12px;background:#fff;padding:14px}.rel-card.wide{grid-column:span 2}.rel-k{font-size:9px;letter-spacing:.12em;color:#8a9bb0;text-transform:uppercase}.rel-tier{font-size:21px;font-weight:700;color:#2563eb;margin:7px 0 8px}.rel-bar{height:5px;border-radius:5px;background:#e8effa;overflow:hidden}.rel-bar i{display:block;height:100%;border-radius:5px;background:linear-gradient(90deg,#6ea4ff,#2563eb)}.rel-v{font-size:13px;color:#1e3a5f;margin:8px 0 4px}.rel-note{font-size:9.5px;color:#8a9bb0;margin-top:6px;line-height:1.6}.rel-events .rel-event{display:flex;justify-content:space-between;border-bottom:1px solid #f1f5fb;padding:7px 0;font-size:10px;color:#405872}.rel-events .rel-event:last-child{border-bottom:0}.rel-event small{color:#8a9bb0}.pgrid{display:grid;grid-template-columns:1fr 1fr;gap:10px}
    .pcard2{border:1px solid #e3ebf7;border-radius:12px;background:#fff;padding:12px 13px;transition:border-color .18s,transform .18s,box-shadow .18s}
    .diary-page{color:#17263b}
    .diary-page .page-head h2{color:#17263b}
    .diary-page .page-head p{color:#6b7c95}
    .diary-page .diary-months{display:flex;gap:8px;margin:0 0 12px;flex-wrap:wrap}
    .diary-page .diary-months button{border:1px solid #e3ebf7;background:#fff;color:#526982;border-radius:8px;padding:6px 12px;font-size:10px;cursor:pointer}
    .diary-page .diary-months button.on{background:#eef4ff;border-color:#c7dcff;color:#2563eb;font-weight:700}
    .diary-page .pcard2{background:#fff;border:1px solid #e3ebf7;border-radius:12px;padding:14px 16px;box-shadow:0 2px 8px rgba(37,99,235,.03)}
    .diary-page .pcard2 h3{font-size:13px;margin:0 0 4px;color:#1e3a5f}
    .diary-page .pcard2 p{font-size:10px;line-height:1.7;color:#526982}
    .diary-page .pcard2 p[style*="color:#2563eb"]{color:#2563eb!important;font-weight:600}
    .diary-page .pgrid{grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}
    .pcard2 h3{font-size:11px;margin:0 0 5px;color:#dbe8fb}
    .plugin-section h3{color:#1e3a5f}
    .plugin-card{display:flex;align-items:center;gap:12px;padding:10px 0;border-bottom:1px solid #f1f5fb}
    .plugin-card:last-child{border-bottom:0}
    .plugin-copy{flex:1;min-width:0}
    .plugin-copy h3{font-size:11px;color:#1e3a5f;margin:0 0 3px}
    .plugin-copy p{font-size:9px;color:#8a9bb0;margin:0}
    .plugin-action{flex:none;height:28px;border:1px solid #dbe8ff;border-radius:14px;background:#f4f9ff;color:#2563eb;font-size:9px;padding:0 12px;cursor:pointer}
    .plugin-action.primary{background:#2563eb;border-color:#2563eb;color:#fff}
    .plugin-action.danger{background:#fff5f5;border-color:#fecaca;color:#b91c1c}
    .plugin-actions{display:flex;gap:6px;flex:none}
    .plugin-line{display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid #f1f5fb;font-size:9px;color:#526982}
    .plugin-line b{color:#8a9bb0;font-weight:400}
    .pcard2 p{font-size:10px;line-height:1.6;color:var(--muted);margin:0}
    .toast{position:fixed;left:50%;bottom:26px;transform:translateX(-50%) translateY(12px);opacity:0;pointer-events:none;z-index:30;transition:.2s;background:#fff;border:1px solid #dbe8ff;color:#243b55;font-size:10.5px;border-radius:9px;padding:8px 13px;box-shadow:0 10px 24px rgba(37,99,235,.12)}
    .toast.on{opacity:1;transform:translateX(-50%) translateY(0)}
    .typing{color:#8a9bb0;font-size:10px;padding:3px 4px 8px}
    .cmd-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px}
    .cmd-group{border:1px solid #e3ebf7;border-radius:12px;background:#fff;padding:11px 12px;transition:border-color .18s,transform .18s,box-shadow .18s}
    .cmd-group:hover{border-color:#bcd4f7;transform:translateY(-2px);box-shadow:0 8px 18px rgba(37,99,235,.06)}
    .cmd-group h3{display:flex;align-items:center;font-size:11px;color:#1e3a5f;margin:0 0 7px}
    .cmd-group h3 span{margin-left:auto;font-weight:400;color:#93a3b8;font-size:9px}
    .cmd-chips{display:flex;flex-wrap:wrap;gap:5px}
    .cmd-chip{border:1px solid #e3ebf7;border-radius:6px;background:#f8fbff;color:#4b5f78;font-size:9px;padding:4px 7px;cursor:pointer;transition:background .16s,color .16s,border-color .16s,transform .16s}
    .cmd-chip:hover{background:#eef4ff;color:#2563eb;border-color:#bcd4f7;transform:translateY(-1px)}
    .cmd-chip.owner:after{content:' owner';color:#c0264a;font-size:8px}
    .cmd-page{display:flex;flex-direction:column;height:100%;min-height:0}
    .cmd-catalog{flex:1;min-height:0;overflow:auto;padding-right:2px}
    .cmd-result{flex:none;height:40%;min-height:150px;border-top:1px solid #e3ebf7;margin-top:10px;padding-top:10px;display:flex;flex-direction:column}
    .cmd-result-head{display:flex;align-items:center;gap:8px;margin-bottom:6px;font-size:10px;color:#6b7c95}
    .cmd-result-head b{color:#1e3a5f;font-size:10.5px;font-weight:600}
    .cmd-result-head .st{margin-left:auto;color:#93a3b8;font-size:9.5px}
    .cmd-output{flex:1;min-height:0;overflow:auto;border:1px solid #e3ebf7;border-radius:9px;background:#f8fbff;padding:9px 10px;color:#4b5f78;font:10px/1.6 "Cascadia Code","Consolas",monospace;white-space:pre-wrap}
    .cmd-output .cmdline{color:#2563eb;margin-bottom:4px}
    .cmd-chip.on{background:#dbeafe;color:#1d4ed8;border-color:#93b7fa}
    .home-head{display:flex;align-items:center;gap:9px;margin-bottom:6px}
    .home-head h2{font-size:18px;margin:0;color:#17263b}
    .home-pill{font-size:9px;color:#1d4ed8;border:1px solid #dbe8ff;background:#eef4ff;border-radius:20px;padding:3px 8px}
    .home-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-top:13px}
    .home-card{border:1px solid #e3ebf7;border-radius:12px;background:#fff;padding:13px;cursor:pointer;transition:border-color .18s,transform .18s,box-shadow .18s}
    .home-card:hover{border-color:#bcd4f7;transform:translateY(-2px);box-shadow:0 8px 18px rgba(37,99,235,.07)}
    .home-ico{width:22px;height:22px;border-radius:7px;display:grid;place-items:center;background:#eef4ff;color:#2563eb;font-size:12px;margin-bottom:8px}
    .home-card h3{font-size:11px;margin:0 0 3px;color:#1e3a5f}
    .home-card p{font-size:9.5px;line-height:1.5;color:#6b7c95;margin:0}
    .home-card .st{font-size:9px;color:#1f9d6b;margin-top:7px}
    .panel-head{display:flex;align-items:center;justify-content:space-between;gap:8px;margin-bottom:9px}.panel-head h3{margin:0}.mini-add{border:1px solid #dbe8ff;background:#f8fbff;color:#2563eb;border-radius:6px;padding:3px 7px;font:9px inherit;cursor:pointer}.mini-add:hover{background:#eef4ff}.savings-modal{position:fixed;inset:0;background:rgba(15,32,55,.28);backdrop-filter:blur(3px);z-index:60;display:grid;place-items:center}.savings-modal .box{width:320px;background:#fff;border:1px solid #e3ebf7;border-radius:12px;box-shadow:0 20px 50px rgba(30,60,100,.2);padding:15px}.savings-modal h3{margin:0 0 10px;font-size:13px;color:#17263b}.savings-modal label{display:block;font-size:9px;color:#8a9bb0;margin-bottom:7px}.savings-modal input,.savings-modal select{display:block;width:100%;border:1px solid #dbe8ff;border-radius:7px;background:#f8fbff;color:#243b55;font:10.5px inherit;padding:6px 7px;margin-top:3px;outline:0}.savings-modal .check{display:flex;align-items:center;gap:6px;font-size:9px;color:#6b7c95}.savings-modal .check input{width:auto;margin:0;display:inline}.savings-modal .row{display:grid;grid-template-columns:1fr 1fr;gap:7px}.form-error{color:#b23b52;font-size:9px;min-height:12px;margin-top:6px;line-height:1.4}.savings-modal .acts{display:flex;gap:6px;margin-top:10px}.savings-modal .acts button{flex:1;border:1px solid #dbe8ff;border-radius:7px;background:#fff;color:#2563eb;padding:6px;font:10px inherit;cursor:pointer}.savings-modal .acts button.primary{background:#2563eb;color:#fff;border-color:#2563eb}.fixed-card{border:1px solid #e3ebf7;border-radius:10px;background:#fff;padding:10px 12px;display:flex;align-items:center;gap:12px}.fixed-card .main{flex:1}.fixed-card .name{font-size:11px;color:#1e3a5f;font-weight:600}.fixed-card .meta{font-size:8.5px;color:#8a9bb0;margin-top:3px}.fixed-card .val{text-align:right}.fixed-card .val b{font-size:13px;color:#2563eb}.fixed-card .val small{display:block;font-size:8px;color:#8a9bb0;margin-top:2px}.fund-row{display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid #f1f5fb;padding:8px 0;font-size:10px}.fund-row:last-child{border-bottom:0}.fund-name{color:#1e3a5f;font-weight:600}.fund-tag{font-size:7.5px;color:#2563eb;background:#eef4ff;border:1px solid #dbe8ff;border-radius:4px;padding:1px 4px;font-weight:400;margin-left:3px}.fund-meta{font-size:8.5px;color:#8a9bb0;margin-top:2px}.fund-value{text-align:right;color:#2563eb;font-family:ui-monospace,monospace;font-size:12px}.fund-value small{display:block;color:#8a9bb0;font-size:8px;margin-top:2px}.fixed-acts{display:flex;gap:4px;margin-top:5px;justify-content:flex-end}.fixed-acts button{border:1px solid #dbe8ff;background:#f8fbff;color:#2563eb;border-radius:5px;padding:2px 5px;font:8px inherit;cursor:pointer}.fixed-acts button.cancel{border-color:#f0d7dd;color:#b23b52;background:#fff}.fixed-acts button:hover{background:#eef4ff}.fixed-lock{font-size:8px;color:#b7791f;background:#fff8e6;border:1px solid #f2d491;border-radius:4px;padding:1px 4px;margin-left:4px}.savings-goals{display:grid;grid-template-columns:repeat(3,1fr);gap:9px;margin-bottom:10px}.goal-card{border:1px solid #e3ebf7;border-radius:11px;background:#fff;padding:11px 12px}.goal-top{display:flex;align-items:center;justify-content:space-between;gap:6px}.goal-top b{font-size:11px;color:#1e3a5f}.goal-top span{font-size:8.5px;color:#8a9bb0}.goal-amt{font-size:15px;font-weight:700;color:#2563eb;margin:6px 0 2px}.goal-amt small{font-size:9px;color:#8a9bb0;font-weight:400}.gbar{height:5px;border-radius:5px;background:#e8effa;overflow:hidden;margin:6px 0 4px}.gbar i{display:block;height:100%;border-radius:5px;background:linear-gradient(90deg,#6ea4ff,#2563eb)}.goal-foot{display:flex;justify-content:space-between;font-size:8.5px;color:#8a9bb0}.savings-two{display:grid;grid-template-columns:1fr 1fr;gap:9px;margin-bottom:10px}.money-row{display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid #f1f5fb;padding:7px 0;font-size:10px;color:#405872}.money-row:last-child{border-bottom:0}.money-row .where{color:#8a9bb0;font-size:8.5px;margin-top:1px}.money-row .amt{font-family:ui-monospace,monospace;color:#1e3a5f}.frozen-row{display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid #f1f5fb;padding:7px 0;font-size:10px}.frozen-row:last-child{border-bottom:0}.frozen-row .why{color:#8a9bb0;font-size:8.5px;margin-top:1px}.frozen-row .amt{color:#b7791f;font-family:ui-monospace,monospace}.frozen-right{display:flex;align-items:center;gap:8px}.frozen-acts{display:flex;gap:4px}.frozen-acts button{border:1px solid #dbe8ff;background:#f8fbff;color:#2563eb;border-radius:5px;padding:2px 5px;font:8.5px inherit;cursor:pointer}.frozen-acts button.del{border-color:#f0d7dd;color:#b23b52;background:#fff}.frozen-acts button:hover{background:#eef4ff}.frozen-tip{font-size:8.5px;color:#8a9bb0;background:#f8fbff;border:1px dashed #dbe8ff;border-radius:6px;padding:6px 7px;margin-top:8px;line-height:1.6}.stat-amber .v{color:#b7791f}.savings-grid{display:grid;grid-template-columns:repeat(5,1fr);gap:9px;margin-bottom:11px}
    .savings-stat{border:1px solid #e3ebf7;border-radius:11px;background:#fff;padding:11px 12px}
    .savings-stat .k{font-size:9px;color:#8a9bb0;margin-bottom:3px}.savings-stat .v{font-size:17px;font-weight:700;color:#17263b;letter-spacing:-.03em}
    .savings-stat .v.blue{color:#2563eb}
    .savings-panel{border:1px solid #e3ebf7;border-radius:12px;background:#fff;padding:12px 13px;margin-bottom:10px}
    .savings-panel h3{font-size:11px;margin:0 0 9px;color:#1e3a5f}
    .savings-form{display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px}
    .savings-form .full{grid-column:1/-1}
    .savings-form label{display:block;font-size:9px;color:#8a9bb0;margin-bottom:3px}
    .savings-form input,.savings-form select{border:1px solid #e3ebf7;border-radius:7px;background:#f8fbff;color:#243b55;font:10.5px inherit;outline:0;padding:6px 7px;width:100%}
    .savings-form input:focus,.savings-form select:focus{border-color:#93b7fa;box-shadow:0 0 0 3px rgba(37,99,235,.08)}
    .savings-form .actions{grid-column:1/-1;display:flex;align-items:center;gap:8px;margin-top:2px}
    .savings-form .actions button{border:0;border-radius:7px;background:#2563eb;color:#fff;font-size:10px;padding:6px 11px;cursor:pointer}
    .savings-form .actions button:hover{background:#1d4ed8}
    .savings-form .ai{font-size:9.5px;color:#6b7c95;display:flex;align-items:center;gap:4px}
    .import-row{display:flex;gap:8px;align-items:center}
    .import-row input[type=file]{flex:1;border:1px dashed #dbe8ff;border-radius:8px;background:#f8fbff;color:#6b7c95;font-size:9.5px;padding:7px}
    .import-row button{border:1px solid #dbe8ff;border-radius:7px;background:#fff;color:#2563eb;font-size:10px;padding:6px 9px;cursor:pointer}
    .import-row button:hover{background:#eef4ff}
    .import-status{font-size:9.5px;color:#8a9bb0;margin-top:6px;min-height:14px}
    .entry-list{display:flex;flex-direction:column;gap:5px;max-height:220px;overflow:auto}
    .entry{display:flex;align-items:center;gap:8px;border-bottom:1px solid #eef3fb;padding:5px 2px;font-size:10px;color:#4b5f78}
    .entry:last-child{border-bottom:0}.entry .amt{margin-left:auto;font-weight:600}.entry .amt.neg{color:#c0264a}.entry .amt.pos{color:#1f9d6b}
    .entry .tag{font-size:8px;color:#8a9bb0;border:1px solid #e3ebf7;border-radius:4px;padding:1px 4px}
    .cron-list{display:flex;flex-direction:column;gap:7px}
    .cron-item{border:1px solid #e3ebf7;border-radius:10px;background:#fff;padding:10px 12px;display:flex;align-items:center;gap:10px;transition:border-color .18s,transform .18s,box-shadow .18s}
    .cron-item:hover{border-color:#bcd4f7;transform:translateY(-1px);box-shadow:0 6px 14px rgba(37,99,235,.06)}
    .cron-dot{width:7px;height:7px;border-radius:50%;background:#1f9d6b;flex:none}.cron-dot.off{background:#c4cedd}
    .cron-main{min-width:0}.cron-main .n{font-size:11px;color:#1e3a5f;font-weight:600}.cron-main .e{font-size:9px;color:#8a9bb0;margin-top:2px}
    .cron-state{margin-left:auto;font-size:9px;color:#1f9d6b}.cron-state.off{color:#8a9bb0}
    .cron-btns{display:flex;gap:5px}
    .cron-btns button{border:1px solid #dbe8ff;border-radius:6px;background:#fff;color:#4b5f78;font-size:9px;padding:3px 7px;cursor:pointer}
    .cron-btns button:hover{background:#eef4ff;color:#2563eb}
    .cron-btns button.danger{color:#c0264a;border-color:#f3c7d2}
    .cron-form{border:1px solid #dbe8ff;border-radius:10px;background:#f8fbff;padding:10px 12px;margin-bottom:10px;display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px}
    .cron-form label{display:block;font-size:8.5px;color:#8a9bb0;margin-bottom:2px}
    .cron-form input,.cron-form select{border:1px solid #e3ebf7;border-radius:6px;background:#fff;color:#243b55;font:9.5px inherit;outline:0;padding:5px 6px;width:100%}
    .cron-form .full{grid-column:1/-1;display:flex;align-items:center;gap:7px}
    .cron-form .full button{border:0;border-radius:6px;background:#2563eb;color:#fff;font-size:9.5px;padding:5px 10px;cursor:pointer}
    .cron-form .full button.cancel{background:#fff;color:#4b5f78;border:1px solid #dbe8ff}
    .cron-form .msg{font-size:9px;color:#8a9bb0}
    .log-toolbar{display:flex;align-items:center;gap:7px;margin-bottom:8px;flex-wrap:wrap}
    .log-toolbar select,.log-toolbar input{border:1px solid #dbe8ff;border-radius:6px;background:#fff;color:#243b55;font:9.5px inherit;outline:0;padding:5px 7px}
    .log-toolbar input{flex:1;max-width:280px}
    .log-toolbar .hint{font-size:9px;color:#8a9bb0;margin-left:auto}
    .log-console{border:1px solid #dbe8ff;border-radius:9px;background:#f8fbff;overflow:auto;height:calc(100% - 86px);min-height:260px;padding:5px 0;font:10px/1.55 "Cascadia Code","Consolas",monospace}
    .log-line{display:grid;grid-template-columns:62px 44px 1fr;gap:8px;padding:2px 9px;border-left:2px solid transparent;color:#4b5f78;white-space:nowrap}
    .log-line:hover{background:#eef4ff;border-left-color:#93b7fa}
    .log-line .lt{color:#8a9bb0}.log-line .lv{font-size:8.5px;font-weight:700}
    .log-line .lv.INFO{color:#1d4ed8}.log-line .lv.WARN{color:#b45309}.log-line .lv.ERROR{color:#c0264a}
    .log-line .lm{overflow:hidden;text-overflow:ellipsis}
    .log-empty{padding:16px;color:#8a9bb0;font-size:10px}
    .persona-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px}
    .persona-card{border:1px solid #e3ebf7;border-radius:12px;background:#fff;padding:12px 13px;transition:border-color .18s,transform .18s,box-shadow .18s}
    .persona-card:hover{border-color:#bcd4f7;transform:translateY(-2px);box-shadow:0 8px 18px rgba(37,99,235,.06)}
    .persona-top{display:flex;align-items:center;gap:8px;margin-bottom:6px}
    .persona-ava{width:27px;height:27px;border-radius:8px;background:#dbeafe;color:#1d4ed8;display:grid;place-items:center;font-size:11px;font-weight:700}
    .persona-card h3{font-size:11px;margin:0;color:#1e3a5f}.persona-card .pill{font-size:8px;color:#1f9d6b;border:1px solid #cdeee0;background:#eefbf5;border-radius:4px;padding:1px 4px;margin-left:auto}
    .persona-card p{font-size:9.5px;line-height:1.55;color:#6b7c95;margin:5px 0 8px;min-height:30px}
    .persona-files{display:flex;flex-wrap:wrap;gap:4px;margin-bottom:8px}.persona-files span{font-size:8px;color:#6b7c95;border:1px solid #e3ebf7;border-radius:4px;padding:1px 4px}
    .persona-actions{display:flex;gap:5px}.persona-actions button{border:1px solid #dbe8ff;border-radius:5px;background:#fff;color:#2563eb;font-size:8.5px;padding:3px 6px;cursor:pointer}.persona-actions button:hover{background:#eef4ff}
    .persona-actions button.on{background:#dbeafe;color:#1d4ed8}
    .persona-toolbar{display:flex;gap:7px;align-items:center;margin-bottom:9px}.persona-toolbar button{border:1px solid #dbe8ff;border-radius:6px;background:#fff;color:#2563eb;font-size:9.5px;padding:5px 8px;cursor:pointer}.persona-toolbar button:hover{background:#eef4ff}
    .persona-toolbar .msg{font-size:9px;color:#8a9bb0;margin-left:auto}
    .persona-toolbar input{display:none}
    .login-mask{position:fixed;inset:0;z-index:50;background:rgba(15,23,42,.35);backdrop-filter:blur(3px);display:none;align-items:flex-start;justify-content:center;padding:80px 16px;overflow:auto}
    .login-mask.on{display:flex}
    .login-card{width:100%;max-width:420px;background:#fff;border:1px solid #dbe8ff;border-radius:14px;padding:18px;box-shadow:0 18px 45px rgba(37,99,235,.16)}
    .login-card h2{font-size:15px;margin:0 0 5px;color:#17263b}.login-card .sub{font-size:10px;color:#6b7c95;line-height:1.6;margin-bottom:13px}
    .login-field{margin-bottom:9px}.login-field label{display:block;font-size:9px;color:#8a9bb0;margin-bottom:3px}
    .login-field input{width:100%;border:1px solid #dbe8ff;border-radius:7px;background:#f8fbff;color:#243b55;font:10.5px inherit;outline:0;padding:7px 8px}
    .login-field input:focus{border-color:#93b7fa;box-shadow:0 0 0 3px rgba(37,99,235,.08)}
    .login-url{border:1px solid #e3ebf7;border-radius:7px;background:#f8fbff;color:#6b7c95;font:10px inherit;padding:7px 8px}
    .login-actions{display:flex;gap:6px;margin-top:10px}.login-actions button{flex:1;border:1px solid #dbe8ff;border-radius:7px;background:#fff;color:#2563eb;font-size:10px;padding:7px;cursor:pointer}
    .login-actions button.primary{background:#2563eb;border-color:#2563eb;color:#fff}.login-actions button:hover{filter:brightness(.97)}
    .login-status{font-size:9px;color:#8a9bb0;margin-top:8px;min-height:14px}
    .login-skip{display:block;margin:9px auto 0;font-size:9px;color:#8a9bb0;background:none;border:0;cursor:pointer}.login-skip:hover{color:#2563eb}




    .info-stats{display:grid;grid-template-columns:repeat(4,1fr);gap:9px;margin-bottom:10px}
    .info-stat{border:1px solid #e3ebf7;border-radius:11px;background:#fff;padding:10px 12px}
    .info-stat .k{font-size:9px;color:#8a9bb0;margin-bottom:2px}.info-stat .v{font-size:18px;font-weight:700;color:#17263b}
    .info-grid{display:grid;grid-template-columns:1fr 1fr;gap:9px}
    .info-panel{border:1px solid #e3ebf7;border-radius:11px;background:#fff;padding:11px 12px;transition:border-color .18s,transform .18s,box-shadow .18s}
    .info-panel:hover{border-color:#bcd4f7;transform:translateY(-2px);box-shadow:0 8px 18px rgba(37,99,235,.06)}
    .info-panel h3{display:flex;align-items:center;font-size:10.5px;margin:0 0 7px;color:#1e3a5f}
    .info-panel h3 span{margin-left:auto;font-size:8.5px;color:#8a9bb0;font-weight:400}
    .info-row{display:flex;justify-content:space-between;gap:10px;font-size:9.5px;color:#6b7c95;padding:3px 0;border-bottom:1px solid #f1f5fb}
    .info-row:last-child{border-bottom:0}.info-row b{font-weight:500;color:#243b55;text-align:right}
    .info-row .ok{color:#1f9d6b}.info-row .warn{color:#b45309}

    .week-toolbar{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:9px}
    .week-toolbar label{font-size:9.5px;color:#6b7c95;display:flex;align-items:center;gap:5px}
    .week-toolbar input[type=number]{width:52px;border:1px solid #dbe8ff;border-radius:6px;background:#fff;color:#243b55;font:10px inherit;padding:4px 6px;outline:0}
    .week-toolbar button,.week-toolbar .file-btn{border:1px solid #dbe8ff;border-radius:6px;background:#fff;color:#2563eb;font-size:9.5px;padding:5px 8px;cursor:pointer}
    .week-toolbar button:hover,.week-toolbar .file-btn:hover{background:#eef4ff}
    .week-toolbar .file-btn input{display:none}
    .week-msg{margin-left:auto;font-size:9px;color:#8a9bb0}
    .week-wrap{border:1px solid #e3ebf7;border-radius:12px;background:#fff;overflow:hidden}
    .week-grid{display:grid;grid-template-columns:44px repeat(7,1fr);width:100%;font-size:9px}
    .week-grid .h{background:#f8fbff;border-bottom:1px solid #e3ebf7;border-right:1px solid #e3ebf7;padding:6px 4px;text-align:center;color:#6b7c95;font-weight:600}
    .week-grid .h:last-child{border-right:0}
    .week-grid .p{background:#f8fbff;border-right:1px solid #e3ebf7;border-bottom:1px solid #e3ebf7;display:flex;align-items:center;justify-content:center;color:#8a9bb0;font-size:8.5px}
    .week-cell{min-height:42px;border-right:1px solid #eef3fb;border-bottom:1px solid #eef3fb;padding:3px;cursor:pointer;transition:background .15s}
    .week-cell:nth-child(8n){border-right:0}
    .week-cell:hover{background:#f8fbff}
    .week-cell.sel{background:#eef4ff;box-shadow:inset 0 0 0 1px #93b7fa}
    .course{background:#eef4ff;border-left:2px solid #2563eb;border-radius:4px;padding:3px 4px;color:#1e3a5f;font-size:8.5px;line-height:1.35;cursor:pointer}
    .course b{display:block;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
    .course span{display:block;color:#6b7c95;font-size:8px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
    .week-grid .p{flex-direction:column;gap:1px;padding:4px 2px;font-size:8px;line-height:1.2}
    .week-grid .p b{font-size:8.5px;color:#6b7c95;font-weight:600}
    .week-grid .p span{font-size:7px;color:#9aabbe}
    .week-period-editor{border:1px solid #dbe8ff;border-radius:10px;background:#f8fbff;padding:9px 10px;margin-bottom:9px}
    .wpe-head{display:flex;align-items:center;gap:8px;margin-bottom:6px;font-size:10px;color:#1e3a5f}
    .wpe-head button{margin-left:auto;border:1px solid #dbe8ff;border-radius:5px;background:#fff;color:#2563eb;font-size:9px;padding:3px 7px;cursor:pointer}
    .wpe-row{display:grid;grid-template-columns:50px 1fr 44px;gap:6px;align-items:center;margin-bottom:4px}
    .wpe-row span{font-size:9px;color:#6b7c95}.wpe-row input{border:1px solid #e3ebf7;border-radius:5px;background:#fff;color:#243b55;font:9px inherit;padding:4px 6px;outline:0}
    .wpe-row .wpe-del{border:1px solid #f3c7d2;border-radius:5px;background:#fff;color:#c0264a;font-size:8.5px;padding:3px 5px;cursor:pointer}
    .wpe-actions{display:flex;align-items:center;gap:7px;margin-top:6px}
    .wpe-actions button{border:0;border-radius:5px;background:#2563eb;color:#fff;font-size:9px;padding:4px 8px;cursor:pointer}.wpe-actions .msg{font-size:9px;color:#8a9bb0}
    .week-form{display:grid;grid-template-columns:1fr 1fr;gap:7px;margin-top:10px;border:1px solid #e3ebf7;border-radius:10px;background:#fff;padding:10px}
    .week-form label{display:block;font-size:8.5px;color:#8a9bb0;margin-bottom:2px}
    .week-form input,.week-form select{border:1px solid #e3ebf7;border-radius:6px;background:#f8fbff;color:#243b55;font:9.5px inherit;outline:0;padding:5px 6px;width:100%}
    .week-form .full{grid-column:1/-1;display:flex;align-items:center;gap:7px}
    .week-form button{border:0;border-radius:6px;background:#2563eb;color:#fff;font-size:9.5px;padding:5px 10px;cursor:pointer}
    .week-form button.del{background:#fff;color:#c0264a;border:1px solid #f3c7d2}
    .week-form .msg{font-size:9px;color:#8a9bb0}


    .cmd-runbar{display:flex;align-items:center;gap:7px;margin:0 0 10px;border:1px solid #dbe8ff;border-radius:9px;background:#f8fbff;padding:6px 8px}
    .cmd-runbar .prompt{color:#2563eb;font:11px "Cascadia Code",monospace}
    .cmd-runbar input{flex:1;border:0;outline:0;background:transparent;color:#243b55;font:11px "Cascadia Code",monospace}
    .cmd-runbar button{border:1px solid #dbe8ff;background:#fff;color:#2563eb;border-radius:6px;font-size:10px;padding:4px 9px;cursor:pointer;transition:background .16s}
    .cmd-runbar button:hover{background:#eef4ff}
    .cmd-hint{font-size:9.5px;color:#8a9bb0;margin:-4px 0 9px;min-height:14px}
    .cmd-hint b{color:#4b5f78;font-weight:500}


    .chat-search{display:none;align-items:center;gap:7px;padding:7px 18px;border-bottom:1px solid #e3ebf7;background:#f8fbff;flex:none}
    .chat-search.on{display:flex}
    .chat-search input{flex:1;border:1px solid #dbe8ff;border-radius:7px;background:#fff;color:#243b55;font:11px inherit;outline:0;padding:5px 8px}
    .chat-search input:focus{border-color:#93b7fa;box-shadow:0 0 0 3px rgba(37,99,235,.08)}
    .chat-search .count{font-size:9px;color:#8a9bb0;min-width:42px;text-align:right}
    .chat-search button{border:1px solid #dbe8ff;background:#fff;color:#4b5f78;border-radius:6px;font-size:10px;padding:3px 7px;cursor:pointer}
    .chat-search button:hover{background:#eef4ff;color:#2563eb}
    .msg .bubble mark{background:#fde68a;color:#7a4b00;border-radius:2px;padding:0 1px}
    .msg .bubble.search-hit{box-shadow:0 0 0 2px #93b7fa inset}



  `;
  document.head.appendChild(css);

  const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const msgs = document.querySelector('.msgs');
  const main = document.querySelector('.main');
  const composer = document.querySelector('.composer');
  const top = document.querySelector('.top');
  const nameEl = top.querySelector('.nm');
  const subEl = top.querySelector('.sub');

  const pageView = document.createElement('div');
  pageView.className = 'page-view';
  main.appendChild(pageView);

  function toast(msg) {
    let t = document.querySelector('.toast');
    if (!t) { t = document.createElement('div'); t.className = 'toast'; document.body.appendChild(t); }
    t.textContent = msg; t.classList.add('on');
    clearTimeout(window.__toast); window.__toast = setTimeout(() => t.classList.remove('on'), 1400);
  }

  // 首次登录
  let loginMask = null;
  function openLogin() {
    if (!loginMask) {
      const saved = (() => { try { return JSON.parse(localStorage.getItem('hsh_web_login') || '{}'); } catch { return {}; } })();
      loginMask = document.createElement('div');
      loginMask.className = 'login-mask';
      loginMask.innerHTML = '<div class="login-card"><h2>连接 Hoshinoumi</h2><div class="sub">你已经在 Web 上，后端地址直接使用当前站点。<br>只填写访问 token 和主人 QQ。</div>' +
        '<div class="login-field"><label>后端</label><div class="login-url">当前 Web 站点 · 同源（无需填写 URL）</div></div>' +
        '<div class="login-field"><label>访问 token</label><input id="loginToken" type="password" value="' + esc(saved.token || '') + '" placeholder="Bearer token"></div>' +
        '<div class="login-field"><label>主人 QQ</label><input id="loginQQ" value="' + esc(saved.qq || '') + '" placeholder="请输入主人 QQ"></div>' +
        '<div class="login-actions"><button id="loginTest">测试连接</button><button class="primary" id="loginSave">保存并进入</button></div>' +
        '<div class="login-status" id="loginStatus"></div><button class="login-skip" id="loginSetup">首次登录？设置密码</button></div>';
      document.body.appendChild(loginMask);
      document.getElementById('loginSetup').addEventListener('click', openSetup);
      document.getElementById('loginTest').addEventListener('click', () => {
        const token = document.getElementById('loginToken').value.trim();
        const qq = document.getElementById('loginQQ').value.trim();
        const st = document.getElementById('loginStatus');
        st.textContent = token && qq ? '连接成功（MOCK）· 42ms' : 'token 和 QQ 都要填';
      });
      document.getElementById('loginSave').addEventListener('click', () => {
        const token = document.getElementById('loginToken').value.trim();
        const qq = document.getElementById('loginQQ').value.trim();
        const st = document.getElementById('loginStatus');
        if (!token || !qq) { st.textContent = 'token 和 QQ 都要填'; return; }
        localStorage.setItem('hsh_web_login', JSON.stringify({ token, qq }));
        loginMask.classList.remove('on');
        toast('已保存登录配置（MOCK）');
        updateConn('当前 Web 站点', qq);
      });
    }
    loginMask.classList.add('on');
  }
  function openSetup() {
    let setupMask = document.querySelector('.setup-mask');
    if (!setupMask) {
      setupMask = document.createElement('div');
      setupMask.className = 'login-mask setup-mask on';
      setupMask.innerHTML = '<div class="login-card"><h2>首次登录 · 设置密码</h2><div class="sub">账号已由邀请人创建，不需要重新注册。<br>填写 QQ、setup code 和新密码。</div>' +
        '<div class="login-field"><label>QQ 号</label><input id="setupQQ" inputmode="numeric" placeholder="输入账号 QQ"></div>' +
        '<div class="login-field"><label>一次性 setup code</label><input id="setupCode" placeholder="邀请你的朋友给你的 setup code"></div>' +
        '<div class="login-field"><label>新密码（至少 8 位）</label><input id="setupPassword" type="password" placeholder="设置登录密码"></div>' +
        '<div class="login-field"><label>确认密码</label><input id="setupPassword2" type="password" placeholder="再输入一次"></div>' +
        '<div class="login-actions"><button id="setupCancel">返回登录</button><button class="primary" id="setupSave">设置密码并登录</button></div>' +
        '<div class="login-status" id="setupStatus"></div></div>';
      document.body.appendChild(setupMask);
      const close = () => setupMask.remove();
      setupMask.querySelector('#setupCancel').addEventListener('click', close);
      setupMask.querySelector('#setupSave').addEventListener('click', () => {
        const qq = setupMask.querySelector('#setupQQ').value.trim();
        const code = setupMask.querySelector('#setupCode').value.trim();
        const password = setupMask.querySelector('#setupPassword').value;
        const password2 = setupMask.querySelector('#setupPassword2').value;
        const st = setupMask.querySelector('#setupStatus');
        if (!qq) { st.textContent = '请输入账号 QQ'; return; }
        if (!code || password.length < 8) { st.textContent = 'setup code 和至少 8 位密码都要填'; return; }
        if (password !== password2) { st.textContent = '两次密码不一致'; return; }
        localStorage.setItem('hsh_web_login', JSON.stringify({ token: 'setup-token', qq }));
        close(); loginMask?.classList.remove('on'); toast('密码已设置，已登录（MOCK）'); updateConn('当前 Web 站点', qq);
      });
    }
    setupMask.classList.add('on');
  }
  function openNewWebChat() {
    let mask = document.querySelector('.new-conv-mask');
    if (!mask) {
      mask = document.createElement('div');
      mask.className = 'login-mask new-conv-mask on';
      mask.innerHTML = '<div class="login-card"><h2>新建会话</h2><div class="sub">选择私聊联系人或创建自有客户端群聊。</div>' +
        '<div class="login-actions" style="margin-bottom:10px"><button id="newWebPrivate">发起私聊</button><button id="newWebGroup">创建群聊</button></div>' +
        '<div id="newWebBody"></div><button class="login-skip" id="newWebCancel">取消</button></div>';
      document.body.appendChild(mask);
      const body = mask.querySelector('#newWebBody');
      mask.querySelector('#newWebCancel').addEventListener('click', () => mask.classList.remove('on'));
      mask.querySelector('#newWebPrivate').addEventListener('click', () => {
        body.innerHTML = '<div class="login-field"><label>选择联系人</label></div>' +
          [['友利','友'],['摄影部','摄']].map(([n,a]) => '<button class="new-contact-web" data-name="'+n+'" data-avatar="'+a+'" style="display:flex;width:100%;align-items:center;gap:8px;border:0;border-bottom:1px solid #eef3fb;background:#fff;padding:8px 2px;cursor:pointer"><span style="width:26px;height:26px;border-radius:8px;background:#eef4ff;display:grid;place-items:center;color:#2563eb;font-size:10px">'+a+'</span><b style="font-size:10px;color:#314a65">'+n+'</b><span style="margin-left:auto;color:#2563eb;font-size:9px">选择</span></button>').join('');
        body.querySelectorAll('.new-contact-web').forEach(b => b.addEventListener('click', () => createWebConversation(b.dataset.name, b.dataset.avatar, '私聊')));
      });
      mask.querySelector('#newWebGroup').addEventListener('click', () => {
        body.innerHTML = '<div class="login-field"><label>群聊名称</label><input id="newWebGroupName" placeholder="例如：周末计划"></div><div class="login-field"><label>成员</label><input value="奈绪、友利" readonly></div><div class="login-actions"><button id="newWebGroupCreate" class="primary">创建群聊</button></div>';
        body.querySelector('#newWebGroupCreate').addEventListener('click', () => {
          const name = (body.querySelector('#newWebGroupName').value || '').trim();
          if (!name) { body.querySelector('#newWebGroupName').focus(); return; }
          createWebConversation(name, '群', '群聊');
        });
      });
    }
    mask.classList.add('on');
  }
  function createWebConversation(name, avatar, type) {
    const id = 'h_' + Date.now().toString(36) + Math.random().toString(36).slice(2, 6);
    const row = document.createElement('div');
    row.className = 'conv';
    row.dataset.convId = id;
    row.innerHTML = '<div class="avatar">' + esc(avatar) + '</div><div style="min-width:0"><div class="nm">' + esc(name) + '</div><div class="last">' + esc(type) + ' · 刚刚创建</div></div><div class="tm">刚刚</div>';
    row.addEventListener('click', () => selectNewWebConversation(name, type, avatar));
    document.querySelector('.convs').prepend(row);
    document.querySelector('.new-conv-mask')?.classList.remove('on');
    selectNewWebConversation(name, type, avatar);
    toast('已创建' + (type === '群聊' ? '群聊' : '会话') + '：' + name);
  }
  function selectNewWebConversation(name, type, avatar) {
    showChat();
    document.querySelectorAll('.conv').forEach(c => c.classList.remove('on'));
    const row = [...document.querySelectorAll('.conv')].find(c => c.dataset.convId && c.querySelector('.nm')?.textContent === name);
    row?.classList.add('on');
    const nm = top.querySelector('.who .nm'); if (nm) nm.textContent = name;
    const sub = top.querySelector('.who .sub'); if (sub) sub.innerHTML = type + ' · 自有客户端 · <span class="pill">在线</span>';
    const whoAvatar = top.querySelector('.who .avatar'); if (whoAvatar) whoAvatar.textContent = avatar;
    msgs.innerHTML = '<div class="day"><b>今天</b> · 刚刚</div><div class="msg"><div class="avatar">' + esc(avatar) + '</div><div><div class="bubble">' + (type === '群聊' ? '群聊已创建，可以开始讨论了。' : '新会话已创建，开始聊天吧。') + '</div><div class="meta">刚刚</div></div></div>';
    const ta = composer.querySelector('textarea'); if (ta) ta.placeholder = '和' + name + '说点什么……';
  }
  document.getElementById('newWebConv')?.addEventListener('click', openNewWebChat);
  function updateConn(url, qq) {
    const v = document.querySelector('.conn .v');
    const meta = document.querySelector('.conn .meta');
    if (v) v.innerHTML = '<span class="dot"></span> 已连接 · schema 35';
    if (meta) meta.textContent = '当前 Web 站点 · 42ms · owner ' + (qq || '');
  }

  function msgHtml(x) {
    return '<div class="msg ' + (x.r === 'me' ? 'me' : '') + '">' +
      (x.r === 'me' ? '' : '<div class="avatar">' + esc(x.a || '奈') + '</div>') +
      '<div><div class="bubble">' + esc(x.t) + '</div>' +
      (x.mem ? '<div class="memchip"><span class="i">✦</span> ' + esc(x.mem) + '</div>' : '') +
      '<div class="meta">' + esc(x.m) + '</div></div>' +
      (x.r === 'me' ? '<div class="avatar" style="background:linear-gradient(135deg,#8ad7e8,#7f9cff);color:#071322">你</div>' : '') + '</div>';
  }

  function showChat() {
    [top, msgs, composer, searchBar].forEach(x => x.classList.remove('chat-hide'));
    pageView.classList.remove('on');
    document.querySelectorAll('.rnav').forEach(x => x.classList.toggle('on', x.dataset.page === 'chat'));
  }

  // 聊天内搜索
  const searchBtn = top.querySelector('.tbtn');
  const chatMoreBtn = document.getElementById('chatMore');
  let chatMoreMenu = null;
  function toggleChatMore() {
    if (!chatMoreMenu) {
      chatMoreMenu = document.createElement('div');
      chatMoreMenu.className = 'chat-more';
      chatMoreMenu.innerHTML = '<button data-act="info">会话信息</button><button data-act="pin">置顶会话</button><button data-act="mute">免打扰</button><div class="sep"></div><button data-act="search">聊天内搜索</button><button data-act="recall">撤回最近消息</button>';
      document.body.appendChild(chatMoreMenu);
      chatMoreMenu.addEventListener('click', e => {
        const act = e.target.closest('button')?.dataset.act;
        if (!act) return;
        chatMoreMenu.classList.remove('on');
        if (act === 'search') { openSearch(true); return; }
        if (act === 'recall') { const own = [...msgs.querySelectorAll('.msg')].reverse().find(m => m.querySelector('.avatar')?.textContent === '你'); if (own) { own.remove(); toast('已撤回（MOCK）'); } else toast('没有可撤回的消息'); return; }
        toast(act === 'info' ? '会话信息（MOCK）' : act === 'pin' ? '已置顶（MOCK）' : '免打扰已开启（MOCK）');
      });
      document.addEventListener('click', e => { if (!chatMoreMenu.contains(e.target) && e.target !== chatMoreBtn) chatMoreMenu.classList.remove('on'); });
    }
    chatMoreMenu.classList.toggle('on');
  }
  chatMoreBtn?.addEventListener('click', e => { e.stopPropagation(); toggleChatMore(); });
  const searchBar = document.createElement('div');
  searchBar.className = 'chat-search';
  searchBar.innerHTML = '<span>⌕</span><input id="chatSearchInput" placeholder="搜索当前聊天"><span class="count" id="chatSearchCount"></span><button id="searchPrev" title="上一条">↑</button><button id="searchNext" title="下一条">↓</button><button id="searchClose" title="关闭">×</button>';
  top.after(searchBar);
  let hitEls = [], hitIndex = -1;
  function clearSearchMarks() {
    msgs.querySelectorAll('.msg .bubble').forEach(b => {
      if (b.dataset.orig !== undefined) { b.textContent = b.dataset.orig; }
      b.classList.remove('search-hit');
    });
    hitEls = []; hitIndex = -1;
  }
  function runSearch() {
    clearSearchMarks();
    const q = searchBar.querySelector('input').value.trim();
    const count = searchBar.querySelector('.count');
    if (!q) { count.textContent = ''; return; }
    const lower = q.toLowerCase();
    msgs.querySelectorAll('.msg .bubble').forEach(b => {
      const text = b.dataset.orig !== undefined ? b.dataset.orig : b.textContent;
      b.dataset.orig = text;
      const i = text.toLowerCase().indexOf(lower);
      if (i < 0) return;
      b.innerHTML = esc(text.slice(0, i)) + '<mark>' + esc(text.slice(i, i + q.length)) + '</mark>' + esc(text.slice(i + q.length));
      hitEls.push(b);
    });
    count.textContent = hitEls.length ? '1/' + hitEls.length : '0 条';
    if (hitEls.length) { hitIndex = 0; focusHit(); }
  }
  function focusHit() {
    hitEls.forEach(b => b.classList.remove('search-hit'));
    if (hitIndex < 0 || !hitEls.length) return;
    hitIndex = (hitIndex + hitEls.length) % hitEls.length;
    const el = hitEls[hitIndex];
    el.classList.add('search-hit');
    el.scrollIntoView({ block: 'center', behavior: 'smooth' });
    searchBar.querySelector('.count').textContent = (hitIndex + 1) + '/' + hitEls.length;
  }
  function openSearch(force) {
    const on = force !== undefined ? force : !searchBar.classList.contains('on');
    searchBar.classList.toggle('on', on);
    if (on) { searchBar.querySelector('input').focus(); }
    else { clearSearchMarks(); searchBar.querySelector('input').value = ''; searchBar.querySelector('.count').textContent = ''; }
  }
  searchBtn.addEventListener('click', () => openSearch());
  searchBar.querySelector('input').addEventListener('input', runSearch);
  searchBar.querySelector('input').addEventListener('keydown', e => {
    if (e.key === 'Enter') { e.preventDefault(); hitIndex++; focusHit(); }
    if (e.key === 'Escape') { openSearch(false); }
  });
  searchBar.querySelector('#searchNext').addEventListener('click', () => { hitIndex++; focusHit(); });
  searchBar.querySelector('#searchPrev').addEventListener('click', () => { hitIndex--; if (hitIndex < 0) hitIndex = hitEls.length - 1; focusHit(); });
  searchBar.querySelector('#searchClose').addEventListener('click', () => openSearch(false));

  function updateUnread() {
    const nums = [...document.querySelectorAll('.conv .unread')].map(x => Number(x.textContent) || 0);
    const total = nums.reduce((a, b) => a + b, 0);
    const badge = document.querySelector('.rnav[data-page="chat"] .badge');
    if (badge) {
      if (total > 0) { badge.textContent = total; badge.style.display = ''; }
      else { badge.textContent = ''; badge.style.display = 'none'; }
    }
  }

  function renderChat(id) {
    const c = CHATS[id] || CHATS.nao;
    nameEl.textContent = c.name;
    subEl.innerHTML = esc(c.sub) + ' <span class="pill">在线</span>';
    msgs.innerHTML = '<div class="day"><b>今天</b> · 20:58</div>' + c.msgs.map(msgHtml).join('');
    openSearch(false);
    document.querySelectorAll('.conv').forEach(x => { const on = x.dataset.conv === id; x.classList.toggle('on', on); if (on) x.querySelector('.unread')?.remove(); });
    showChat();
    updateUnread();
    msgs.scrollTop = msgs.scrollHeight;
  }

  const convIds = ['nao', 'seagroup', 'student', 'photo', 'test'];
  document.querySelectorAll('.conv').forEach((x, i) => {
    x.dataset.conv = convIds[i] || 'nao';
    x.addEventListener('click', () => { x.querySelector('.unread')?.remove(); updateUnread(); renderChat(x.dataset.conv); });
  });

  function append(role, text, meta) {
    msgs.insertAdjacentHTML('beforeend', msgHtml({ r: role, t: text, m: meta || '刚刚 · MOCK' }));
    msgs.scrollTop = msgs.scrollHeight;
  }

  function send() {
    const el = document.querySelector('.composer textarea');
    const text = el.value.trim();
    if (!text) { toast('先输入一点内容'); return; }
    el.value = '';
    append('me', text, '刚刚 · 已读');
    msgs.insertAdjacentHTML('beforeend', '<div class="typing" id="typing">nao 正在输入…</div>');
    msgs.scrollTop = msgs.scrollHeight;
    setTimeout(() => {
      document.getElementById('typing')?.remove();
      const t = text.toLowerCase();
      let reply = '嗯，我在听。你继续说。';
      if (t.includes('方案') || t.includes('过')) reply = '方案过了就好。你之前一直担心，现在可以松一口气了。';
      else if (t.includes('钱') || t.includes('余额') || t.includes('存')) reply = '本月结余 ¥3,300，旅行目标 60%。要记一笔吗？';
      else if (t.includes('冷') || t.includes('天气')) reply = '外面冷的话，回去先喝点热的。别硬撑。';
      append('bot', reply, '刚刚 · MOCK 回复');
    }, 520);
  }

  const input = document.querySelector('.composer textarea');
  document.querySelector('.send').addEventListener('click', send);
  input.addEventListener('keydown', e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); } });

  document.querySelectorAll('.tool').forEach(b => b.addEventListener('click', () => {
    const t = b.textContent.trim();
    input.value = '[' + t + '] ';
    input.focus();
    toast(t + '：v35.5 演示占位');
  }));

  function validMoney(v) {
    const str = String(v ?? '').trim();
    if (!/^\d+(\.\d{1,2})?$/.test(str)) return null;
    const n = Number(str); return n > 0 ? n : null;
  }
  function showPage(name) {
    if (name === 'settings') {
      let saved = {}; try { saved = JSON.parse(localStorage.getItem('hsh_web_login') || '{}'); } catch {}
      pageView.innerHTML = '<div class="page-head"><div><h2>设置</h2><p>v35.5 Web 演示 · 登录 / 后端 / 连接</p></div><button class="back" id="backChat">← 返回聊天</button></div>' +
        '<div class="info-grid"><div class="info-panel"><h3>登录配置</h3><div class="info-row"><span>后端</span><b>' + esc(location.origin === 'null' ? '当前 Web 站点' : location.origin) + ' · 同源</b></div><div class="info-row"><span>token</span><b>' + (saved.token ? '已保存 · 掩码' : '未配置') + '</b></div><div class="info-row"><span>主人 QQ</span><b>' + esc(saved.qq || '') + '</b></div><div class="info-row"><span>操作</span><b><button class="back" id="relogin">登录 / 重新配置</button></b></div></div>' +
        '<div class="info-panel"><h3>连接</h3><div class="info-row"><span>状态</span><b class="ok">已连接 · MOCK</b></div><div class="info-row"><span>schema</span><b>35</b></div><div class="info-row"><span>延迟</span><b>42ms</b></div></div></div>' +
        '<div style="margin-top:18px;padding-top:10px;border-top:1px solid #eef3fb;text-align:center;font:8px ui-monospace,monospace;letter-spacing:.12em;color:#a8b5c7">POWERED BY JYOUSHITOU</div>' +
        '<div style="display:flex;justify-content:center;gap:6px;margin-top:8px"><a href="https://github.com/jyoushitou/Hoshinoumi" target="_blank" rel="noopener" style="font-size:9px;color:#2563eb;text-decoration:none">GitHub</a><span style="color:#c7d3e3">·</span><a href="https://github.com/jyoushitou" target="_blank" rel="noopener" style="font-size:9px;color:#6b7c95;text-decoration:none">作者 jyoushitou</a></div>';
      [top, msgs, composer, searchBar].forEach(x => x.classList.add('chat-hide'));
      pageView.classList.add('on');
      document.querySelectorAll('.rnav').forEach(x => x.classList.toggle('on', x.dataset.page === name));
      document.getElementById('backChat').addEventListener('click', () => showChat());
      document.getElementById('relogin').addEventListener('click', openLogin);
      return;
    }
    if (name === 'persona') {
      const PS = window.__personas || (window.__personas = [
        { name: 'nao', display: '友利奈绪', active: true, files: ['prompt','life','supplement','state','voice'], desc: '口语、简短、带行动；优先记住对话里的细枝末节。' },
        { name: 'student', display: '学生会长', active: false, files: ['prompt','state'], desc: '更正式、更克制的学生会语气，适合公共群。' }
      ]);
      function renderPersona() {
        const cards = PS.map((p, i) => '<div class="persona-card"><div class="persona-top"><div class="persona-ava">' + esc(p.display.slice(0,1)) + '</div><h3>' + esc(p.display) + ' · ' + esc(p.name) + '</h3>' + (p.active ? '<span class="pill">当前</span>' : '') + '</div><p>' + esc(p.desc) + '</p><div class="persona-files">' + p.files.map(f => '<span>' + esc(f) + '</span>').join('') + '</div><div class="persona-actions"><button data-act="preview" data-i="' + i + '">预览</button><button data-act="activate" data-i="' + i + '">' + (p.active ? '已激活' : '激活') + '</button><button data-act="export" data-i="' + i + '">导出</button></div></div>').join('');
        pageView.innerHTML = '<div class="page-head"><div><h2>人设</h2><p>v35.5 Web 演示 · MOCK 数据 · 导入 / 导出 / 激活</p></div><button class="back" id="backChat">← 返回聊天</button></div><div class="persona-toolbar"><button id="psImport">导入人设卡 JSON</button><input id="psFile" type="file" accept=".json,application/json"><span class="msg" id="psMsg">只读预览 · 仅 owner 可激活/导入</span></div><div class="persona-grid">' + cards + '</div>';
        [top, msgs, composer, searchBar].forEach(x => x.classList.add('chat-hide'));
        pageView.classList.add('on');
        document.querySelectorAll('.rnav').forEach(x => x.classList.toggle('on', x.dataset.page === name));
        function openSavingModal(kind) {
          const isGoal = kind === 'goal';
          const box = document.createElement('div');
          box.className = 'savings-modal';
          box.innerHTML = '<div class="box"><h3>' + (isGoal ? '新增存钱目标' : '新增冻结 / 待缴费') + '</h3>' +
            '<label>' + (isGoal ? '目标名称' : '缴费用途') + '<input id="smName" placeholder="' + (isGoal ? '旅行基金' : '房租') + '"></label>' +
            '<div class="row"><label>' + (isGoal ? '目标金额' : '冻结金额') + '<input id="smAmount" type="number" step="0.01" placeholder="1000"></label><label>' + (isGoal ? '已存金额' : '预计日期') + '<input id="smSecond" ' + (isGoal ? 'type="number" step="0.01" placeholder="0"' : 'placeholder="2027-03-01"') + '></label></div>' +
            '<label>' + (isGoal ? '截止日期' : '备注（可选）') + '<input id="smDue" placeholder="' + (isGoal ? '2027-06' : '每月固定 / 学费') + '"></label>' +
            '<div class="form-error" id="smErr"></div><div class="acts"><button id="smCancel">取消</button><button class="primary" id="smSave">保存</button></div></div>';
          pageView.appendChild(box);
          const close = () => box.remove();
          box.addEventListener('click', e => { if (e.target === box) close(); });
          box.querySelector('#smCancel').onclick = close;
          box.querySelector('#smSave').onclick = () => {
            const name = box.querySelector('#smName').value.trim();
            const amount = validMoney(box.querySelector('#smAmount').value);
            const err = box.querySelector('#smErr');
            if (!name) { err.textContent = '名称 / 用途不能为空'; box.querySelector('#smName').focus(); return; }
            if (!amount) { err.textContent = '金额必须大于 0，最多两位小数'; box.querySelector('#smAmount').focus(); return; }
            if (isGoal) {
              const saved = Number(box.querySelector('#smSecond').value || 0);
              if (saved < 0 || saved > amount) { err.textContent = '已存金额不能小于 0 或大于目标金额'; box.querySelector('#smSecond').focus(); return; }
            }
            if (isGoal) {
              const saved = Number(box.querySelector('#smSecond').value) || 0;
              S.goals.push({ name, saved, target: amount, due: box.querySelector('#smDue').value.trim() || '长期' });
            } else {
              S.frozen.push({ name, amount, due: box.querySelector('#smSecond').value.trim() || box.querySelector('#smDue').value.trim() || '待定' });
            }
            close(); renderSavings(); toast(isGoal ? '已新增存钱目标（MOCK）' : '已新增冻结 / 待缴费（MOCK）');
          };
        }
        document.getElementById('backChat').addEventListener('click', () => showChat());
        const cfToggle = document.getElementById('cfToggle');
        if (cfToggle) cfToggle.addEventListener('click', () => { const next = cfToggle.textContent.includes('12') ? 6 : 12; cfToggle.textContent = '近 ' + next + ' 个月'; const el = document.getElementById('webCfChart'); if (el) el.innerHTML = cashflowWebSvg(next); });
        document.getElementById('psImport').addEventListener('click', () => document.getElementById('psFile').click());
        document.getElementById('psFile').addEventListener('change', e => {
          const f = e.target.files[0]; if (!f) return;
          f.text().then(txt => {
            try {
              const d = JSON.parse(txt);
              PS.push({ name: d.name || ('imported' + (PS.length + 1)), display: d.display || d.name || '导入人设', active: false, files: Object.keys(d.files || d).filter(k => ['prompt','life','supplement','state','voice'].includes(k)), desc: d.desc || (d.prompt || '').slice(0, 60) || '导入的人设卡' });
              localStorage.setItem('hsh_personas', JSON.stringify(PS));
              renderPersona(); toast('已导入人设卡（MOCK）');
            } catch (err) { document.getElementById('psMsg').textContent = 'JSON 解析失败：' + err.message; }
          });
        });
        pageView.querySelectorAll('.persona-actions button').forEach(b => b.addEventListener('click', () => {
          const i = Number(b.dataset.i), p = PS[i], act = b.dataset.act;
          if (act === 'activate') { PS.forEach(x => x.active = false); p.active = true; renderPersona(); toast('已激活 ' + p.display + '（MOCK）'); }
          else if (act === 'preview') { toast('预览 ' + p.display + ' · prompt/life/state/voice'); }
          else if (act === 'export') {
            const blob = new Blob([JSON.stringify(p, null, 2)], { type: 'application/json' });
            const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = p.name + '.json'; a.click(); toast('已导出 ' + p.name + '.json');
          }
        }));
      }
      renderPersona();
      return;
    }
    if (name === 'diary') {
      const DESIGN_DIARY = [
        { id: 1, date: '2026-11-19', title: '方案通过', content: '今天方案终于过了，客户没有继续改。', mood: '轻松', source: '!diary' },
        { id: 2, date: '2026-11-18', title: '旅行目标 60%', content: '这个月结余三千三，旅行目标到六成了。', mood: '开心', source: '!diary' },
        { id: 3, date: '2026-11-17', title: '窗边读书', content: '读完《十日终焉》第 3 章，窗边光线刚好。', mood: '平静', source: '!diary' },
        { id: 4, date: '2026-10-28', title: '十月小记', content: '降温了，把夏天的衣服收起来，窗边开始有冷风。', mood: '平静', source: '!diary' }
      ];
      let diaryData = DESIGN_DIARY, diaryMonth = '';
      const monthOf = d => String(d || '').slice(0, 7);
      const preview = t => { const v = String(t || '').replace(/\s+/g, ' ').trim(); return v.length > 50 ? v.slice(0, 50) + '…' : v; };
      const render = () => {
        const months = [...new Set(diaryData.map(x => monthOf(x.date)))].filter(Boolean).sort().reverse();
        if (!diaryMonth || !months.includes(diaryMonth)) diaryMonth = months[0] || '';
        const rows = diaryData.filter(x => monthOf(x.date) === diaryMonth).sort((a, b) => String(b.date).localeCompare(String(a.date)));
        pageView.innerHTML = '<div class="diary-page"><div class="page-head"><div><h2>日记</h2><p>按月查看 · 前 50 字概览 · 点开详情</p></div><button class="back" id="backChat">← 返回聊天</button></div>' +
          '<div class="diary-months">' + months.map(m => '<button class="' + (m === diaryMonth ? 'on' : '') + '" data-diary-month="' + m + '">' + m.replace('-', ' 年 ') + ' 月</button>').join('') + '</div>' +
          '<div class="pgrid" id="diaryList">' + (rows.length ? rows.map(x => '<div class="pcard2" data-diary-id="' + x.id + '" style="cursor:pointer"><h3>' + esc(x.title || '无标题') + '</h3><p>' + esc(x.date + ' · ' + (x.mood || '')) + '</p><p style="margin-top:6px;color:#526982">' + esc(preview(x.content)) + '</p><p style="margin-top:8px;color:#2563eb;font-size:9px">查看</p></div>').join('') : '<div class="pcard2">这个月还没有日记</div>') + '</div></div>';
        document.getElementById('backChat').addEventListener('click', () => showChat());
        pageView.querySelectorAll('[data-diary-month]').forEach(b => b.addEventListener('click', () => { diaryMonth = b.dataset.diaryMonth; render(); }));
        pageView.querySelectorAll('[data-diary-id]').forEach(card => card.addEventListener('click', () => {
          const item = diaryData.find(x => String(x.id) === card.dataset.diaryId); if (!item) return;
          pageView.innerHTML = '<div class="diary-page"><div class="page-head"><div><h2>日记详情</h2><p>' + esc(item.date + ' · ' + (item.mood || '')) + '</p></div><button class="back" id="diaryBack">← 返回日记</button></div><div class="pcard2" style="max-width:760px"><h3 style="font-size:16px">' + esc(item.title || '无标题') + '</h3><p style="font-size:9px;color:#8a9bb0">' + esc(item.date + ' · ' + (item.source || '!diary')) + '</p><p style="margin-top:14px;font-size:11px;line-height:1.9;color:#405872;white-space:pre-wrap">' + esc(item.content || '') + '</p></div></div>';
          document.getElementById('diaryBack').addEventListener('click', render);
        }));
      };
      pageView.classList.add('on');
      [top, msgs, composer, searchBar].forEach(x => x.classList.add('chat-hide'));
      document.querySelectorAll('.rnav').forEach(x => x.classList.toggle('on', x.dataset.page === 'diary'));
      render();
      fetch('http://127.0.0.1:27005/api/diary?all=1', { headers: { Authorization: 'Bearer mock-token' } })
        .then(r => r.ok ? r.json() : Promise.reject())
        .then(j => { if (Array.isArray(j.data) && j.data.length) { diaryData = j.data; render(); } })
        .catch(() => {});
      return;
    }
    if (name === 'plugins') {
      const pluginCard = (title, desc, action, label) => '<div class="pcard2 plugin-card"><div class="plugin-copy"><h3>' + title + '</h3><p>' + desc + '</p></div><button class="plugin-action" onclick="toast(&quot;' + action + '（演示）&quot;)">' + label + '</button></div>';
      pageView.innerHTML = '<div class="page-head"><div><h2>插件</h2><p>安装 / 审批 / 权限 / 错误 · 独立管理页</p></div><button class="back" id="backChat">← 返回聊天</button></div>' +
        '<div class="pgrid">' +
        '<div class="pcard2 plugin-section"><h3>已安装 6</h3>' + pluginCard('天气 · weather', '读天气 · network · v1.2.0', '已停用 weather', '停用') + pluginCard('读书摘要 · reader', '读写书架 · filesystem / db · v1.0.3', '已停用 reader', '停用') + pluginCard('音乐 · music', '播放 / 搜索 · network · v0.9.1', '已启用 music', '启用') + '</div>' +
        '<div class="pcard2 plugin-section"><h3>待审批 1</h3><div class="plugin-card"><div class="plugin-copy"><h3>记账助手 · ledger</h3><p>读写财务 · finance · 仅 owner</p></div><div class="plugin-actions"><button class="plugin-action primary" onclick="toast(&quot;已批准 ledger（演示）&quot;)">批准</button><button class="plugin-action danger" onclick="toast(&quot;已拒绝 ledger（演示）&quot;)">拒绝</button></div></div><h3 style="margin-top:14px">权限</h3><div class="plugin-line"><span>network</span><b>2 个插件</b></div><div class="plugin-line"><span>filesystem</span><b>1 个</b></div><div class="plugin-line"><span>finance</span><b>需 owner</b></div></div>' +
        '<div class="pcard2 plugin-section"><h3>其他已安装</h3>' + pluginCard('面板 · dashboard', '前端 slot · read-only · v1.0.0', '已停用 dashboard', '停用') + pluginCard('提醒 · reminder', '定时提醒 · notifications · v1.0.2', '已停用 reminder', '停用') + '</div>' +
        '<div class="pcard2 plugin-section"><h3>错误</h3><div class="plugin-line"><span>music 播放失败</span><b>20:12</b></div><div class="plugin-line"><span>weather 请求超时</span><b>18:03</b></div></div></div>';
      pageView.classList.add('on');
      [top, msgs, composer, searchBar].forEach(x => x.classList.add('chat-hide'));
      document.querySelectorAll('.rnav').forEach(x => x.classList.toggle('on', x.dataset.page === 'plugins'));
      document.getElementById('backChat').addEventListener('click', () => showChat());
      return;
    }
    if (name === 'logs') {
      const LOGS = window.__logs || (window.__logs = [
        ['09:13','INFO','chat','len=18 target=10001'],
        ['09:12','INFO','command','status'],
        ['09:11','INFO','memory','append 2 条'],
        ['09:08','INFO','relation','affinity +0.020'],
        ['09:04','WARN','search_images','timeout after 5000ms'],
        ['08:58','INFO','memory','append 1 条'],
        ['08:55','INFO','chat','reply len=32'],
        ['08:42','INFO','cron','每日早报 已触发'],
        ['08:31','INFO','gateway','client connected 127.0.0.1'],
        ['08:22','INFO','chat','reply len=21'],
        ['08:10','WARN','vision','OCR slow 3210ms'],
        ['08:02','INFO','savings','entry +500.00 saving'],
        ['07:58','INFO','persona','active nao'],
        ['07:45','INFO','chat','reply len=16'],
        ['07:31','INFO','db','schema 35 · 42 tables'],
        ['07:20','INFO','gw','tcp frame 27004 ok'],
        ['07:02','INFO','cron','日记提醒 已触发'],
        ['06:58','INFO','chat','reply len=24'],
        ['06:40','ERROR','search_images','connection reset'],
        ['06:31','INFO','memory','recall 3 条']
      ]);
      let level = 'ALL', q = '';
      function renderLogs() {
        pageView.innerHTML = '<div class="page-head"><div><h2>运行日志</h2><p>v35.5 Web 演示 · MOCK 数据 · 一行一条</p></div><button class="back" id="backChat">← 返回聊天</button></div>' +
          '<div class="log-toolbar"><select id="logLevel"><option value="ALL">全部级别</option><option>INFO</option><option>WARN</option><option>ERROR</option></select><input id="logQ" placeholder="搜索日志…"><button class="back" id="logRefresh">刷新</button><button class="back" id="logClear">清空</button><span class="hint" id="logCount"></span></div>' +
          '<div class="log-console" id="logConsole"></div>';
        document.getElementById('backChat').addEventListener('click', () => showChat());
        document.getElementById('logLevel').value = level;
        document.getElementById('logLevel').addEventListener('change', e => { level = e.target.value; paintLogs(); });
        document.getElementById('logQ').value = q;
        document.getElementById('logQ').addEventListener('input', e => { q = e.target.value; paintLogs(); });
        document.getElementById('logRefresh').addEventListener('click', () => { paintLogs(); toast('日志已刷新（MOCK）'); });
        document.getElementById('logClear').addEventListener('click', () => { window.__logs = []; LOGS.length = 0; paintLogs(); });
        paintLogs();
      }
      function paintLogs() {
        const box = document.getElementById('logConsole');
        const list = LOGS.filter(l => (level === 'ALL' || l[1] === level) && (!q || l.join(' ').toLowerCase().includes(q.toLowerCase())));
        document.getElementById('logCount').textContent = list.length + ' 条';
        box.innerHTML = list.length ? list.map(l => '<div class="log-line"><span class="lt">' + esc(l[0]) + '</span><span class="lv ' + esc(l[1]) + '">' + esc(l[1]) + '</span><span class="lm">' + esc(l[2] + '  ' + l[3]) + '</span></div>').join('') : '<div class="log-empty">没有匹配的日志</div>';
        box.scrollTop = box.scrollHeight;
      }
      renderLogs();
      [top, msgs, composer, searchBar].forEach(x => x.classList.add('chat-hide'));
      pageView.classList.add('on');
      document.querySelectorAll('.rnav').forEach(x => x.classList.toggle('on', x.dataset.page === name));
      return;
    }
    if (name === 'cron') {
      const C = window.__cron || (window.__cron = {
        nextId: 4,
        items: [
          { id: 1, name: '每日早报', expr: '0 8 * * *', desc: '每天 08:00', enabled: true },
          { id: 2, name: '日记提醒', expr: '30 22 * * *', desc: '每天 22:30', enabled: true },
          { id: 3, name: '健康检查', expr: '0 * * * *', desc: '每小时', enabled: false }
        ]
      });
      let editing = null, showForm = false;
      function renderCron() {
        const list = C.items.map(x => '<div class="cron-item"><span class="cron-dot' + (x.enabled ? '' : ' off') + '"></span><div class="cron-main"><div class="n">' + esc(x.name) + '</div><div class="e">' + esc(x.expr) + ' · ' + esc(x.desc) + '</div></div><span class="cron-state' + (x.enabled ? '' : ' off') + '">' + (x.enabled ? '启用' : '停用') + '</span><div class="cron-btns"><button data-act="run" data-id="' + x.id + '">立即运行</button><button data-act="edit" data-id="' + x.id + '">编辑</button><button data-act="toggle" data-id="' + x.id + '">' + (x.enabled ? '停用' : '启用') + '</button><button class="danger" data-act="del" data-id="' + x.id + '">删除</button></div></div>').join('');
        const form = showForm ? '<div class="cron-form"><div><label>名称</label><input id="crName" value="' + esc(editing ? editing.name : '') + '" placeholder="每日早报"></div><div><label>Cron</label><input id="crExpr" value="' + esc(editing ? editing.expr : '0 8 * * *') + '" placeholder="0 8 * * *"></div><div><label>说明</label><input id="crDesc" value="' + esc(editing ? editing.desc : '每天 08:00') + '"></div><div class="full"><label style="display:flex;align-items:center;gap:4px"><input type="checkbox" id="crEnabled" ' + (!editing || editing.enabled ? 'checked' : '') + '> 启用</label><button id="crSave">' + (editing ? '保存修改' : '新增任务') + '</button><button class="cancel" id="crCancel">取消</button><span class="msg" id="crMsg"></span></div></div>' : '';
        pageView.innerHTML = '<div class="page-head"><div><h2>定时任务</h2><p>v35.5 Web 演示 · MOCK 数据 · 支持增加 / 修改 / 删除</p></div><div style="margin-left:auto;display:flex;gap:7px"><button class="back" id="crAdd">＋ 新增任务</button><button class="back" id="backChat">← 返回聊天</button></div></div>' + form + '<div class="cron-list">' + list + '</div>';
        [top, msgs, composer, searchBar].forEach(x => x.classList.add('chat-hide'));
        pageView.classList.add('on');
        document.querySelectorAll('.rnav').forEach(x => x.classList.toggle('on', x.dataset.page === name));
        document.getElementById('backChat').addEventListener('click', () => showChat());
        document.getElementById('crAdd').addEventListener('click', () => { editing = null; showForm = true; renderCron(); });
        pageView.querySelectorAll('.cron-btns button').forEach(b => b.addEventListener('click', () => {
          const id = Number(b.dataset.id), act = b.dataset.act, item = C.items.find(x => x.id === id);
          if (!item) return;
          if (act === 'run') { toast('已运行 ' + item.name + '（MOCK）'); return; }
          if (act === 'toggle') { item.enabled = !item.enabled; renderCron(); toast((item.enabled ? '已启用 ' : '已停用 ') + item.name); return; }
          if (act === 'edit') { editing = item; showForm = true; renderCron(); return; }
          if (act === 'del') { C.items = C.items.filter(x => x.id !== id); renderCron(); toast('已删除 ' + item.name); }
        }));
        const save = document.getElementById('crSave');
        if (save) save.addEventListener('click', () => {
          const name = document.getElementById('crName').value.trim();
          const expr = document.getElementById('crExpr').value.trim();
          const desc = document.getElementById('crDesc').value.trim();
          const enabled = document.getElementById('crEnabled').checked;
          if (!name || !expr) { document.getElementById('crMsg').textContent = '名称和 Cron 必填'; return; }
          if (editing) Object.assign(editing, { name, expr, desc, enabled });
          else C.items.push({ id: C.nextId++, name, expr, desc: desc || expr, enabled });
          editing = null; showForm = false; renderCron(); toast('任务已保存（MOCK）');
        });
        const cancel = document.getElementById('crCancel');
        if (cancel) cancel.addEventListener('click', () => { editing = null; showForm = false; renderCron(); });
      }
      renderCron();
      return;
    }
    if (name === 'info') {
      pageView.innerHTML = '<div class="page-head"><div><h2>信息</h2><p>v35.5 Web 演示 · MOCK 数据 · 运行状态 / 数据库 / 计划 / 阅读</p></div><button class="back" id="backChat">← 返回聊天</button></div>' +
        '<div class="info-stats"><div class="info-stat"><div class="k">版本</div><div class="v">v35.5</div></div><div class="info-stat"><div class="k">schema</div><div class="v">35</div></div><div class="info-stat"><div class="k">数据表</div><div class="v">42</div></div><div class="info-stat"><div class="k">命令</div><div class="v">51</div></div></div>' +
        '<div class="info-grid">' +
        '<div class="info-panel"><h3>运行 <span>已连接</span></h3><div class="info-row"><span>后端</span><b>127.0.0.1:27004</b></div><div class="info-row"><span>延迟</span><b class="ok">42ms</b></div><div class="info-row"><span>运行时长</span><b>6 天 4 小时</b></div><div class="info-row"><span>API 余额</span><b>¥126.40</b></div></div>' +
        '<div class="info-panel"><h3>数据库 <span>schema 35</span></h3><div class="info-row"><span>引擎</span><b>MySQL 8</b></div><div class="info-row"><span>表数量</span><b>42</b></div><div class="info-row"><span>记忆 / 事件</span><b>4 / 7</b></div><div class="info-row"><span>日志</span><b>24 条</b></div></div>' +
        '<div class="info-panel"><h3>日志 <span>最近 24h</span></h3><div class="info-row"><span>INFO</span><b>23 条</b></div><div class="info-row"><span>WARN</span><b class="warn">1 条</b></div><div class="info-row"><span>最新</span><b>09:13 chat len=18</b></div><div class="info-row"><span>失败</span><b class="warn">search_images timeout</b></div></div>' +
        '<div class="info-panel"><h3>学习计划 <span>已读取</span></h3><div class="info-row"><span>当前</span><b>读书 · 《十日终焉》</b></div><div class="info-row"><span>进度</span><b>60%</b></div><div class="info-row"><span>本周</span><b>3 小时</b></div><div class="info-row"><span>下一项</span><b>复盘 · 周日</b></div></div>' +
        '<div class="info-panel"><h3>阅读 <span>书架</span></h3><div class="info-row"><span>在读</span><b>《十日终焉》</b></div><div class="info-row"><span>进度</span><b>62%</b></div><div class="info-row"><span>本周</span><b>3h 20m</b></div><div class="info-row"><span>读完</span><b>12 本</b></div></div>' +
        '<div class="info-panel"><h3>多端 <span>在线</span></h3><div class="info-row"><span>Web</span><b class="ok">当前</b></div><div class="info-row"><span>VS Code</span><b class="ok">已连接</b></div><div class="info-row"><span>DSH</span><b class="ok">已连接</b></div><div class="info-row"><span>网关</span><b>v26.4 · TCP</b></div></div>' +
        '</div>';
      [top, msgs, composer, searchBar].forEach(x => x.classList.add('chat-hide'));
      pageView.classList.add('on');
      document.querySelectorAll('.rnav').forEach(x => x.classList.toggle('on', x.dataset.page === name));
      document.getElementById('backChat').addEventListener('click', () => showChat());
      return;
    }
    if (name === 'weekly') {
      const WD = ['周一','周二','周三','周四','周五','周六','周日'];
      const W = window.__weekly || (window.__weekly = {
        week: currentIsoWeek(),
        periods: {},
        courses: [
          { day: 0, period: 1, name: '高等数学', teacher: '李老师', loc: '教三 201' },
          { day: 2, period: 3, name: '大学英语', teacher: '王老师', loc: '文科楼 104' },
          { day: 4, period: 5, name: '数据结构', teacher: '陈老师', loc: '实验楼 302' }
        ]
      });
      const PERIOD_DEFAULT = [
        { no: 1, time: '08:00-08:45' }, { no: 2, time: '08:55-09:40' },
        { no: 3, time: '10:00-10:45' }, { no: 4, time: '10:55-11:40' },
        { no: 5, time: '14:00-14:45' }, { no: 6, time: '14:55-15:40' }
      ];
      function getPeriods(w) {
        if (!W.periods[w]) {
          const count = w === 13 ? 8 : w === 14 ? 4 : 6;
          const base = PERIOD_DEFAULT.slice();
          W.periods[w] = Array.from({ length: count }, (_, i) => base[i] || { no: i + 1, time: i === 7 ? '16:55-17:40' : '16:00-16:45' });
        }
        return W.periods[w];
      }
      let sel = { day: 0, period: 1 }, editIdx = -1, showPeriods = false;
      function renderWeekly() {
        let html = '<div class="page-head"><div><h2>周计划表</h2><p>v35.5 Web 演示 · MOCK 数据 · 第 ' + W.week + ' 周</p></div><button class="back" id="backChat">← 返回聊天</button></div>';
        html += '<div class="week-toolbar"><label>周次 <input id="wkNum" type="number" min="1" max="53" value="' + W.week + '"></label><button id="wkGo">跳转</button><button id="wkPeriods">节次设置</button><label class="file-btn">导入 HTML<input id="wkFile" type="file" accept=".html,text/html"></label><span class="week-msg" id="wkMsg">点击空格子新增；点课程编辑/删除</span></div>';
        if (showPeriods) {
          const ps = getPeriods(W.week);
          html += '<div class="week-period-editor"><div class="wpe-head"><b>第 ' + W.week + ' 周节次</b><button id="wpeAdd">＋ 添加节次</button></div>' + ps.map((p, i) => '<div class="wpe-row"><span>第 ' + p.no + ' 节</span><input data-pi="' + i + '" value="' + esc(p.time) + '"><button class="wpe-del" data-pi="' + i + '">删除</button></div>').join('') + '<div class="wpe-actions"><button id="wpeSave">保存本周节次</button><span class="msg" id="wpeMsg"></span></div></div>';
        }
        html += '<div class="week-wrap"><div class="week-grid">';
        html += '<div class="h">节次</div>' + WD.map(d => '<div class="h">' + d + '</div>').join('');
        const periods = getPeriods(W.week);
        periods.forEach(period => {
          const p = period.no;
          html += '<div class="p"><b>' + p + '</b><span>' + esc(period.time || '') + '</span></div>';
          for (let d = 0; d < 7; d++) {
            const idx = W.courses.findIndex(c => c.day === d && c.period === p);
            html += '<div class="week-cell' + (sel.day === d && sel.period === p ? ' sel' : '') + '" data-day="' + d + '" data-period="' + p + '">';
            if (idx >= 0) {
              const c = W.courses[idx];
              html += '<div class="course" data-idx="' + idx + '"><b>' + esc(c.name) + '</b><span>' + esc(c.loc) + '</span></div>';
            }
            html += '</div>';
          }
        });
        html += '</div></div>';
        const c = editIdx >= 0 ? W.courses[editIdx] : null;
        html += '<div class="week-form"><div><label>课程名</label><input id="wkName" value="' + esc(c ? c.name : '') + '"></div><div><label>地点</label><input id="wkLoc" value="' + esc(c ? c.loc : '') + '"></div><div class="full"><button id="wkSave">' + (editIdx >= 0 ? '保存修改' : '添加到格子') + '</button>' + (editIdx >= 0 ? '<button class="del" id="wkDel">删除课程</button>' : '') + '<span class="msg" id="wkFormMsg"></span></div></div>';
        pageView.innerHTML = html;
        document.getElementById('backChat').addEventListener('click', () => showChat());
        document.getElementById('wkGo').addEventListener('click', () => {
          const n = Number(document.getElementById('wkNum').value); if (n >= 1 && n <= 53) { W.week = n; getPeriods(n); renderWeekly(); }
        });
        document.getElementById('wkPeriods').addEventListener('click', () => { showPeriods = !showPeriods; renderWeekly(); });
        const wpeAdd = document.getElementById('wpeAdd');
        if (wpeAdd) wpeAdd.addEventListener('click', () => {
          const ps = getPeriods(W.week); ps.push({ no: ps.length + 1, time: '16:00-16:45' }); renderWeekly();
        });
        pageView.querySelectorAll('.wpe-del').forEach(b => b.addEventListener('click', () => {
          const ps = getPeriods(W.week); const i = Number(b.dataset.pi);
          const no = ps[i].no; ps.splice(i, 1); ps.forEach((p, j) => p.no = j + 1);
          W.courses = W.courses.filter(c => c.period !== no);
          renderWeekly();
        }));
        const wpeSave = document.getElementById('wpeSave');
        if (wpeSave) wpeSave.addEventListener('click', () => {
          const ps = getPeriods(W.week);
          pageView.querySelectorAll('[data-pi]').forEach(inp => { const i = Number(inp.dataset.pi); if (ps[i] && inp.value.trim()) ps[i].time = inp.value.trim(); });
          showPeriods = false; renderWeekly(); toast('第 ' + W.week + ' 周节次已保存（MOCK）');
        });
        pageView.querySelectorAll('.week-cell').forEach(cell => cell.addEventListener('click', e => {
          if (e.target.closest('.course')) return;
          sel = { day: Number(cell.dataset.day), period: Number(cell.dataset.period) }; editIdx = -1; renderWeekly();
        }));
        pageView.querySelectorAll('.course').forEach(c => c.addEventListener('click', e => {
          e.stopPropagation(); editIdx = Number(c.dataset.idx);
          const cc = W.courses[editIdx]; sel = { day: cc.day, period: cc.period }; renderWeekly();
        }));
        document.getElementById('wkSave').addEventListener('click', () => {
          const name = document.getElementById('wkName').value.trim();
          const loc = document.getElementById('wkLoc').value.trim();
          if (!name) { document.getElementById('wkFormMsg').textContent = '先填课程名'; return; }
          if (editIdx >= 0) W.courses[editIdx] = { ...W.courses[editIdx], name, loc };
          else W.courses.push({ day: sel.day, period: sel.period, name, loc });
          editIdx = -1; renderWeekly(); toast('周计划已更新（MOCK）');
        });
        const del = document.getElementById('wkDel');
        if (del) del.addEventListener('click', () => { W.courses.splice(editIdx, 1); editIdx = -1; renderWeekly(); toast('课程已删除（MOCK）'); });
        const file = document.getElementById('wkFile');
        file.addEventListener('change', () => {
          const f = file.files[0]; if (!f) return; const msg = document.getElementById('wkMsg');
          f.text().then(txt => {
            const doc = new DOMParser().parseFromString(txt, 'text/html');
            const table = doc.querySelector('#KebiaoTable1') || doc.querySelector('table');
            if (!table) { msg.textContent = '没有找到课表表格'; return; }
            let n = 0;
            table.querySelectorAll('tr').forEach((tr, ri) => {
              if (ri === 0) return;
              tr.querySelectorAll('td').forEach((td, di) => {
                const t = td.innerText.trim(); if (!t) return;
                const lines = t.split(/\n+/).map(x => x.trim()).filter(Boolean);
                W.courses.push({ day: Math.max(0, Math.min(6, di)), period: Math.min(6, ri), name: lines[0] || '课程', teacher: lines[1] || '', loc: lines[2] || '', weeks: '1-16周' });
                n++;
              });
            });
            renderWeekly(); toast('HTML 导入 ' + n + ' 条（MOCK）');
          });
        });
      }
      renderWeekly();
      [top, msgs, composer, searchBar].forEach(x => x.classList.add('chat-hide'));
      pageView.classList.add('on');
      document.querySelectorAll('.rnav').forEach(x => x.classList.toggle('on', x.dataset.page === name));
      return;
    }
    if (name === 'savings') {
      /* v35.9.1 design: goals/accounts/frozen */
      const S = window.__savings || (window.__savings = {
        income: 8000, expense: 3200,
        goals: [
          { name: '旅行基金', saved: 1800, target: 5000, due: '2027-03' },
          { name: '新电脑', saved: 900, target: 6000, due: '2027-06' },
          { name: '应急金', saved: 1200, target: 10000, due: '长期' }
        ],
        funds: [
          { name: '余额宝', type: '货币基金', value: 1500, rate: 1.35, profit: 0.05, account: '支付宝', redeem: '快速赎回' },
          { name: '沪深300指数', type: '基金', value: 800, rate: 0, profit: 50, account: '银行卡', redeem: 'T+1' }
        ],
        fixed: [
          { name: '12 个月定期', amount: 2000, rate: 1.65, months: 12, due: '2027-06-01', account: '银行卡', deducted: false },
          { name: '3 个月定期', amount: 1000, rate: 1.15, months: 3, due: '2027-02-01', account: '支付宝', deducted: false }
        ],
        frozen: [
          { name: '房租', amount: 1800, due: '每月 5 日' },
          { name: '学费', amount: 2000, due: '2027-02-20' },
          { name: '水电费', amount: 300, due: '每月 20 日' }
        ],
        saved: 3300, target: 5500,
        accounts: [['银行卡', 5300.00], ['支付宝', 1200], ['微信', 300], ['现金', 0]],
        entries: [
          ['11-19', 'expense', '银行卡', '午饭', -35.5],
          ['11-18', 'saving', '银行卡', '旅行目标', 500],
          ['11-17', 'income', '银行卡', '兼职', 800]
        ]
      });
      function money(n){ return '¥' + Number(n || 0).toLocaleString('zh-CN', {minimumFractionDigits: 2, maximumFractionDigits: 2}); }
      const CF_ALL = [
        {m:'2025-12',i:6200,e:4100},{m:'2026-01',i:9800,e:5600},{m:'2026-02',i:7400,e:4800},
        {m:'2026-03',i:8100,e:6200},{m:'2026-04',i:6900,e:5300},{m:'2026-05',i:8800,e:4900},
        {m:'2026-06',i:7600,e:5700},{m:'2026-07',i:9100,e:6100},{m:'2026-08',i:8300,e:5200},
        {m:'2026-09',i:7800,e:5900},{m:'2026-10',i:8600,e:5000},{m:'2026-11',i:8200,e:5430}
      ];
      function cashflowWebSvg(count){
        const data = count === 6 ? CF_ALL.slice(-6) : CF_ALL;
        const w=900,h=220,pad={l:38,r:10,t:12,b:24},iw=w-pad.l-pad.r,ih=h-pad.t-pad.b;
        const max=Math.max(...data.map(d=>Math.max(d.i,d.e)),1),step=iw/data.length,bw=Math.max(6,Math.min(20,step*.27));
        let out='';
        for(let g=0;g<=3;g++){const y=pad.t+ih*g/3;const val=Math.round(max*(3-g)/3);out+=`<line class="axis" x1="${pad.l}" y1="${y}" x2="${w-pad.r}" y2="${y}"/><text x="${pad.l-6}" y="${y+3}" text-anchor="end">${val>=1000?(val/1000).toFixed(0)+'k':val}</text>`}
        data.forEach((d,idx)=>{const x=pad.l+idx*step,ihh=d.i/max*ih,ehh=d.e/max*ih;out+=`<rect class="bar" x="${x+step/2-bw-1}" y="${pad.t+ih-ihh}" width="${bw}" height="${ihh}" rx="3" fill="#60a5fa"/><rect class="bar" x="${x+step/2+1}" y="${pad.t+ih-ehh}" width="${bw}" height="${ehh}" rx="3" fill="#fca5a5"/><text x="${x+step/2}" y="${h-7}" text-anchor="middle">${d.m.slice(5)}</text>`});
        const pts=data.map((d,idx)=>`${pad.l+idx*step+step/2},${pad.t+ih-(d.i-d.e)/max*ih}`).join(' ');out+=`<polyline class="netline" points="${pts}"/>`;
        return `<svg class="cf-web-svg" viewBox="0 0 ${w} ${h}" role="img" aria-label="每月流水">${out}</svg>`;
      }
      function renderSavings() {
        const today = new Date(); today.setHours(23, 59, 59, 999);
        S.fixed = (S.fixed || []).filter(f => {
          const due = new Date(String(f.due || '') + 'T00:00:00');
          if (Number.isNaN(due.getTime()) || due > today) return true;
          const interest = Number(f.amount || 0) * Number(f.rate || 0) / 100 * ((f.months || 12) / 12);
          const acc = S.accounts.find(a => a[0] === (f.account || '银行卡')) || S.accounts[0];
          if (acc) acc[1] = Number(acc[1] || 0) + Number(f.amount || 0) + interest;
          S.entries.unshift([new Date().toISOString().slice(5, 10), 'income', acc ? acc[0] : '银行卡', f.name + ' 到期自动转回', Number(f.amount || 0) + interest]);
          return false;
        });
        const rows = S.entries.map(e => '<div class="entry"><span class="tag">' + esc(e[1]) + '</span><span>' + esc(e[2]) + ' · ' + esc(e[3]) + '</span><span class="amt ' + (e[4] < 0 ? 'neg' : 'pos') + '">' + (e[4] > 0 ? '+' : '') + money(e[4]) + '</span><span style="color:#9aabbe">' + esc(e[0]) + '</span></div>').join('');
        const total = S.accounts.reduce((n, a) => n + Number(a[1] || 0), 0);
        const frozen = (S.frozen || []).reduce((n, f) => n + Number(f.amount || 0), 0);
        const fixedTotal = (S.fixed || []).reduce((n, f) => n + Number(f.amount || 0), 0);
        const fundTotal = (S.funds || []).reduce((n, f) => n + Number(f.value || 0), 0);
        const assetTotal = total + fixedTotal + fundTotal;
        const available = assetTotal - frozen - fixedTotal - fundTotal;
        const fundCards = (S.funds || []).map(f => '<div class="fund-row"><div><div class="fund-name">' + esc(f.name) + ' <span class="fund-tag">' + esc(f.type) + '</span></div><div class="fund-meta">' + (f.rate ? '7 日年化 ' + Number(f.rate).toFixed(2) + '% · ' : '') + '收益 ' + money(f.profit) + ' · ' + esc(f.account) + ' · ' + esc(f.redeem) + '</div></div><div class="fund-value">' + money(f.value) + '<small>持有金额</small></div></div>').join('');
        const fixedCards = (S.fixed || []).map((f, i) => '<div class="fixed-card"><div class="main"><div class="name">' + esc(f.name) + '<span class="fixed-lock">锁定</span></div><div class="meta">年利率 ' + Number(f.rate).toFixed(2) + '% · 到期 ' + esc(f.due) + ' · 预计利息 ' + money(f.amount * f.rate / 100 * ((f.months || 12) / 12)) + ' · 到期回 ' + esc(f.account || '银行卡') + (f.deducted === false ? ' · 补录' : '') + '</div></div><div class="val"><b>' + money(f.amount) + '</b><small>本金</small></div><div class="fixed-acts"><button class="cancel" data-cancel="' + i + '">取消</button></div></div>').join('');
        const goalCards = (S.goals || []).map(g => {
          const pct = g.target ? Math.min(100, Math.round(g.saved / g.target * 100)) : 0;
          return '<div class="goal-card"><div class="goal-top"><b>' + esc(g.name) + '</b><span>截止 ' + esc(g.due) + '</span></div><div class="goal-amt">' + money(g.saved) + ' <small>/ ' + money(g.target) + '</small></div><div class="gbar"><i style="width:' + pct + '%"></i></div><div class="goal-foot"><span>' + pct + '%</span><span>还差 ' + money(Math.max(0, g.target - g.saved)) + '</span></div></div>';
        }).join('');
        const accountRows = S.accounts.map(a => '<div class="money-row"><div><div>' + esc(a[0]) + '</div><div class="where">' + (a[1] ? '资金位置' : '暂无余额') + '</div></div><span class="amt">' + money(a[1]) + '</span></div>').join('');
        const frozenRows = (S.frozen || []).map((f, i) => '<div class="frozen-row"><div><div>' + esc(f.name) + '</div><div class="why">预计 ' + esc(f.due) + ' · 不可动用</div></div><div class="frozen-right"><span class="amt">' + money(f.amount) + '</span><span class="frozen-acts"><button data-pay="' + i + '">已缴费</button><button class="del" data-del="' + i + '">删除</button></span></div></div>').join('');
        pageView.innerHTML = '<div class="page-head"><div><h2>存钱</h2><p>v35.5 Web 演示 · 多目标 / 资金位置 / 冻结预留</p></div><button class="back" id="backChat">← 返回聊天</button></div>' +
          '<div class="savings-grid"><div class="savings-stat"><div class="k">可用余额</div><div class="v blue">' + money(available) + '</div></div><div class="savings-stat stat-amber"><div class="k">冻结 / 预留</div><div class="v">' + money(frozen) + '</div></div><div class="savings-stat"><div class="k">定期存款</div><div class="v">' + money(fixedTotal) + '</div></div><div class="savings-stat"><div class="k">总资产</div><div class="v">' + money(assetTotal) + '</div></div></div>' +
          '<div class="savings-panel cashflow-panel"><div class="panel-head"><h3>每月流水</h3><button class="mini-add" id="cfToggle">近 12 个月</button></div><div class="cf-kpis"><div><small>本月收入</small><b style="color:#1f9d6b">¥8,200</b></div><div><small>本月支出</small><b style="color:#dc2626">¥5,430</b></div><div><small>本月结余</small><b style="color:#2563eb">+¥2,770</b></div></div><div id="webCfChart">' + cashflowWebSvg(12) + '</div><div class="cf-legend"><span><i style="background:#60a5fa"></i>收入</span><span><i style="background:#fca5a5"></i>支出</span><span><i style="background:#0f766e"></i>净结余</span><em>仅主人可见 · 互转不计入</em></div></div>' +
          '<div class="savings-panel"><div class="panel-head"><h3>存钱目标</h3><button class="mini-add" id="addGoal">＋ 新目标</button></div><div class="savings-goals">' + goalCards + '</div></div>' +
          '<div class="savings-panel"><div class="panel-head"><h3>定期存款</h3><button class="mini-add" id="addFixed">＋ 存定期</button></div>' + fixedCards + '<div class="frozen-tip">到期自动按来源账户转回本金+利息，无需手动操作。</div></div>' +
          '<div class="savings-panel"><div class="panel-head"><h3>理财 / 基金</h3><button class="mini-add" id="addFund">＋ 买入</button></div>' + fundCards + '</div>' +
          '<div class="savings-two"><div class="savings-panel"><h3>钱存在哪</h3>' + accountRows + '<div class="frozen-tip">总余额 ' + money(total) + ' = 各账户余额合计</div></div><div class="savings-panel"><div class="panel-head"><h3>冻结 / 待缴费</h3><button class="mini-add" id="addFrozen">＋ 新增</button></div>' + frozenRows + '<div class="frozen-tip">可用余额 = 总资产 ' + money(assetTotal) + ' - 冻结 ' + money(frozen) + ' - 定期 ' + money(fixedTotal) + ' - 理财 ' + money(fundTotal) + ' = <b>' + money(available) + '</b></div></div></div>' +
          '<div class="savings-two"><div class="savings-panel"><h3>记一笔</h3><div class="savings-form"><div><label>金额</label><input id="svAmount" type="number" step="0.01" placeholder="35.50"></div><div><label>账户</label><select id="svAccount">' + S.accounts.map(a => '<option>' + esc(a[0]) + '</option>').join('') + '</select></div><div><label>类型</label><select id="svKind"><option value="expense">支出</option><option value="income">收入</option><option value="saving">存钱</option></select></div><div class="full"><label>备注</label><input id="svNote" placeholder="午饭 / 旅行目标 / 兼职"></div><div class="actions"><button id="svSave">保存</button><span class="import-status" id="svMsg"></span></div></div></div><div class="savings-panel"><h3>最近流水</h3><div class="entry-list">' + rows + '</div></div></div>';
        document.getElementById('backChat').addEventListener('click', () => showChat());
        function openSavingModal(kind) {
          const isGoal = kind === 'goal';
          const box = document.createElement('div');
          box.className = 'savings-modal';
          box.innerHTML = '<div class="box"><h3>' + (isGoal ? '新增存钱目标' : '新增冻结 / 待缴费') + '</h3>' +
            '<label>' + (isGoal ? '目标名称' : '缴费用途') + '<input id="smName" placeholder="' + (isGoal ? '旅行基金' : '房租') + '"></label>' +
            '<div class="row"><label>' + (isGoal ? '目标金额' : '冻结金额') + '<input id="smAmount" type="number" step="0.01" placeholder="1000"></label><label>' + (isGoal ? '已存金额' : '预计日期') + '<input id="smSecond" ' + (isGoal ? 'type="number" step="0.01" placeholder="0"' : 'placeholder="2027-03-01"') + '></label></div>' +
            '<label>' + (isGoal ? '截止日期' : '备注（可选）') + '<input id="smDue" placeholder="' + (isGoal ? '2027-06' : '每月固定 / 学费') + '"></label>' +
            '<div class="form-error" id="smErr"></div><div class="acts"><button id="smCancel">取消</button><button class="primary" id="smSave">保存</button></div></div>';
          pageView.appendChild(box);
          const close = () => box.remove();
          box.addEventListener('click', e => { if (e.target === box) close(); });
          box.querySelector('#smCancel').onclick = close;
          box.querySelector('#smSave').onclick = () => {
            const name = box.querySelector('#smName').value.trim();
            const amount = validMoney(box.querySelector('#smAmount').value);
            const err = box.querySelector('#smErr');
            if (!name) { err.textContent = '名称 / 用途不能为空'; box.querySelector('#smName').focus(); return; }
            if (!amount) { err.textContent = '金额必须大于 0，最多两位小数'; box.querySelector('#smAmount').focus(); return; }
            if (isGoal) {
              const saved = Number(box.querySelector('#smSecond').value || 0);
              if (saved < 0 || saved > amount) { err.textContent = '已存金额不能小于 0 或大于目标金额'; box.querySelector('#smSecond').focus(); return; }
            }
            if (isGoal) {
              const saved = Number(box.querySelector('#smSecond').value) || 0;
              S.goals.push({ name, saved, target: amount, due: box.querySelector('#smDue').value.trim() || '长期' });
            } else {
              S.frozen.push({ name, amount, due: box.querySelector('#smSecond').value.trim() || box.querySelector('#smDue').value.trim() || '待定' });
            }
            close(); renderSavings(); toast(isGoal ? '已新增存钱目标（MOCK）' : '已新增冻结 / 待缴费（MOCK）');
          };
        }
        function openFixedModal() {
          const box = document.createElement('div');
          box.className = 'savings-modal';
          box.innerHTML = '<div class="box"><h3>存入定期</h3>' +
            '<label>本金金额<input id="fxAmount" type="number" step="0.01" placeholder="1000.00"></label>' +
            '<div class="row"><label>期限<select id="fxMonths"><option value="3">3 个月</option><option value="6">6 个月</option><option value="12" selected>12 个月</option><option value="24">24 个月</option><option value="36">36 个月</option></select></label><label>年利率 %<input id="fxRate" type="number" step="0.01" placeholder="1.65"></label></div>' +
            '<div class="row"><label>到期日<input id="fxDue" placeholder="2027-06-01"></label><label>来源账户<select id="fxAccount">' + S.accounts.map(a => '<option>' + esc(a[0]) + '</option>').join('') + '</select></label></div>' +
            '<label class="check"><input type="checkbox" id="fxExisting"> 之前已存入，仅补录（不扣来源账户）</label>' +
            '<div class="form-error" id="fxErr"></div><div class="acts"><button id="fxCancel">取消</button><button class="primary" id="fxSave">确认存入</button></div></div>';
          pageView.appendChild(box);
          const close = () => box.remove();
          box.addEventListener('click', e => { if (e.target === box) close(); });
          box.querySelector('#fxCancel').onclick = close;
          box.querySelector('#fxSave').onclick = () => {
            const amount = validMoney(box.querySelector('#fxAmount').value);
            const rate = Number(box.querySelector('#fxRate').value);
            const err = box.querySelector('#fxErr');
            const months = Number(box.querySelector('#fxMonths').value);
            const due = box.querySelector('#fxDue').value.trim();
            const account = box.querySelector('#fxAccount').value;
            const existing = box.querySelector('#fxExisting').checked;
            if (!amount) { err.textContent = '本金必须大于 0，最多两位小数'; box.querySelector('#fxAmount').focus(); return; }
            if (!existing) {
              const acc = S.accounts.find(a => a[0] === account);
              if (!acc || Number(acc[1] || 0) < amount) { err.textContent = '来源账户余额不足'; box.querySelector('#fxAmount').focus(); return; }
              acc[1] = Number(acc[1] || 0) - amount;
            }
            if (!rate || rate <= 0 || rate > 20) { err.textContent = '年利率必须在 0–20% 之间'; box.querySelector('#fxRate').focus(); return; }
            S.fixed.push({ name: months + ' 个月定期', amount, rate, months, due: due || '待定', account, deducted: !existing });
            close(); renderSavings(); toast('已存入定期（MOCK）');
          };
        }
        document.getElementById('addGoal').onclick = () => openSavingModal('goal');
        pageView.querySelectorAll('[data-pay]').forEach(btn => btn.onclick = () => {
          const i = Number(btn.dataset.pay); const f = S.frozen[i]; if (!f) return;
          const acc = S.accounts[0]; if (acc) acc[1] = Number(acc[1] || 0) - Number(f.amount || 0);
          S.entries.unshift([new Date().toISOString().slice(5, 10), 'expense', acc ? acc[0] : '银行卡', f.name + ' 缴费', -Number(f.amount || 0)]);
          S.expense += Number(f.amount || 0); S.frozen.splice(i, 1); renderSavings(); toast('已标记缴费并解冻（MOCK）');
        });
        pageView.querySelectorAll('[data-del]').forEach(btn => btn.onclick = () => {
          const i = Number(btn.dataset.del); if (!S.frozen[i]) return;
          S.frozen.splice(i, 1); renderSavings(); toast('已删除冻结项（MOCK）');
        });
        pageView.querySelectorAll('[data-cancel]').forEach(btn => btn.onclick = () => {
          const i = Number(btn.dataset.cancel); const f = S.fixed[i]; if (!f) return;
          const acc = S.accounts.find(a => a[0] === (f.account || '银行卡')) || S.accounts[0]; if (acc) acc[1] = Number(acc[1] || 0) + Number(f.amount || 0);
          S.entries.unshift([new Date().toISOString().slice(5, 10), 'income', acc ? acc[0] : '银行卡', f.name + ' 取消转回', Number(f.amount || 0)]);
          S.fixed.splice(i, 1); renderSavings(); toast('已取消定期，本金转回活期（MOCK）');
        });
        function openFundModal() {
          const box = document.createElement('div'); box.className = 'savings-modal';
          box.innerHTML = '<div class="box"><h3>买入理财 / 基金</h3>' +
            '<label>产品名称<input id="fdName" placeholder="余额宝 / 沪深300指数"></label>' +
            '<div class="row"><label>类型<select id="fdType"><option>货币基金</option><option>基金</option></select></label><label>买入金额<input id="fdAmount" type="number" step="0.01" placeholder="500"></label></div>' +
            '<div class="row"><label>来源账户<select id="fdAccount">' + S.accounts.map(a => '<option>' + esc(a[0]) + '</option>').join('') + '</select></label><label>赎回规则<input id="fdRedeem" placeholder="快速赎回 / T+1"></label></div>' +
            '<div class="form-error" id="fdErr"></div><div class="acts"><button id="fdCancel">取消</button><button class="primary" id="fdSave">确认买入</button></div></div>';
          pageView.appendChild(box);
          const close = () => box.remove(); box.addEventListener('click', e => { if (e.target === box) close(); });
          box.querySelector('#fdCancel').onclick = close;
          box.querySelector('#fdSave').onclick = () => {
            const name = box.querySelector('#fdName').value.trim(); const amount = validMoney(box.querySelector('#fdAmount').value);
            const err = box.querySelector('#fdErr');
            if (!name) { err.textContent = '产品名称不能为空'; box.querySelector('#fdName').focus(); return; }
            if (!amount) { err.textContent = '买入金额必须大于 0，最多两位小数'; box.querySelector('#fdAmount').focus(); return; }
            const account = box.querySelector('#fdAccount').value;
            const acc = S.accounts.find(a => a[0] === account);
            if (!acc || Number(acc[1] || 0) < amount) { err.textContent = '来源账户余额不足'; box.querySelector('#fdAmount').focus(); return; }
            acc[1] = Number(acc[1] || 0) - amount;
            S.funds.push({ name, type: box.querySelector('#fdType').value, value: amount, rate: 0, profit: 0, account, redeem: box.querySelector('#fdRedeem').value.trim() || 'T+1' });
            close(); renderSavings(); toast('已买入理财 / 基金（MOCK）');
          };
        }
        document.getElementById('addFixed').onclick = () => openFixedModal();
        document.getElementById('addFund').onclick = () => openFundModal();
        document.getElementById('addFrozen').onclick = () => openSavingModal('frozen');
        document.getElementById('svSave').addEventListener('click', () => {
          const amount = validMoney(document.getElementById('svAmount').value);
          if (!amount) { document.getElementById('svMsg').textContent = '金额必须大于 0，最多两位小数'; return; }
          const kind = document.getElementById('svKind').value;
          const account = document.getElementById('svAccount').value;
          const note = document.getElementById('svNote').value || (kind === 'expense' ? '支出' : kind === 'income' ? '收入' : '存钱');
          const delta = kind === 'expense' ? -amount : amount;
          S.entries.unshift([new Date().toISOString().slice(5, 10), kind, account, note, delta]);
          if (kind === 'expense') S.expense += amount; else if (kind === 'income') S.income += amount;
          const acc = S.accounts.find(a => a[0] === account); if (acc) acc[1] = Number(acc[1] || 0) + delta;
          renderSavings(); toast('已记一笔 · MOCK');
        });
        const csvBtn = document.getElementById('csvPreview'); if (csvBtn) csvBtn.addEventListener('click', () => {
          const f = document.getElementById('csvFile').files[0];
          const msg = document.getElementById('csvMsg');
          if (!f) { msg.textContent = '先选择 CSV 文件'; return; }
          f.text().then(text => {
            const lines = text.split(/\r?\n/).filter(Boolean);
            const rows = lines.slice(1).map(x => x.split(','));
            if (!rows.length) { msg.textContent = 'CSV 没有数据行'; return; }
            msg.textContent = '已读取 ' + rows.length + ' 行，确认导入…';
            rows.forEach(r => {
              const amount = Math.abs(Number((r[2] || '0').replace(/[^\d.-]/g, '')));
              if (!amount) return;
              const kind = (r[1] || 'expense').trim();
              const delta = kind === 'expense' ? -amount : amount;
              S.entries.unshift([(r[3] || '').slice(5, 10) || new Date().toISOString().slice(5, 10), kind, (r[0] || '银行卡').trim(), (r[4] || 'CSV 导入').trim(), delta]);
              if (kind === 'expense') S.expense += amount; else if (kind === 'income') S.income += amount;
            });
            renderSavings(); toast('CSV 已导入 ' + rows.length + ' 行（MOCK）');
          });
        });
      }
      renderSavings();
      [top, msgs, composer, searchBar].forEach(x => x.classList.add('chat-hide'));
      pageView.classList.add('on');
      document.querySelectorAll('.rnav').forEach(x => x.classList.toggle('on', x.dataset.page === name));
      return;
    }
    if (name === 'home') {
      const modules = [
        ['chat','◉','聊天','和 nao 对话，自动加载历史。'],
        ['memory','◈','记忆','记忆本、画像、关系、事件。'],
        ['savings','¥','存钱','总余额、分账户、目标、流水。'],
        ['info','≡','信息','运行状态、日志、计划、阅读。'],
        ['persona','◇','人设','角色卡、预览、激活、导入。'],
        ['settings','⚙','设置','后端地址、连接测试、页面可见性。'],
        ['commands','⌘','命令','全量 51 个命令，按功能分组。'],
        ['cron','◷','定时任务','早报、日记提醒、健康检查。'],
        ['logs','≣','运行日志','命令与任务执行记录。'],
        ['plugins','▣','插件','安装 / 审批 / 权限 / 错误。']
      ];
      pageView.innerHTML = '<div class="page-head"><div><div class="home-head"><h2>主页</h2><span class="home-pill">10 个功能模块</span></div><p>从主页进入聊天、记忆、存钱、信息、人设、设置、命令、定时任务和运行日志。</p></div><button class="back" id="backChat">← 返回聊天</button></div><div class="home-grid">' +
        modules.map(m => '<div class="home-card" data-target="' + m[0] + '"><div class="home-ico">' + m[1] + '</div><h3>' + esc(m[2]) + '</h3><p>' + esc(m[3]) + '</p><div class="st">● 已连接 · MOCK</div></div>').join('') + '</div>';
      [top, msgs, composer, searchBar].forEach(x => x.classList.add('chat-hide'));
      pageView.classList.add('on');
      document.querySelectorAll('.rnav').forEach(x => x.classList.toggle('on', x.dataset.page === name));
      document.getElementById('backChat').addEventListener('click', () => showChat());
      pageView.querySelectorAll('.home-card').forEach(c => c.addEventListener('click', () => {
        const t = c.dataset.target;
        if (t === 'chat') renderChat(document.querySelector('.conv.on')?.dataset.conv || 'nao');
        else showPage(t);
      }));
      return;
    }
    if (name === 'commands') {
      const groups = Object.entries(COMMAND_GROUPS).map(([g, cmds]) =>
        '<div class="cmd-group"><h3>' + esc(g) + '<span>' + cmds.length + '</span></h3><div class="cmd-chips">' +
        cmds.map(c => '<button class="cmd-chip' + (/!(reload|set|exit|quit|clear|say|sayg|backup|plugin|adduser|gw|config|code|apikeys)/.test(c) ? ' owner' : '') + '">' + esc(c) + '</button>').join('') +
        '</div></div>').join('');
      pageView.innerHTML = '<div class="cmd-page"><div class="cmd-catalog"><div class="page-head"><div><h2>命令</h2><p>51 个命令 · MOCK 目录 · v35.14 改为 /api/commands 读取</p></div><button class="back" id="backChat">← 返回聊天</button></div><div class="cmd-runbar"><span class="prompt">&gt;</span><input id="cmdInput" placeholder="输入命令，例如 !persona activate nao"><button id="cmdRun">执行</button></div><div class="cmd-hint" id="cmdHint">无参命令直接执行；带参命令先填参数；二级命令点上方命令后按提示输入。</div><div class="cmd-grid">' + groups + '</div></div><div class="cmd-result"><div class="cmd-result-head"><b>执行结果</b><span class="st" id="cmdState">选择上方命令运行</span></div><div class="cmd-output" id="cmdOutput">点击任意命令，结果显示在这里。\n\n提示：最终版通过 POST /api/command 执行。</div></div></div>';
      [top, msgs, composer, searchBar].forEach(x => x.classList.add('chat-hide'));
      pageView.classList.add('on');
      document.querySelectorAll('.rnav').forEach(x => x.classList.toggle('on', x.dataset.page === name));
      document.getElementById('backChat').addEventListener('click', () => showChat());
      const RESULTS = {
        '!ping': '🏓 Pong！奈绪在线~',
        '!status': '运行中（MOCK）\n主人 QQ：未配置\n记忆：4 条\nschema：35',
        '!help': '命令目录：51 个\n基础 / 记忆 / 媒体 / 日常 / 阅读 / 计划 / 插件 / 账号 / 多端',
        '!memory': '10001：3 条记忆\n10002：1 条记忆',
        '!logs': '09:13 INFO chat len=18\n09:04 WARN search_images timeout',
        '!persona': 'nao · 当前人设\n只读预览 · 仅 owner'
      };
      function runCommand(raw) {
        const output = document.getElementById('cmdOutput');
        const state = document.getElementById('cmdState');
        const hint = document.getElementById('cmdHint');
        const input = document.getElementById('cmdInput');
        if (!output || !input) return;
        const value = String(raw || input.value || '').trim();
        if (!value) { hint.textContent = '先输入命令'; return; }
        const parts = value.split(/\s+/);
        const base = parts[0];
        const meta = COMMAND_META[base];
        state.textContent = '刚刚 · MOCK';
        hint.innerHTML = meta ? '<b>用法</b> ' + esc(meta.usage) : '无参命令可以直接执行';
        if (meta && meta.required && parts.length < 2) {
          output.innerHTML = '<div class="cmdline">&gt; ' + esc(value) + '</div>需要参数：' + esc(meta.args) + '\n用法：' + esc(meta.usage);
          state.textContent = '缺少参数';
          return;
        }
        let result = RESULTS[base] || ('已执行 ' + value + '（MOCK）');
        if (meta && meta.sub && parts[1]) result = '已执行 ' + value + '\n二级命令：' + parts[1] + '（MOCK）';
        output.innerHTML = '<div class="cmdline">&gt; ' + esc(value) + '</div>' + esc(result);
        pageView.querySelectorAll('.cmd-chip').forEach(x => x.classList.toggle('on', x.textContent.replace(' owner', '').trim() === base));
      }
      pageView.querySelectorAll('.cmd-chip').forEach(c => c.addEventListener('click', () => {
        const cmd = c.textContent.replace(' owner', '').trim();
        const input = document.getElementById('cmdInput');
        const meta = COMMAND_META[cmd];
        input.value = cmd + ' ';
        if (meta && (meta.required || meta.sub)) {
          document.getElementById('cmdHint').innerHTML = '<b>需要参数</b> ' + esc(meta.usage) + (meta.sub ? '<br>二级命令：' + esc(meta.sub.join(' / ')) : '');
          input.focus();
          document.getElementById('cmdOutput').innerHTML = '<div class="cmdline">&gt; ' + esc(cmd) + '</div>等待参数…';
          document.getElementById('cmdState').textContent = '等待参数';
        } else {
          runCommand(cmd);
        }
      }));
      document.getElementById('cmdRun').addEventListener('click', () => runCommand(document.getElementById('cmdInput').value));
      document.getElementById('cmdInput').addEventListener('keydown', e => { if (e.key === 'Enter') { e.preventDefault(); runCommand(e.target.value); } });
      return;
    }
    if (name === 'memory') {
      const M = [
        { date: '11-19', target: '10001', text: '今天方案终于过了，客户没有继续改。', tags: ['工作', '情绪'], long: true, src: '对话摘要' },
        { date: '11-19', target: '10001', text: '她不喜欢太吵的地方，偏好安静。', tags: ['偏好'], long: true, src: '对话提取' },
        { date: '11-19', target: '10001', text: '正在读《十日终焉》，喜欢在窗边看书。', tags: ['阅读'], long: false, src: '对话' },
        { date: '11-18', target: '10001', text: '本月结余 ¥3,300，旅行目标 60%。', tags: ['财务'], long: false, src: '财务摘要 · 仅 owner', lock: true },
        { date: '11-18', target: '10001', text: '房租每月 5 日缴，金额 ¥1,800。', tags: ['缴费'], long: true, src: '财务摘要 · 仅 owner', lock: true }
      ];
      pageView.innerHTML = '<div class="page-head"><div><h2>记忆</h2><p>v35.5 Web 演示 · MOCK 数据 · 最近 7 天</p></div><button class="back" id="backChat">← 返回聊天</button></div>' +
        '<div class="mem-stats"><div class="mem-stat"><div class="k">记忆总数</div><div class="v">18</div></div><div class="mem-stat"><div class="k">长期记忆</div><div class="v">4</div></div><div class="mem-stat"><div class="k">事件</div><div class="v">7</div></div><div class="mem-stat"><div class="k">会话</div><div class="v">2</div></div></div>' +
        '<div class="mem-layout"><div class="mem-list">' + M.map(m => '<div class="mem-card"><div class="mem-top"><b>' + esc(m.target) + ' · 记忆</b><span class="mem-date">' + esc(m.date) + '</span></div><div class="mem-text">' + esc(m.text) + '</div><div class="mem-meta">' + m.tags.map(t => '<span class="mem-tag">' + esc(t) + '</span>').join('') + (m.long ? '<span class="mem-tag long">长期</span>' : '') + (m.lock ? '<span class="mem-tag lock">owner</span>' : '') + '<span class="mem-src">来源：' + esc(m.src) + '</span></div></div>').join('') + '</div>' +
        '<div class="mem-side"><div class="mem-panel"><h3>最近事件</h3><div class="mem-event"><i></i><div>方案通过<small>11-19 · 来自聊天</small></div></div><div class="mem-event"><i></i><div>旅行目标 60%<small>11-18 · 财务</small></div></div><div class="mem-event"><i></i><div>读完《十日终焉》第 3 章<small>11-17 · 阅读</small></div></div></div>' +
        '<div class="mem-panel"><h3>画像摘要</h3><div class="mem-profile"><b>偏好</b> 安静、窗边、热饮<br><b>在意</b> 工作反馈、旅行目标<br><b>作息</b> 晚间聊天较多</div></div>' +
        '<div class="mem-panel"><h3>关键词</h3><div class="mem-chips"><span>方案</span><span>旅行</span><span>安静</span><span>十日终焉</span><span>房租</span><span>存钱</span></div></div></div></div>';
      [top, msgs, composer, searchBar].forEach(x => x.classList.add('chat-hide'));
      pageView.classList.add('on');
      document.querySelectorAll('.rnav').forEach(x => x.classList.toggle('on', x.dataset.page === name));
      document.getElementById('backChat').addEventListener('click', () => showChat());
      return;
    }
    if (name === 'relation') {
      pageView.innerHTML = '<div class="page-head"><div><h2>关系</h2><p>v35.5 Web 演示 · MOCK 数据 · 仅 owner 可见</p></div><button class="back" id="backChat">← 返回聊天</button></div>' +
        '<div class="rel-page"><div class="rel-card wide"><div class="rel-k">关系档位</div><div class="rel-tier">熟</div><div class="rel-bar"><i style="width:45%"></i></div><div class="rel-note">算是熟人：可以开玩笑，但别太热络</div></div>' +
        '<div class="rel-card"><div class="rel-k">最近变化</div><div class="rel-v">聊天</div><div class="rel-note">不展示具体增减数值</div></div>' +
        '<div class="rel-card"><div class="rel-k">可见范围</div><div class="rel-v">仅 owner 全量</div><div class="rel-note">普通用户只能查看自己的关系</div></div>' +
        '<div class="rel-card wide"><div class="rel-k">关系事件</div><div class="rel-events"><div class="rel-event"><span>聊天</span><small>2026-11-19 12:00</small></div></div></div></div>';
      [top, msgs, composer, searchBar].forEach(x => x.classList.add('chat-hide'));
      pageView.classList.add('on');
      document.querySelectorAll('.rnav').forEach(x => x.classList.toggle('on', x.dataset.page === name));
      document.getElementById('backChat').addEventListener('click', () => showChat());
      return;
    }
    const rows = PAGES[name] || [];
    pageView.innerHTML = '<div class="page-head"><div><h2>' + esc(TITLES[name] || name) +
      '</h2><p>v35.5 Web 演示 · MOCK 数据</p></div><button class="back" id="backChat">← 返回聊天</button></div>' +
      '<div class="pgrid">' + rows.map(r => '<div class="pcard2"><h3>' + esc(r[0]) + '</h3><p>' + esc(r[1]) + '</p></div>').join('') + '</div>';
    [top, msgs, composer, searchBar].forEach(x => x.classList.add('chat-hide'));
    pageView.classList.add('on');
    document.querySelectorAll('.rnav').forEach(x => x.classList.toggle('on', x.dataset.page === name));
    document.getElementById('backChat').addEventListener('click', () => showChat());
  }

  const railPages = ['home', 'chat', 'memory', 'relation', 'savings', 'weekly', 'info', 'persona', 'commands', 'cron', 'logs', 'diary', 'plugins', 'settings'];
  document.querySelectorAll('.rnav').forEach((b, i) => {
    b.dataset.page = b.dataset.page || railPages[i] || 'chat';
    b.addEventListener('click', () => {
      const p = b.dataset.page;
      if (p === 'chat') { renderChat(document.querySelector('.conv.on')?.dataset.conv || 'nao'); }
      else showPage(p);
    });
  });

  document.querySelectorAll('.q').forEach(q => {
    const text = q.textContent;
    const page = text.includes('存钱') ? 'savings' : text.includes('记忆') ? 'memory' : text.includes('周计划') ? 'weekly' : 'persona';
    q.addEventListener('click', () => showPage(page));
  });

  renderChat('nao');
  updateUnread();
  if (!localStorage.getItem('hsh_web_login') && !location.search.includes('skipLogin')) setTimeout(openLogin, 80);
})();

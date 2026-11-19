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
    weekly: [['第 12 周', '3 门课'], ['周一 1-2 节', '高等数学 · 教三 201'], ['周三 3-4 节', '大学英语 · 文科楼 104'], ['周五 5-6 节', '数据结构 · 实验楼 302']],
    persona: [['当前人设', 'nao · 友利奈绪'], ['风格', '口语 · 简短 · 行动回复'], ['文件', 'prompt / life / supplement / state / voice'], ['状态', '只读预览 · 仅 owner']],
    relation: [['亲密度', '0.62 · 熟'], ['档位', '熟'], ['最近变化', '+0.020 · 聊天'], ['可见范围', '仅 owner 全量；普通用户只看自己']],
    settings: [['后端地址', 'http://127.0.0.1:27004'], ['连接状态', '已连接 · schema 35'], ['主人 QQ', '822891053'], ['视觉', '深色 · 动画默认关闭']],
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

  const TITLES = { home: '主页', memory: '记忆', savings: '存钱', weekly: '周计划表', persona: '人设', relation: '关系', info: '信息', commands: '命令', cron: '定时任务', logs: '运行日志', settings: '设置', plugins: '插件' };

  // 注入演示用样式
  const css = document.createElement('style');
  css.textContent = `
    .chat-hide{display:none!important}
    .page-view{display:none;flex:1;min-height:0;overflow:auto;padding:22px 24px;background:#fff;color:#17263b}
    .page-view.on{display:block}
    .page-head{display:flex;align-items:center;gap:12px;margin-bottom:16px}
    .page-head h2{font-size:17px;margin:0;font-weight:650;color:#17263b}
    .page-head p{font-size:10.5px;color:#6b7c95;margin:3px 0 0}
    .back{margin-left:auto;font-size:10px;color:#2563eb;border:1px solid #dbe8ff;border-radius:8px;padding:5px 9px;background:#fff;cursor:pointer;transition:background .18s}
    .pgrid{display:grid;grid-template-columns:1fr 1fr;gap:10px}
    .pcard2{border:1px solid #e3ebf7;border-radius:12px;background:#fff;padding:12px 13px;transition:border-color .18s,transform .18s,box-shadow .18s}
    .pcard2 h3{font-size:11px;margin:0 0 5px;color:#dbe8fb}
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
    .savings-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:9px;margin-bottom:11px}
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
        '<div class="login-field"><label>主人 QQ</label><input id="loginQQ" value="' + esc(saved.qq || '822891053') + '" placeholder="822891053"></div>' +
        '<div class="login-actions"><button id="loginTest">测试连接</button><button class="primary" id="loginSave">保存并进入</button></div>' +
        '<div class="login-status" id="loginStatus"></div><button class="login-skip" id="loginSkip">稍后配置</button></div>';
      document.body.appendChild(loginMask);
      document.getElementById('loginSkip').addEventListener('click', () => loginMask.classList.remove('on'));
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

  function showPage(name) {
    if (name === 'settings') {
      let saved = {}; try { saved = JSON.parse(localStorage.getItem('hsh_web_login') || '{}'); } catch {}
      pageView.innerHTML = '<div class="page-head"><div><h2>设置</h2><p>v35.5 Web 演示 · 登录 / 后端 / 连接</p></div><button class="back" id="backChat">← 返回聊天</button></div>' +
        '<div class="info-grid"><div class="info-panel"><h3>登录配置</h3><div class="info-row"><span>后端</span><b>' + esc(location.origin === 'null' ? '当前 Web 站点' : location.origin) + ' · 同源</b></div><div class="info-row"><span>token</span><b>' + (saved.token ? '已保存 · 掩码' : '未配置') + '</b></div><div class="info-row"><span>主人 QQ</span><b>' + esc(saved.qq || '822891053') + '</b></div><div class="info-row"><span>操作</span><b><button class="back" id="relogin">登录 / 重新配置</button></b></div></div>' +
        '<div class="info-panel"><h3>连接</h3><div class="info-row"><span>状态</span><b class="ok">已连接 · MOCK</b></div><div class="info-row"><span>schema</span><b>35</b></div><div class="info-row"><span>延迟</span><b>42ms</b></div></div></div>';
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
        document.getElementById('backChat').addEventListener('click', () => showChat());
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
    if (name === 'logs') {
      const LOGS = window.__logs || (window.__logs = [
        ['09:13','INFO','chat','len=18 target=822891053'],
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
        week: 12,
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
        html += '<div class="week-toolbar"><label>周次 <input id="wkNum" type="number" min="1" max="60" value="' + W.week + '"></label><button id="wkGo">跳转</button><button id="wkPeriods">节次设置</button><label class="file-btn">导入 HTML<input id="wkFile" type="file" accept=".html,text/html"></label><span class="week-msg" id="wkMsg">点击空格子新增；点课程编辑/删除</span></div>';
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
          const n = Number(document.getElementById('wkNum').value); if (n >= 1 && n <= 60) { W.week = n; getPeriods(n); renderWeekly(); }
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
      const S = window.__savings || (window.__savings = {
        income: 8000, expense: 3200, saved: 3300, target: 5500,
        accounts: [['银行卡', 3300.00], ['支付宝', 0], ['微信', 0], ['现金', 0]],
        entries: [
          ['11-19', 'expense', '银行卡', '午饭', -35.5],
          ['11-18', 'saving', '银行卡', '旅行目标', 500],
          ['11-17', 'income', '银行卡', '兼职', 800]
        ]
      });
      function money(n){ return '¥' + Number(n || 0).toLocaleString('zh-CN', {minimumFractionDigits: 2, maximumFractionDigits: 2}); }
      function renderSavings() {
        const rows = S.entries.map(e => '<div class="entry"><span class="tag">' + esc(e[1]) + '</span><span>' + esc(e[2]) + ' · ' + esc(e[3]) + '</span><span class="amt ' + (e[4] < 0 ? 'neg' : 'pos') + '">' + (e[4] > 0 ? '+' : '') + money(e[4]) + '</span><span style="color:#9aabbe">' + esc(e[0]) + '</span></div>').join('');
        const total = S.accounts.reduce((n, a) => n + Number(a[1] || 0), 0);
        pageView.innerHTML = '<div class="page-head"><div><h2>存钱</h2><p>v35.5 Web 演示 · MOCK 数据 · 仅主人私聊</p></div><button class="back" id="backChat">← 返回聊天</button></div>' +
          '<div class="savings-grid"><div class="savings-stat"><div class="k">总余额</div><div class="v blue">' + money(total) + '</div></div><div class="savings-stat"><div class="k">本月收入</div><div class="v">' + money(S.income) + '</div></div><div class="savings-stat"><div class="k">本月支出</div><div class="v">' + money(S.expense) + '</div></div><div class="savings-stat"><div class="k">旅行目标</div><div class="v">' + Math.round(S.target ? (S.saved / S.target * 100) : 0) + '%</div></div></div>' +
          '<div class="savings-panel"><h3>记一笔</h3><div class="savings-form"><div><label>金额</label><input id="svAmount" type="number" step="0.01" placeholder="35.50"></div><div><label>账户</label><select id="svAccount">' + S.accounts.map(a => '<option>' + esc(a[0]) + '</option>').join('') + '</select></div><div><label>类型</label><select id="svKind"><option value="expense">支出</option><option value="income">收入</option><option value="saving">存钱</option></select></div><div class="full"><label>备注</label><input id="svNote" placeholder="午饭 / 旅行目标 / 兼职"></div><div class="actions"><button id="svSave">保存</button><label class="ai"><input type="checkbox" id="svAI" checked> AI 可见</label><span class="import-status" id="svMsg"></span></div></div></div>' +
          '<div class="savings-panel"><h3>导入 CSV</h3><div class="import-row"><input id="csvFile" type="file" accept=".csv,text/csv"><button id="csvPreview">预览并导入</button></div><div class="import-status" id="csvMsg">CSV 表头：account,kind,amount,date,note</div></div>' +
          '<div class="savings-panel"><h3>最近流水</h3><div class="entry-list">' + rows + '</div></div>';
        document.getElementById('backChat').addEventListener('click', () => showChat());
        document.getElementById('svSave').addEventListener('click', () => {
          const amount = Number(document.getElementById('svAmount').value);
          if (!amount || amount <= 0) { document.getElementById('svMsg').textContent = '先填正确金额'; return; }
          const kind = document.getElementById('svKind').value;
          const account = document.getElementById('svAccount').value;
          const note = document.getElementById('svNote').value || (kind === 'expense' ? '支出' : kind === 'income' ? '收入' : '存钱');
          const delta = kind === 'expense' ? -amount : amount;
          S.entries.unshift([new Date().toISOString().slice(5, 10), kind, account, note, delta]);
          if (kind === 'expense') S.expense += amount; else if (kind === 'income') S.income += amount;
          const acc = S.accounts.find(a => a[0] === account); if (acc) acc[1] = Number(acc[1] || 0) + delta;
          renderSavings(); toast('已记一笔 · MOCK');
        });
        document.getElementById('csvPreview').addEventListener('click', () => {
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
        '!status': '运行中（MOCK）\n主人 QQ：822891053\n记忆：4 条\nschema：35',
        '!help': '命令目录：51 个\n基础 / 记忆 / 媒体 / 日常 / 阅读 / 计划 / 插件 / 账号 / 多端',
        '!memory': '822891053：3 条记忆\n10001：1 条记忆',
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
    const rows = PAGES[name] || [];
    pageView.innerHTML = '<div class="page-head"><div><h2>' + esc(TITLES[name] || name) +
      '</h2><p>v35.5 Web 演示 · MOCK 数据</p></div><button class="back" id="backChat">← 返回聊天</button></div>' +
      '<div class="pgrid">' + rows.map(r => '<div class="pcard2"><h3>' + esc(r[0]) + '</h3><p>' + esc(r[1]) + '</p></div>').join('') + '</div>';
    [top, msgs, composer, searchBar].forEach(x => x.classList.add('chat-hide'));
    pageView.classList.add('on');
    document.querySelectorAll('.rnav').forEach(x => x.classList.toggle('on', x.dataset.page === name));
    document.getElementById('backChat').addEventListener('click', () => showChat());
  }

  const railPages = ['home', 'chat', 'memory', 'relation', 'savings', 'weekly', 'info', 'persona', 'commands', 'cron', 'logs', 'settings'];
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
  if (!localStorage.getItem('hsh_web_login')) setTimeout(openLogin, 80);
})();

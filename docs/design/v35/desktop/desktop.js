const chats = [
  { id:'nao', name:'友利奈绪', type:'private', sub:'私聊 · 记忆同步', unread:2, avatar:'奈', time:'21:04', last:'今天也一起加油吧', msgs:[
    ['bot','你回来啦。今天外面有点冷，先喝点热的吧。','20:58'],
    ['me','刚到家。今天那个方案终于过了。','21:00'],
    ['bot','那很好啊。你上次说怕过不了，我还记着呢。要不要记进“今天值得高兴的事”？','21:01'],
    ['me','好。顺便帮我看下这个月还剩多少。','21:03'],
    ['bot','本月收入 ¥8,000，支出 ¥3,200，存钱 ¥1,500，结余 ¥3,300。旅行目标已经 60% 了。','21:03']
  ]},
  { id:'g1', name:'测试群 10002', type:'group', sub:'群聊 · 5 人', unread:0, avatar:'测', time:'20:41', last:'群里的大家晚上好。', msgs:[
    ['bot','群里的大家晚上好。','20:30'],
    ['me','晚上好，今天群里安静得有点过分。','20:31']
  ]},
  { id:'g2', name:'星之海学园', type:'group', sub:'群聊 · 12 人', unread:0, avatar:'星', time:'19:58', last:'明天放学后开个短会', msgs:[
    ['bot','明天放学后开个短会，记得带会议记录。','19:58'],
    ['me','收到，会长。','19:59']
  ]}
]
let current = chats[0], filter='all'
const $ = s => document.querySelector(s)
const esc = s => String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))
function toast(text){const t=$('#toast');t.textContent=text;t.classList.add('show');clearTimeout(t._tid);t._tid=setTimeout(()=>t.classList.remove('show'),1600)}
function renderConvs(){
  const list = chats.filter(c=>filter==='all'||c.type===filter)
  $('#convList').innerHTML = list.map(c=>`<button class="conv ${c.id===current.id?'on':''}" data-id="${c.id}">
    <span class="avatar">${esc(c.avatar)}</span><span class="body"><b>${esc(c.name)}</b><small>${esc(c.last)}</small></span><span class="tm">${esc(c.time)}</span>${c.unread?`<span class="un">${c.unread}</span>`:''}
  </button>`).join('')
  const totalUnread = chats.reduce((n, c) => n + Number(c.unread || 0), 0)
  const rail = document.getElementById('railUnread')
  if (rail) { rail.textContent = String(totalUnread); rail.hidden = totalUnread <= 0 }
  document.querySelectorAll('.conv').forEach(el=>el.onclick=()=>{
    current=chats.find(c=>c.id===el.dataset.id); current.unread=0; hidePage(); renderConvs(); renderChat()
  })
}
function renderChat(){
  $('#peerName').textContent=current.name
  $('#peerAvatar').textContent=current.avatar
  $('#peerSub').innerHTML=`${esc(current.sub)} <i class="online-pill">在线</i>`
  $('#messages').innerHTML='<div class="day">今天</div>'+current.msgs.map((m,i)=>{
    const me=m[0]==='me'
    return `<div class="msg ${me?'me':''}" style="animation-delay:${Math.min(i*30,180)}ms"><span class="avatar ${me?'me':''}">${me?'你':esc(current.avatar)}</span><div><div class="bubble">${esc(m[1])}</div><div class="meta">${m[2]} · 已读</div></div></div>`
  }).join('')
  $('#messages').scrollTop=$('#messages').scrollHeight
}
function addMessage(who,text){
  const box=$('#messages'); const me=who==='me'
  const el=document.createElement('div'); el.className='msg '+(me?'me':'')
  el.innerHTML=`<span class="avatar ${me?'me':''}">${me?'你':esc(current.avatar)}</span><div><div class="bubble">${esc(text)}</div><div class="meta">刚刚 · 已读</div></div>`
  box.appendChild(el); box.scrollTop=box.scrollHeight; current.msgs.push([who,text,'刚刚'])
}
function send(){
  const input=$('#input'); const text=input.value.trim(); if(!text)return
  input.value=''; addMessage('me',text); current.last=text; renderConvs()
  const typing=document.createElement('div'); typing.className='msg typing'
  typing.innerHTML=`<span class="avatar">${esc(current.avatar)}</span><div><div class="bubble"><i class="dot"></i><i class="dot"></i><i class="dot"></i></div></div>`
  $('#messages').appendChild(typing); $('#messages').scrollTop=$('#messages').scrollHeight
  setTimeout(()=>{typing.remove(); addMessage('bot',`收到：${text}。${current.type==='group'?'群里我也在听。':'我记着呢。'}`)},900)
}
function setFilter(f){filter=f;document.querySelectorAll('.tabs button').forEach(b=>b.classList.toggle('on',b.dataset.filter===f));renderConvs()}
function showToast(text){toast(text)}
document.querySelectorAll('.tabs button').forEach(b=>b.onclick=()=>setFilter(b.dataset.filter))
$('#sendBtn').onclick=send
$('#input').addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();send()}})
$('#input').addEventListener('input',e=>{e.target.style.height='21px';e.target.style.height=Math.min(80,e.target.scrollHeight)+'px'})
const pageView = $('#pageView')
function hidePage(){pageView.hidden=true;pageView.innerHTML=''}
function showChat(){hidePage()}
function pageHead(title,sub){return `<div class="pv-head"><div><h1>${title}</h1><p>${sub}</p></div></div>`}

const DIARY_API_BASE = (location.hostname === '127.0.0.1' || location.hostname === 'localhost') && location.port === '27005' ? '' : 'http://127.0.0.1:27005'
const DIARY_HEADERS = { Authorization: 'Bearer mock-token' }
let diaryData = []
let diaryMonth = ''
function diaryMonthOf(date){ return String(date || '').slice(0, 7) }
function diaryPreview(text){ const v=String(text||'').replace(/\s+/g,' ').trim(); return v.length>50?v.slice(0,50)+'…':v }
function renderDiaryDesktop(){
  const months=[...new Set(diaryData.map(x=>diaryMonthOf(x.date)))].filter(Boolean).sort().reverse()
  if(!diaryMonth||!months.includes(diaryMonth)) diaryMonth=months[0]||''
  const count=document.getElementById('diaryCount'); if(count) count.textContent=String(diaryData.length)
  const mc=document.getElementById('diaryMonthCount'); if(mc) mc.textContent=String(months.length)
  const last=document.getElementById('diaryLast'); if(last) last.textContent=diaryData.map(x=>x.date).sort().reverse()[0]||'—'
  const dh=document.getElementById('diaryMonths')
  if(dh) dh.innerHTML=months.length?months.map(m=>`<button class="${m===diaryMonth?'on':''}" onclick="selectDiaryMonthDesktop('${m}')">${m.replace('-',' 年 ')} 月</button>`).join(''):'<button>暂无月份</button>'
  const list=document.getElementById('diaryList')
  if(!list) return
  const rows=diaryData.filter(x=>diaryMonthOf(x.date)===diaryMonth).sort((a,b)=>String(b.date).localeCompare(String(a.date)))
  list.innerHTML=rows.length?rows.map(x=>`<div class="pv-row" style="cursor:pointer" onclick="showDiaryDetail(${x.id})"><b style="font-size:10px">${x.title||'无标题'}</b><span>${x.date} · ${x.mood||''} · 查看</span><div style="grid-column:1/-1;font-size:9px;color:#6b7c95;line-height:1.7">${diaryPreview(x.content)}</div></div>`).join(''):'<div class="pv-row">这个月还没有日记<span>—</span></div>'
}
function selectDiaryMonthDesktop(month){ diaryMonth=month; renderDiaryDesktop() }
function showDiaryDetail(id){
  const item=diaryData.find(x=>String(x.id)===String(id)); if(!item) return
  pageView.hidden=false
  pageView.innerHTML=`<div class="pv-head"><div><h1>日记详情</h1><p>${item.date} · ${item.mood||''}</p></div><button class="back" onclick="showPage('diary')">← 返回日记</button></div><div class="pv-card" style="max-width:760px"><b style="font-size:16px">${item.title||'无标题'}</b><small>${item.date} · ${item.source||'!diary'}</small><div style="margin-top:14px;font-size:11px;line-height:1.9;color:#405872;white-space:pre-wrap">${item.content||''}</div></div>`
}
async function loadDiaryPage(){
  try {
    const r=await fetch(DIARY_API_BASE + '/api/diary?all=1', { headers: DIARY_HEADERS }); if(!r.ok) throw new Error('http'); const j=await r.json(); if(!Array.isArray(j.data)) throw new Error('schema')
    diaryData=j.data.length?j.data:[{id:1,date:'2026-11-19',title:'方案通过',content:'今天方案终于过了，客户没有继续改。',mood:'轻松',source:'!diary'}]
  } catch {
    diaryData=[{id:1,date:'2026-11-19',title:'方案通过',content:'今天方案终于过了，客户没有继续改。',mood:'轻松',source:'!diary'},{id:2,date:'2026-10-28',title:'十月小记',content:'降温了，把夏天的衣服收起来，窗边开始有冷风。',mood:'平静',source:'!diary'}]
  }
  renderDiaryDesktop()
}

function showPage(page){
  const pv=pageView; pv.hidden=false
  if(page==='home') pv.innerHTML=pageHead('主页','10 个模块 · 设计稿')+`<div class="pv-grid"><div class="pv-card"><b>已连接</b><small>后端 · schema 36</small></div><div class="pv-card"><b>4</b><small>记忆会话</small></div><div class="pv-card"><b>¥3,300</b><small>本月结余</small></div><div class="pv-card"><b>第 47 周</b><small>周计划</small></div></div><div class="pv-sec">模块</div><div class="pv-chips"><button>聊天</button><button>记忆</button><button>关系</button><button>存钱</button><button>周计划</button><button>信息</button><button>人设</button><button>命令</button><button>定时</button><button>日志</button></div>`
  else if(page==='memory') pv.innerHTML=pageHead('记忆','独立应用客户端 · 来自后端 · 设计稿')+
    `<div class="pv-grid"><div class="pv-card"><b>18</b><small>记忆总数</small></div><div class="pv-card"><b>4</b><small>长期记忆</small></div><div class="pv-card"><b>7</b><small>事件</small></div><div class="pv-card"><b>2</b><small>会话</small></div></div>`+
    `<div class="mem-cols"><div class="mem-list">`+
    [['今天方案终于过了，客户没有继续改。','工作 · 情绪','长期 · 对话摘要'],['她不喜欢太吵的地方，偏好安静。','偏好','长期 · 对话提取'],['正在读《十日终焉》，喜欢在窗边看书。','阅读','对话'],['本月结余 ¥3,300，旅行目标 60%。','财务','owner · 财务摘要'],['房租每月 5 日缴，金额 ¥1,800。','缴费','长期 · 财务摘要']].map((x,i)=>
      `<div class="mem-item"><div class="mem-top"><b>10001 · 记忆</b><span>11-${19-Math.floor(i/2)}</span></div><div class="mem-text">${x[0]}</div><div class="mem-tags"><i>${x[1]}</i><em>${x[2]}</em></div></div>`).join('')+
    `</div><div class="mem-side"><div class="pv-card"><h3>最近事件</h3><div class="pv-row">方案通过<span>11-19</span></div><div class="pv-row">旅行目标 60%<span>11-18</span></div><div class="pv-row">读完《十日终焉》第 3 章<span>11-17</span></div></div>`+
    `<div class="pv-card"><h3>画像摘要</h3><div class="pv-row">偏好<span>安静 / 窗边 / 热饮</span></div><div class="pv-row">在意<span>工作反馈 / 旅行目标</span></div><div class="pv-row">作息<span>晚间聊天较多</span></div></div>`+
    `<div class="pv-card"><h3>关键词</h3><div class="mem-chips"><span>方案</span><span>旅行</span><span>安静</span><span>十日终焉</span><span>房租</span><span>存钱</span></div></div></div></div>`

  else if(page==='relation') pv.innerHTML=pageHead('关系','独立应用客户端 · 仅 owner 可见 · 不显示数值')+
    `<div class="mem-cols"><div><div class="pv-card"><h3>关系档位</h3><b style="font-size:21px;display:block;margin:7px 0 8px;color:var(--blue)">熟</b><div class="track"><i style="width:45%"></i></div><small>算是熟人：可以开玩笑，但别太热络</small></div><div class="pv-card" style="margin-top:10px"><h3>关系事件</h3><div class="pv-row">聊天<span>11-19 12:00</span></div><div class="pv-row">一起看电影<span>11-18</span></div></div></div>`+
    `<div class="mem-side"><div class="pv-card"><h3>最近变化</h3><div class="pv-row">聊天<span>有更新</span></div><div class="pv-row">不展示具体数值<span>owner</span></div></div><div class="pv-card"><h3>可见范围</h3><div class="pv-row">仅 owner 全量</div><div class="pv-row">普通用户<span>只看自己</span></div></div></div></div>`
  else if(page==='savings') pv.innerHTML=pageHead('存钱','独立应用客户端 · 总资产 / 可用 / 冻结 / 定期 / 理财')+`<div class="sav-top"><button id="savQuickEntry">＋ 记一笔</button></div>`+
    `<div class="pv-grid"><div class="pv-card"><b>¥2,700</b><small>可用余额</small></div><div class="pv-card"><b>¥4,100</b><small>冻结 / 预留</small></div><div class="pv-card"><b>¥3,000</b><small>定期存款</small></div><div class="pv-card"><b>¥2,300</b><small>理财 / 基金</small></div><div class="pv-card"><b>¥12,100</b><small>总资产</small></div></div>`+
    `<div class="sav-head"><div class="pv-sec" style="margin:0">存钱目标</div><button class="sav-add" data-sav="goal">＋ 新目标</button></div><div class="sav-goals"><div class="sav-goal"><div class="sav-goal-top"><b>旅行基金</b><small>截止 2027-03</small></div><div class="sav-amt">¥1,800 <small>/ ¥5,000</small></div><div class="sav-bar"><i style="width:36%"></i></div><div class="sav-foot"><span>36%</span><span>还差 ¥3,200</span></div></div><div class="sav-goal"><div class="sav-goal-top"><b>新电脑</b><small>截止 2027-06</small></div><div class="sav-amt">¥900 <small>/ ¥6,000</small></div><div class="sav-bar"><i style="width:15%"></i></div><div class="sav-foot"><span>15%</span><span>还差 ¥5,100</span></div></div><div class="sav-goal"><div class="sav-goal-top"><b>应急金</b><small>截止 长期</small></div><div class="sav-amt">¥1,200 <small>/ ¥10,000</small></div><div class="sav-bar"><i style="width:12%"></i></div><div class="sav-foot"><span>12%</span><span>还差 ¥8,800</span></div></div></div>`+
    `<div class="sav-head"><div class="pv-sec" style="margin:0">定期存款</div><button class="sav-add" data-sav="fixed">＋ 存定期</button></div><div class="sav-list"><div class="sav-row"><div><b>12 个月定期</b><small>年利率 1.65% · 到期 2027-06-01 · 到期回 银行卡 · 补录</small></div><span class="sav-right">¥2,000<button class="sav-act danger" data-sav="cancel">取消</button></span></div><div class="sav-row"><div><b>3 个月定期</b><small>年利率 1.15% · 到期 2027-02-01 · 到期回 支付宝 · 补录</small></div><span class="sav-right">¥1,000<button class="sav-act danger" data-sav="cancel">取消</button></span></div><div class="sav-tip">到期自动按来源账户转回本金+利息，无需手动操作。</div></div>`+
    `<div class="sav-head"><div class="pv-sec" style="margin:0">理财 / 基金</div><button class="sav-add" data-sav="fund">＋ 买入</button></div><div class="sav-list"><div class="sav-row"><div><b>余额宝 <em>货币基金</em></b><small>7 日年化 1.35% · 收益 ¥0.05 · 支付宝 · 快速赎回</small></div><span>¥1,500</span></div><div class="sav-row"><div><b>沪深300指数 <em>基金</em></b><small>收益 ¥50 · 银行卡 · T+1</small></div><span>¥800</span></div></div>`+
    `<div class="mem-cols" style="margin-top:10px"><div class="pv-card"><h3>钱存在哪</h3><div class="pv-row">银行卡<span>¥5,300</span></div><div class="pv-row">支付宝<span>¥1,200</span></div><div class="pv-row">微信<span>¥300</span></div><div class="pv-row">现金<span>¥0</span></div></div><div class="pv-card"><div class="sav-head"><h3>冻结 / 待缴费</h3><button class="sav-add" data-sav="frozen">＋ 新增</button></div><div class="pv-row">房租<span class="sav-right">¥1,800 · 每月 5 日<button class="sav-act" data-sav="pay">已缴费</button><button class="sav-act danger" data-sav="del">删除</button></span></div><div class="pv-row">学费<span class="sav-right">¥2,000 · 2027-02-20<button class="sav-act" data-sav="pay">已缴费</button><button class="sav-act danger" data-sav="del">删除</button></span></div><div class="pv-row">水电费<span class="sav-right">¥300 · 每月 20 日<button class="sav-act" data-sav="pay">已缴费</button><button class="sav-act danger" data-sav="del">删除</button></span></div><div class="sav-tip">可用余额 = 总资产 ¥12,100 - 冻结 ¥4,100 - 定期 ¥3,000 - 理财 ¥2,300 = ¥2,700</div></div></div>`+
    `<div class="mem-cols" style="margin-top:10px"><div class="pv-card"><div class="sav-head"><h3>记一笔</h3></div><div class="entry-form"><label>金额<input id="savAmount" type="number" step="0.01" placeholder="35.50"></label><label>账户<select id="savAccount"><option>银行卡</option><option>支付宝</option><option>微信</option><option>现金</option></select></label><label>类型<select id="savKind"><option value="expense">支出</option><option value="income">收入</option><option value="saving">存钱</option></select></label><label class="full">备注<input id="savNote" placeholder="午饭 / 旅行目标 / 兼职"></label><button id="savEntryBtn">保存</button></div></div><div class="pv-card"><h3>最近流水</h3><div class="pv-row">午饭<span>-¥35.50 · 11-19</span></div><div class="pv-row">旅行目标<span>+¥500 · 11-18</span></div><div class="pv-row">兼职<span>+¥800 · 11-17</span></div></div></div>`
  else if(page==='weekly') {
    const times = ['08:00-08:45','08:55-09:40','10:00-10:45','10:55-11:40','14:00-14:45','14:55-15:40'];
    const days = ['周一','周二','周三','周四','周五','周六','周日'];
    const courses = { 0: { 0: '高等数学|教三 201' }, 2: { 1: '大学英语|文科楼 104' }, 4: { 4: '数据结构|实验楼 302' }, 3: { 4: '读书|30 分钟' } };
    let grid = '<div class="wk-dayhead"><span></span>' + days.map(d => `<span>${d}</span>`).join('') + '</div>';
    for (let r = 0; r < 6; r++) {
      grid += `<div class="wk-row"><div class="wk-period"><b>${r+1}</b><small>${times[r]}</small></div>`;
      for (let c = 0; c < 7; c++) {
        const v = courses[c]?.[r] || '';
        grid += `<div class="wk-cell">${v ? `<div class="wk-course"><b>${v.split('|')[0]}</b><small>${v.split('|')[1]}</small></div>` : ''}</div>`;
      }
      grid += '</div>';
    }
    pv.innerHTML = pageHead('周计划表','独立应用客户端 · ISO 年周 · 按周配置') +
      `<div class="wk-toolbar"><label>周次 <input value="47"></label><button>跳转</button><button>节次设置</button><button>导入 HTML</button><span>点击空格子新增；点课程编辑/删除</span></div>` +
      `<div class="wk-grid">${grid}</div>` +
      `<div class="wk-form"><label>课程名<input id="wkName" placeholder="课程名"></label><label>地点<input id="wkLoc" placeholder="地点"></label><button id="wkAdd">添加到格子</button></div>`;
    pv.querySelectorAll('.wk-cell').forEach(cell => cell.onclick = () => {
      if (cell.querySelector('.wk-course')) return;
      const name = pv.querySelector('#wkName').value.trim(); if (!name) return;
      const loc = pv.querySelector('#wkLoc').value.trim();
      cell.innerHTML = `<div class="wk-course"><b>${name}</b><small>${loc || '未填写地点'}</small></div>`;
    });
    pv.querySelector('#wkAdd').onclick = () => toast('先点上方空格子，再添加课程（设计稿）');
    return;
  }
  else if(page==='info') pv.innerHTML=pageHead('信息','运行 / 数据库 / 计划 / 阅读')+`<div class="pv-row">后端<span>已连接 · 42ms</span></div><div class="pv-row">数据库<span>schema 36 · 正常</span></div><div class="pv-row">今日对话<span>12 次</span></div><div class="pv-row">记忆<span>4 条 / 2 会话</span></div><div class="pv-row">阅读<span>《十日终焉》· 60%</span></div>`
  else if(page==='persona') pv.innerHTML=pageHead('人设','nao · 当前激活')+`<div class="pv-card"><b>nao</b><small>友利奈绪 · 星之海学园</small></div><div class="pv-sec">文件</div><div class="pv-row">prompt.txt<span>已加载</span></div><div class="pv-row">supplement.txt<span>已加载</span></div><div class="pv-row">life.txt<span>已加载</span></div><div class="pv-row">state.json<span>mood 0.1</span></div>`
  else if(page==='commands') pv.innerHTML=pageHead('命令','51 个命令 · 设计稿 · 最终走 /api/commands')+
    `<div class="cmd-run"><span>&gt;</span><input id="cmdInput" placeholder="输入命令，例如 !persona activate nao"><button id="cmdRun">执行</button></div><div class="cmd-hint" id="cmdHint">无参命令直接执行；带参命令先填参数；二级命令点上方命令后按提示输入。</div>`+
    `<div class="cmd-grid">`+
    [['基础',15,['!help','!ping','!status','!version','!uptime','!meta','!usage','!log','!db','!stats','!history','!reload owner','!set owner','!exit owner','!quit owner']],['记忆',8,['!memory','!memorybook','!event','!keywords','!clear owner','!profile','!growth','!relation']],['媒体',8,['!img','!acg','!sticker','!clip','!voice','!vision','!say owner','!sayg owner']],['日常',7,['!diary','!todo','!cron','!hooks','!backup owner','!update','!task']],['阅读',2,['!books','!book']],['计划',1,['!plan']],['插件',1,['!plugin owner']],['账号',2,['!adduser owner','!persona']],['多端',7,['!dding','!resence','!route','!ow owner','!config owner','!code owner','!lanikeys owner']]].map(([g,n,cs])=>
      `<div class="cmd-group"><h3>${g}<span>${n}</span></h3><div class="cmd-chips">${cs.map(c=>`<i class="${c.includes('owner')?'owner':''}">${c}</i>`).join('')}</div></div>`).join('')+
    `</div><div class="cmd-result"><div class="cmd-result-head"><b>执行结果</b><span id="cmdState">选择上方命令运行</span></div><pre id="cmdOutput">点击任意命令，结果显示在这里。\n\n提示：最终版通过 POST /api/command 执行。</pre></div>`

  else if(page==='cron') pv.innerHTML=pageHead('定时任务','列表 / 启停 / 立即运行')+`<div class="pv-row">每日早报 · 08:00<span>启用</span></div><div class="pv-row">日记提醒 · 22:30<span>启用</span></div><div class="pv-row">健康检查 · 每小时<span>停用</span></div>`
else if(page==='diary'){ pv.innerHTML=pageHead('日记','按月查看 · 前 50 字概览 · 点开详情')+`<div class="pv-grid"><div class="pv-card"><b id="diaryCount">—</b><small>全部日记</small></div><div class="pv-card"><b id="diaryMonthCount">—</b><small>月份</small></div><div class="pv-card"><b id="diaryLast">—</b><small>最近</small></div></div><div class="pv-sec">按月份查看</div><div class="pv-chips" id="diaryMonths"><button>加载中…</button></div><div class="pv-sec">本月日记</div><div id="diaryList"><div class="pv-row">正在读取 /api/diary<span>…</span></div></div>`; void loadDiaryPage() }
  else if(page==='plugins') pv.innerHTML=pageHead('插件','安装 / 审批 / 权限 / 错误 · 独立管理页')+`<div class="pv-grid"><div class="pv-card"><b>6</b><small>已安装</small></div><div class="pv-card"><b>1</b><small>待审批</small></div><div class="pv-card"><b>2</b><small>错误</small></div></div><div class="pv-sec">已安装</div><div class="pv-row">天气 · weather<span>启用 · network</span></div><div class="pv-row">读书摘要 · reader<span>启用 · filesystem</span></div><div class="pv-row">音乐 · music<span>停用 · network</span></div><div class="pv-row">面板 · dashboard<span>启用 · read-only</span></div><div class="pv-sec">待审批</div><div class="pv-row">记账助手 · ledger<span>finance · owner</span></div><div class="pv-sec">权限</div><div class="pv-row">network<span>2 个插件</span></div><div class="pv-row">filesystem<span>1 个</span></div><div class="pv-row">finance<span>需 owner</span></div><div class="pv-sec">错误</div><div class="pv-row">music 播放失败<span>20:12</span></div><div class="pv-row">weather 超时<span>18:03</span></div>`
    else if(page==='logs') pv.innerHTML=pageHead('运行日志','最近 3 条 · 设计稿')+`<div class="pv-code">09:13 INFO  chat target=10001 len=18
09:12 INFO  command status
09:04 WARN  search_images upstream timeout</div>`
}
pageView.addEventListener('click', e => {
  if (e.target.closest('#savQuickEntry')) { document.getElementById('savAmount')?.scrollIntoView({behavior:'smooth',block:'center'}); return; }
  if (e.target.closest('#savEntryBtn')) { toast('已记一笔（设计稿）'); return; }
  const sav = e.target.closest('[data-sav]');
  if (sav) {
    const m = { goal: '新增存钱目标', fixed: '存入定期', fund: '买入理财 / 基金', frozen: '新增冻结 / 待缴费', pay: '标记已缴费并解冻', del: '删除冻结项', cancel: '取消定期，本金转回来源账户' };
    toast((m[sav.dataset.sav] || '操作') + '（设计稿）');
  }

  const chip = e.target.closest('.cmd-group .cmd-chips i');
  if (chip) { const inp=document.getElementById('cmdInput'); if(inp)inp.value=chip.textContent; const st=document.getElementById('cmdState'); if(st)st.textContent='已选择 · 点执行'; }
  const run = e.target.closest('#cmdRun');
  if (run) {
    const inp=document.getElementById('cmdInput'); const out=document.getElementById('cmdOutput'); const st=document.getElementById('cmdState');
    const v=(inp?.value||'').trim(); if(!out||!st) return;
    if(!v){st.textContent='先输入命令';return;}
    st.textContent='刚刚 · MOCK';
    out.textContent='> '+v+'\n\n已执行（设计稿）\n最终版通过 POST /api/command 返回真实结果。';
  }
})
document.querySelectorAll('.rnav').forEach(b=>b.onclick=()=>{document.querySelectorAll('.rnav').forEach(x=>x.classList.remove('on'));b.classList.add('on');if(b.dataset.page==='settings'){openSettings()}else if(b.dataset.page==='chat'){showChat()}else{showPage(b.dataset.page)}})
function updateRoutePreview(){const base=$('#routeBase').value.trim().replace(/\/+$/,'');const api=$('#routeApi').value.trim()||'/api';$('#routePreview').textContent=`${base}${api}/status`}
function openSettings(){$('#settingsModal').classList.add('open');updateRoutePreview()}
function closeSettings(){$('#settingsModal').classList.remove('open')}
$('#settingsClose').onclick=closeSettings
$('#settingsModal').addEventListener('click',e=>{if(e.target===$('#settingsModal'))closeSettings()})
$('#routeBase').addEventListener('input',updateRoutePreview)
$('#routeApi').addEventListener('input',updateRoutePreview)
$('#testRoute').onclick=()=>{const st=$('#routeStatus');st.className='route-status';st.textContent='测试中…';setTimeout(()=>{st.className='route-status ok';st.textContent='连接成功 · 42ms · schema 36'},700)}
$('#saveRoute').onclick=()=>{closeSettings();toast('路由已保存到系统安全存储（设计稿）')}
$('#newChat').onclick=()=>toast('新建会话（设计稿）')
$('#searchBtn').onclick=()=>toast('聊天内搜索（设计稿）')
$('#moreBtn').onclick=()=>toast('会话菜单（设计稿）')
document.querySelectorAll('[data-win]').forEach(b=>b.onclick=()=>toast(b.dataset.win==='close'?'关闭到托盘（设计稿）':b.dataset.win==='min'?'最小化（设计稿）':'最大化（设计稿）'))
$('#trayBtn').onclick=()=>{$('#mini').classList.toggle('open');renderMini()}
$('#miniClose').onclick=()=>$('#mini').classList.remove('open')
$('#miniSend').onclick=()=>{const v=$('#miniInput').value.trim();if(!v)return;$('#miniInput').value='';current.msgs.push(['me',v,'刚刚']);renderMini();renderChat()}
$('#miniInput').addEventListener('keydown',e=>{if(e.key==='Enter')$('#miniSend').click()})
function renderMini(){
  $('#miniBody').innerHTML=current.msgs.slice(-4).map(m=>`<div class="b ${m[0]==='me'?'me':''}">${esc(m[1])}</div>`).join('')
  $('#miniBody').scrollTop=$('#miniBody').scrollHeight
}
let updateTimer = null
function openUpdate(){
  const modal = $('#updateModal'); if (!modal) return
  modal.classList.add('open')
  $('#updateSpin').style.display = 'inline-block'; $('#updateNow').disabled = true
  $('#updateTitle').textContent = '正在检查更新…'
  $('#updateVersion').textContent = '当前 v35.6.0'
  $('#updateNotes').textContent = '连接更新服务器，比较版本…'
  $('#updateProgress').style.display = 'none'; $('#updateProgress i').style.width = '0%'
  setTimeout(() => {
    $('#updateSpin').style.display = 'none'
    $('#updateTitle').textContent = '发现新版本 v35.6.1'
    $('#updateVersion').textContent = '当前 v35.6.0 → 最新 v35.6.1'
    $('#updateNotes').textContent = '更新内容：\n· WebView2 固定运行时\n· 显示能力检测 / 兜底页\n· 托盘小窗与路由配置修复\n· 下载完成后重启安装'
    $('#updateNow').disabled = false
    $('#updateNow').textContent = '下载并安装'
  }, 700)
}
function closeUpdate(){ $('#updateModal')?.classList.remove('open'); if(updateTimer){clearInterval(updateTimer);updateTimer=null} }
$('#updateClose').onclick=closeUpdate
$('#updateLater').onclick=closeUpdate
$('#updateModal').addEventListener('click',e=>{if(e.target===$('#updateModal'))closeUpdate()})
$('#updateNow').onclick=()=>{
  const bar=$('#updateProgress'); bar.style.display='block'; $('#updateNow').disabled=true; $('#updateNow').textContent='下载中…'
  let p=0; updateTimer=setInterval(()=>{p=Math.min(100,p+12);bar.querySelector('i').style.width=p+'%';if(p>=100){clearInterval(updateTimer);updateTimer=null;$('#updateTitle').textContent='下载完成，可重启安装';$('#updateNow').textContent='立即重启';$('#updateNow').disabled=false}},160)
}
$('#updateCard').onclick=openUpdate
document.querySelectorAll('.quick button').forEach(b=>b.onclick=()=>toast(`快捷入口：${b.textContent.split('\\n')[0]}`))
setTimeout(()=>{const typing=document.createElement('div');typing.className='msg typing';typing.innerHTML=`<span class="avatar">${esc(current.avatar)}</span><div><div class="bubble"><i class="dot"></i><i class="dot"></i><i class="dot"></i></div></div>`;/* no auto on load */},0)
renderConvs(); renderChat(); renderMini()

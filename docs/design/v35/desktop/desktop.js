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
  { id:'g2', name:'星之海学园', type:'group', sub:'群聊 · 12 人', unread:5, avatar:'星', time:'19:58', last:'明天放学后开个短会', msgs:[
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
  else if(page==='savings') pv.innerHTML=pageHead('存钱','独立应用客户端 · 总资产 / 可用 / 冻结 / 定期 / 理财')+
    `<div class="pv-grid"><div class="pv-card"><b>¥2,700</b><small>可用余额</small></div><div class="pv-card"><b>¥4,100</b><small>冻结 / 预留</small></div><div class="pv-card"><b>¥3,000</b><small>定期存款</small></div><div class="pv-card"><b>¥2,300</b><small>理财 / 基金</small></div><div class="pv-card"><b>¥12,100</b><small>总资产</small></div></div>`+
    `<div class="pv-sec">存钱目标</div><div class="pv-row">旅行基金<span>¥1,800 / ¥5,000 · 36%</span></div><div class="pv-row">新电脑<span>¥900 / ¥6,000 · 15%</span></div><div class="pv-row">应急金<span>¥1,200 / ¥10,000 · 12%</span></div>`+
    `<div class="pv-sec">钱存在哪</div><div class="pv-row">银行卡<span>¥5,300</span></div><div class="pv-row">支付宝<span>¥1,200</span></div><div class="pv-row">微信<span>¥300</span></div>`+
    `<div class="pv-sec">冻结 / 待缴费</div><div class="pv-row">房租<span>¥1,800 · 每月 5 日</span></div><div class="pv-row">学费<span>¥2,000 · 2027-02-20</span></div><div class="pv-row">水电费<span>¥300 · 每月 20 日</span></div>`+
    `<div class="pv-sec">定期存款</div><div class="pv-row">12 个月定期<span>¥2,000 · 1.65% · 到期回银行卡</span></div><div class="pv-row">3 个月定期<span>¥1,000 · 1.15% · 到期回支付宝</span></div>`+
    `<div class="pv-sec">理财 / 基金</div><div class="pv-row">余额宝<span>¥1,500 · 支付宝</span></div><div class="pv-row">沪深300指数<span>¥800 · 银行卡</span></div>`+
    `<div class="pv-sec">最近流水</div><div class="pv-row">午饭<span>-¥35.50</span></div><div class="pv-row">旅行目标<span>+¥500</span></div><div class="pv-row">兼职<span>+¥800</span></div>`
  else if(page==='weekly') pv.innerHTML=pageHead('周计划表','ISO 年周 · 按周配置')+`<div class="pv-sec">第 47 周</div><div class="pv-week"><div class="th"></div><div class="th">周一</div><div class="th">周二</div><div class="th">周三</div><div class="th">周四</div><div class="th">周五</div><div class="th">1-2</div><div class="cell"><b>高等数学</b>教三 201</div><div class="cell"></div><div class="cell"><b>大学英语</b>文科楼 104</div><div class="cell"></div><div class="cell"></div><div class="th">3-4</div><div class="cell"></div><div class="cell"><b>数据结构</b>实验楼 302</div><div class="cell"></div><div class="cell"><b>读书</b>30 分钟</div><div class="cell"></div></div>`
  else if(page==='info') pv.innerHTML=pageHead('信息','运行 / 数据库 / 计划 / 阅读')+`<div class="pv-row">后端<span>已连接 · 42ms</span></div><div class="pv-row">数据库<span>schema 36 · 正常</span></div><div class="pv-row">今日对话<span>12 次</span></div><div class="pv-row">记忆<span>4 条 / 2 会话</span></div><div class="pv-row">阅读<span>《十日终焉》· 60%</span></div>`
  else if(page==='persona') pv.innerHTML=pageHead('人设','nao · 当前激活')+`<div class="pv-card"><b>nao</b><small>友利奈绪 · 星之海学园</small></div><div class="pv-sec">文件</div><div class="pv-row">prompt.txt<span>已加载</span></div><div class="pv-row">supplement.txt<span>已加载</span></div><div class="pv-row">life.txt<span>已加载</span></div><div class="pv-row">state.json<span>mood 0.1</span></div>`
  else if(page==='commands') pv.innerHTML=pageHead('命令','来自 /api/commands · 设计稿')+`<div class="pv-chips"><button>基础</button><button>记忆</button><button>媒体</button><button>日常</button><button>配置</button></div><div class="pv-sec">命令</div><div class="pv-row">!status<span>运行状态</span></div><div class="pv-row">!memory<span>记忆查询</span></div><div class="pv-row">!savings<span>存钱统计</span></div><div class="pv-row">!persona<span>人设管理</span></div>`
  else if(page==='cron') pv.innerHTML=pageHead('定时任务','列表 / 启停 / 立即运行')+`<div class="pv-row">每日早报 · 08:00<span>启用</span></div><div class="pv-row">日记提醒 · 22:30<span>启用</span></div><div class="pv-row">健康检查 · 每小时<span>停用</span></div>`
  else if(page==='logs') pv.innerHTML=pageHead('运行日志','最近 3 条 · 设计稿')+`<div class="pv-code">09:13 INFO  chat target=10001 len=18
09:12 INFO  command status
09:04 WARN  search_images upstream timeout</div>`
}
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
$('#updateCard').onclick=()=>toast('检查更新：v35.6.0（设计稿）')
document.querySelectorAll('.quick button').forEach(b=>b.onclick=()=>toast(`快捷入口：${b.textContent.split('\\n')[0]}`))
setTimeout(()=>{const typing=document.createElement('div');typing.className='msg typing';typing.innerHTML=`<span class="avatar">${esc(current.avatar)}</span><div><div class="bubble"><i class="dot"></i><i class="dot"></i><i class="dot"></i></div></div>`;/* no auto on load */},0)
renderConvs(); renderChat(); renderMini()

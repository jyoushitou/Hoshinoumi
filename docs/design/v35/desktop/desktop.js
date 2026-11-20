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
    current=chats.find(c=>c.id===el.dataset.id); current.unread=0; renderConvs(); renderChat()
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
document.querySelectorAll('.rnav').forEach(b=>b.onclick=()=>{document.querySelectorAll('.rnav').forEach(x=>x.classList.remove('on'));b.classList.add('on');toast(`打开：${b.title}`)})
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

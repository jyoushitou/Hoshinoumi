/**
 * hoshinoumi-dsh — browser half.
 * Adds a compact "nao" entry to the session header and opens the
 * Hoshinoumi interface in a same-origin full-screen iframe.
 */
if (typeof window !== 'undefined' && window.__ModuleLoader__ && !window.__HOSHINOMI_DSH_CLIENT_LOADED__) {
  window.__HOSHINOMI_DSH_CLIENT_LOADED__ = true
  window.__ModuleLoader__.load({
  id: 'hoshinoumi-dsh',
  factory(require) {
    const React = require('react')

    const CSS = `
[data-nao-entry]{display:inline-flex;align-items:center;gap:5px;height:26px;padding:0 9px;border:1px solid var(--dsw-alias-border-l3,var(--dsw-alias-border-l2,rgba(128,128,128,.28)));border-radius:7px;background:transparent;color:var(--dsw-alias-label-secondary);font:inherit;font-size:11px;line-height:1;cursor:pointer;white-space:nowrap}
[data-nao-entry]:hover{background:var(--dsw-alias-interactive-bg-hover,rgba(128,128,128,.12));color:var(--dsw-alias-label-primary)}
[data-nao-entry] i{width:6px;height:6px;border-radius:50%;background:#2fa56b;box-shadow:0 0 0 2px rgba(47,165,107,.14)}
[data-nao-overlay]{position:fixed;inset:0;z-index:2147483000;background:#fbfbf8;display:block;animation:naoFade .15s ease both}
@keyframes naoFade{from{opacity:0}to{opacity:1}}
[data-nao-shell]{width:100vw;height:100vh;background:#fbfbf8;border:0;border-radius:0;overflow:hidden;box-shadow:none;display:flex;flex-direction:column;animation:naoIn .18s ease both}
@keyframes naoIn{from{opacity:0;transform:translateY(8px) scale(.995)}to{opacity:1;transform:none}}
[data-nao-bar]{height:38px;flex:none;background:#f3f3ef;border-bottom:1px solid #e3e3dd;display:flex;align-items:center;gap:9px;padding:0 11px;font-size:11px;color:#74756c}
[data-nao-bar] b{font-weight:700;color:#2d2e28}
[data-nao-close]{margin-left:auto;width:30px;height:30px;border:1px solid #d8d8d2;border-radius:7px;background:#fff;color:#33342e;cursor:pointer;font-size:19px;line-height:1;box-shadow:0 1px 4px rgba(0,0,0,.08)}
[data-nao-close]:hover{background:#e6e6df;color:#2d2e28}
[data-nao-frame]{flex:1;width:100%;border:0;background:#fbfbf8}
`

    function openNao() {
      if (document.querySelector('[data-nao-overlay]')) return
      const overlay = document.createElement('div')
      overlay.setAttribute('data-nao-overlay', '')
      const shell = document.createElement('div')
      shell.setAttribute('data-nao-shell', '')
      const bar = document.createElement('div')
      bar.setAttribute('data-nao-bar', '')
      bar.innerHTML = '<i style="width:7px;height:7px;border-radius:50%;background:#2fa56b;display:inline-block"></i><b>nao</b><span>Hoshinoumi · 本机后端</span>'
      const close = document.createElement('button')
      close.setAttribute('data-nao-close', '')
      close.setAttribute('title', '关闭（Esc）')
      close.textContent = '×'
      const frame = document.createElement('iframe')
      frame.setAttribute('data-nao-frame', '')
      frame.setAttribute('title', 'Hoshinoumi nao')
      frame.src = '/api/hoshinoumi/ui?v=35.2.24&t=' + Date.now()
      const onKey = (e) => { if (e.key === 'Escape') { e.preventDefault(); closeNao() } }
      const onMessage = (e) => { if (e.data && e.data.type === 'hoshinoumi:close') closeNao() }
      const closeNao = () => {
        document.removeEventListener('keydown', onKey, true)
        window.removeEventListener('message', onMessage)
        overlay.remove()
      }
      close.addEventListener('click', closeNao)
      document.addEventListener('keydown', onKey, true)
      window.addEventListener('message', onMessage)
      frame.addEventListener('load', () => {
        try {
          frame.contentWindow.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') { e.preventDefault(); closeNao() }
          })
        } catch {}
      })
      bar.appendChild(close)
      shell.appendChild(bar)
      shell.appendChild(frame)
      overlay.appendChild(shell)
      document.body.appendChild(overlay)
      close.focus()
    }

    function NaoEntry() {
      return React.createElement('button', {
        'data-nao-entry': '',
        type: 'button',
        title: '打开 Hoshinoumi nao',
        onClick: openNao,
      }, React.createElement('i'), 'nao')
    }

    return {
      inject: ['slots'],
      apply(ctx) {
        const style = document.createElement('style')
        style.setAttribute('data-plugin-css', 'hoshinoumi_dsh')
        style.textContent = CSS
        document.head.appendChild(style)
        ctx.effect(() => () => style.remove(), 'hoshinoumi_dsh: styles')
        ctx.slots.inject('conversation.input.right', () => ctx.slots.register(
          { name: 'conversation.input.right', id: 'hoshinoumi-nao-entry', order: 20 },
          NaoEntry,
        ))
      },
    }
  },
})
}

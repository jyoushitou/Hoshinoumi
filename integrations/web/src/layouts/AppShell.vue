<script setup lang="ts">
import RailNav from '@/components/RailNav.vue'
import ConversationList from '@/components/ConversationList.vue'
import ContextPanel from '@/components/ContextPanel.vue'
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useSessionStore } from '@/stores/session'
import { contextHandleTop, contextHidden, railHidden, setContextHandleTop, sideHidden } from '@/composables/useLayoutState'
const auth = useAuthStore(); const session = useSessionStore()
const layoutStyle = computed(() => ({
  '--rail': railHidden.value ? '0px' : '64px',
  '--side': sideHidden.value ? '0px' : '292px',
  '--context': contextHidden.value ? '0px' : '304px',
}))
const draggingEdge = ref(false)
let dragStartY = 0, dragStartTop = 0, dragMoved = false
function startContextDrag(event: PointerEvent) {
  if (event.button !== 0) return
  draggingEdge.value = true; dragMoved = false
  dragStartY = event.clientY; dragStartTop = contextHandleTop.value
  window.addEventListener('pointermove', moveContextDrag)
  window.addEventListener('pointerup', endContextDrag, { once: true })
}
function moveContextDrag(event: PointerEvent) {
  if (!draggingEdge.value) return
  if (Math.abs(event.clientY - dragStartY) > 3) dragMoved = true
  setContextHandleTop(dragStartTop + event.clientY - dragStartY)
}
function endContextDrag() {
  draggingEdge.value = false
  window.removeEventListener('pointermove', moveContextDrag)
}
function onFocus() { if (auth.loggedIn) void session.syncNow(true) }
function onVisibility() { if (document.visibilityState === 'visible' && auth.loggedIn) void session.syncNow() }
onMounted(() => {
  if (auth.loggedIn) { void session.refresh(); session.startSync() }
  else session.error = '未登录，请先填写 QQ 和 token'
  window.addEventListener('focus', onFocus)
  document.addEventListener('visibilitychange', onVisibility)
})
onBeforeUnmount(() => {
  window.removeEventListener('focus', onFocus)
  document.removeEventListener('visibilitychange', onVisibility)
  window.removeEventListener('pointermove', moveContextDrag)
  session.stopSync()
})
</script>
<template>
  <div
    class="shell"
    :class="{ 'rail-hidden': railHidden, 'left-hidden': sideHidden, 'right-hidden': contextHidden }"
    :style="layoutStyle"
  >
    <RailNav />
    <ConversationList />
    <main class="main">
      <RouterView />
    </main>
    <ContextPanel />
    <button
      v-if="contextHidden"
      class="edge-handle right-edge"
      :class="{ dragging: draggingEdge }"
      :style="{ top: contextHandleTop + 'px' }"
      type="button"
      title="展开右侧栏，可上下拖动"
      @pointerdown.prevent="startContextDrag"
      @click="!dragMoved && (contextHidden = false)"
    >‹</button>
  </div>
</template>
<style scoped>
.shell{position:relative;display:grid;grid-template-columns:var(--rail,64px) var(--side,292px) minmax(0,1fr) var(--context,304px);height:100vh;height:100dvh;overflow:hidden;min-height:0;transition:grid-template-columns .24s cubic-bezier(.22,1,.36,1)}
.main{min-width:0;min-height:0;height:100%;display:flex;flex-direction:column;background:#fff;overflow:hidden}
.shell :deep(.rail),.shell :deep(.side),.shell :deep(.context){transition:opacity .2s,transform .28s,visibility 0s}
.shell.rail-hidden :deep(.rail){opacity:0;pointer-events:none;overflow:hidden;min-width:0;transform:translateX(-8px);visibility:hidden;transition:opacity .2s,transform .28s,visibility 0s .28s}
.shell.left-hidden :deep(.side){opacity:0;pointer-events:none;overflow:hidden;min-width:0;transform:translateX(-8px);visibility:hidden;transition:opacity .2s,transform .28s,visibility 0s .28s}
.shell.right-hidden :deep(.context){opacity:0;pointer-events:none;overflow:hidden;min-width:0;transform:translateX(8px);visibility:hidden;transition:opacity .2s,transform .28s,visibility 0s .28s}
.edge-handle{position:fixed;top:52px;z-index:30;width:26px;height:56px;border:1px solid #c7dcff;background:#eef4ff;color:#2563eb;font:16px inherit;font-weight:700;cursor:grab;align-items:center;justify-content:center;padding:0;box-shadow:0 4px 12px rgba(37,99,235,.12);display:flex}
.edge-handle.right-edge{right:0;border-right:0;border-radius:8px 0 0 8px;touch-action:none;user-select:none}
.edge-handle.dragging{background:#dbeafe;cursor:grabbing}
@media(max-width:1180px){.shell{grid-template-columns:var(--rail,64px) var(--side,292px) minmax(0,1fr)!important}:deep(.context){display:none}.edge-handle{display:none}}
@media(max-width:820px){.shell{grid-template-columns:54px minmax(0,1fr)}:deep(.side){display:none}}
</style>

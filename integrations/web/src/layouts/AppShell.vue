<script setup lang="ts">
import RailNav from '@/components/RailNav.vue'
import ConversationList from '@/components/ConversationList.vue'
import ContextPanel from '@/components/ContextPanel.vue'
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { contextHandleY, contextHidden, railHidden, setContextHandleY, sideHidden } from '@/composables/useLayoutState'
import { useAuthStore } from '@/stores/auth'
import { useSessionStore } from '@/stores/session'
const auth = useAuthStore(); const session = useSessionStore()
const layoutStyle = computed(() => ({
  '--rail': railHidden.value ? '0px' : '64px',
  '--side': sideHidden.value ? '0px' : '292px',
  '--context': contextHidden.value ? '0px' : '304px',
}))
const draggingEdge = ref(false)
let dragStartY = 0, dragStartPercent = 0, dragMoved = false
function startContextDrag(event: PointerEvent) {
  draggingEdge.value = true; dragMoved = false
  dragStartY = event.clientY; dragStartPercent = contextHandleY.value
  window.addEventListener('pointermove', moveContextDrag)
  window.addEventListener('pointerup', endContextDrag, { once: true })
}
function moveContextDrag(event: PointerEvent) {
  if (!draggingEdge.value) return
  const delta = ((event.clientY - dragStartY) / Math.max(1, window.innerHeight)) * 100
  if (Math.abs(event.clientY - dragStartY) > 3) dragMoved = true
  setContextHandleY(dragStartPercent + delta)
}
function endContextDrag() {
  draggingEdge.value = false
  window.removeEventListener('pointermove', moveContextDrag)
  if (!dragMoved) contextHidden.value = !contextHidden.value
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
  session.stopSync()
})
</script>
<template>
  <div class="shell" :style="layoutStyle">
    <RailNav v-show="!railHidden" />
    <ConversationList v-show="!sideHidden" />
    <main class="main">
      <RouterView />
    </main>
    <ContextPanel v-show="!contextHidden" />
    <button v-if="railHidden" class="edge rail-edge" type="button" title="展开导航" @click="railHidden = false">»</button>
    <button v-if="sideHidden" class="edge side-edge" type="button" title="展开会话列表" @click="sideHidden = false">☰</button>
    <button class="context-edge" :class="{ dragging: draggingEdge }" :style="{ top: contextHandleY + '%' }" type="button" :title="contextHidden ? '展开上下文' : '收起上下文'" @pointerdown.prevent="startContextDrag">{{ contextHidden ? '‹' : '›' }}</button>
  </div>
</template>
<style scoped>
.shell{position:relative;display:grid;grid-template-columns:var(--rail,64px) var(--side,292px) minmax(0,1fr) var(--context,304px);height:100vh;height:100dvh;overflow:hidden;min-height:0;transition:grid-template-columns .22s ease}.edge{position:fixed;z-index:40;border:1px solid #dbe8ff;background:#fff;color:#2563eb;box-shadow:0 4px 14px rgba(37,99,235,.12);cursor:pointer}.rail-edge{left:8px;top:50%;width:24px;height:42px;border-radius:10px;font:12px inherit}.side-edge{left:12px;bottom:16px;width:38px;height:32px;border-radius:9px;font:14px inherit}.context-edge{position:fixed;right:0;z-index:45;width:14px;height:54px;transform:translateY(-50%);border:1px solid #dbe8ff;border-right:0;border-radius:9px 0 0 9px;background:#fff;color:#526982;font:12px inherit;cursor:ns-resize;box-shadow:-2px 0 10px rgba(24,58,110,.08);touch-action:none}.context-edge:hover,.context-edge.dragging{background:#eef4ff;color:#2563eb}
.main{min-width:0;min-height:0;height:100%;display:flex;flex-direction:column;background:#fff;overflow:hidden}
@media(max-width:1180px){.shell{grid-template-columns:var(--rail,64px) var(--side,292px) minmax(0,1fr)!important}:deep(.context){display:none}.context-edge{display:none}}
@media(max-width:820px){.shell{grid-template-columns:54px minmax(0,1fr)}:deep(.side){display:none}}
</style>

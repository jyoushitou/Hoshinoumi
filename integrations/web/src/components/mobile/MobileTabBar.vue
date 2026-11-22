<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useMobileNav } from '@/composables/useMobileNav'
import { useSessionStore } from '@/stores/session'
import { useIsOwner } from '@/composables/useIsOwner'

const route = useRoute()
const router = useRouter()
const { entries, quickEntries } = useMobileNav()
const session = useSessionStore()
const isOwner = useIsOwner()
const visibleEntries = computed(() => isOwner.value ? entries : entries.filter(entry => entry.key !== 'relation'))
const visibleQuick = computed(() => {
  const list = quickEntries.value.filter(entry => isOwner.value || entry.key !== 'relation')
  return list.length ? list : visibleEntries.value.slice(0, 1)
})
const expanded = ref(false)
const activePath = computed(() => route.path)

watch(() => route.path, () => { expanded.value = false })

function go(path: string) {
  expanded.value = false
  if (route.path !== path) void router.push(path)
}
</script>

<template>
  <nav class="mobile-tabbar" :class="{ expanded }">
    <button
      class="tab-grip"
      type="button"
      :aria-expanded="expanded"
      aria-label="展开或收起全部入口"
      @click="expanded = !expanded"
    >
      <span class="grip-icon">⌃</span>
    </button>

    <div class="quick-row" :style="{ gridTemplateColumns: `repeat(${visibleQuick.length}, 1fr)` }">
      <button
        v-for="entry in visibleQuick"
        :key="entry.key"
        class="tab-item"
        :class="{ on: activePath === entry.path }"
        type="button"
        @click="go(entry.path)"
      >
        <span class="tab-icon">{{ entry.icon }}</span>
        <span class="tab-label">{{ entry.label }}</span>
        <span v-if="entry.key === 'chats' && session.unread > 0" class="tab-unread">{{ session.unread > 99 ? '99+' : session.unread }}</span>
      </button>
    </div>

    <div v-if="expanded" class="all-grid">
      <button
        v-for="entry in visibleEntries"
        :key="entry.key"
        class="all-item"
        :class="{ on: activePath === entry.path }"
        type="button"
        :title="entry.label"
        :aria-label="entry.label"
        @click="go(entry.path)"
      >
        {{ entry.icon }}
        <span v-if="entry.key === 'chats' && session.unread > 0" class="all-unread">{{ session.unread > 99 ? '99+' : session.unread }}</span>
      </button>
    </div>
  </nav>
</template>

<style scoped>
.mobile-tabbar{
  position:relative;flex:none;display:flex;flex-direction:column;align-items:stretch;
  background:#fff;border-top:1px solid #e3ebf7;padding:0 6px max(6px, env(safe-area-inset-bottom));min-height:70px;
  transition:height .18s ease;height:70px;overflow:visible;z-index:30;
}
.mobile-tabbar.expanded{height:auto}
.tab-grip{
  position:absolute;left:50%;top:-14px;transform:translateX(-50%);
  width:38px;height:22px;border:1px solid #dbe8ff;border-radius:12px;background:#fff;
  color:#2563eb;display:grid;place-items:center;cursor:pointer;z-index:2;
  box-shadow:0 4px 10px rgba(37,99,235,.10);
}
.grip-icon{font-size:9px;line-height:1;transition:transform .18s}
.mobile-tabbar.expanded .grip-icon{transform:rotate(180deg)}
.quick-row{display:grid;height:54px;align-items:stretch}
.tab-item{
  border:0;background:transparent;color:#8a9bb0;display:flex;flex-direction:column;
  align-items:center;justify-content:center;gap:2px;min-width:0;border-radius:10px;cursor:pointer;
}
.tab-item{position:relative}
.tab-item.on{color:#2563eb;background:#eef4ff;font-weight:700}
.tab-unread{position:absolute;top:3px;right:calc(50% - 22px);min-width:14px;height:14px;padding:0 3px;border-radius:7px;background:#ef4444;color:#fff;font-size:7px;font-weight:800;display:grid;place-items:center}
.tab-icon{font-size:15px;line-height:1}
.tab-label{font-size:8px;line-height:1.2;white-space:nowrap}
.all-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:5px;padding:4px 4px 2px;border-top:1px solid #eef3fb}
.all-item{
  height:44px;border:1px solid #e1ebf9;background:#f8fbff;border-radius:9px;
  color:#687f9b;font-size:16px;display:grid;place-items:center;cursor:pointer;
}
.all-item{position:relative}
.all-item.on{color:#2563eb;background:#eef4ff;border-color:#bcd4ff}
.all-unread{position:absolute;top:4px;right:6px;min-width:12px;height:12px;border-radius:6px;background:#ef4444;color:#fff;font-size:6px;font-weight:800;display:grid;place-items:center;padding:0 2px}
</style>

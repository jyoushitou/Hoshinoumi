<script setup lang="ts">
import { computed, ref } from 'vue'
const props = defineProps<{ qq?: string | number; group?: string | number; name?: string; size?: number }>()
const failed = ref(false)
const src = computed(() => {
  const group = String(props.group || '').trim()
  const qq = String(props.qq || '').trim()
  if (group) return `https://p.qlogo.cn/gh/${encodeURIComponent(group)}/${encodeURIComponent(group)}/100`
  if (qq && qq !== '0') return `https://q1.qlogo.cn/g?b=qq&nk=${encodeURIComponent(qq)}&s=100`
  return ''
})
const initial = computed(() => String(props.name || props.qq || '?').trim().slice(0, 1) || '?')
const altText = computed(() => String(props.name || props.qq || 'avatar'))
</script>
<template>
  <span class="qq-avatar"><img v-if="src && !failed" :src="src" :alt="altText" referrerpolicy="no-referrer" @error="failed = true"><b v-else>{{ initial }}</b></span>
</template>
<style scoped>
.qq-avatar{display:grid;place-items:center;overflow:hidden;background:#dbeafe;color:#1d4ed8;flex:none;border-radius:inherit}.qq-avatar img{width:100%;height:100%;object-fit:cover;display:block}.qq-avatar b{font-size:inherit;font-weight:700}
</style>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import AppShell from '@/layouts/AppShell.vue'
import MobileShell from '@/layouts/MobileShell.vue'
import LoginModal from '@/components/LoginModal.vue'
import { useAuthStore } from '@/stores/auth'
const auth = useAuthStore()
const isMobile = ref(false)
let media: MediaQueryList | null = null
let viewportRaf = 0
function syncViewport() {
  cancelAnimationFrame(viewportRaf)
  viewportRaf = requestAnimationFrame(() => {
    document.documentElement.style.setProperty('--app-height', `${window.innerHeight}px`)
    document.documentElement.classList.toggle('device-mobile', window.innerWidth <= 820)
    document.documentElement.classList.toggle('device-tablet', window.innerWidth > 820 && window.innerWidth <= 1180)
  })
}
const MOBILE_QUERY = '(max-width: 820px)'
function forcedLayout() {
  if (typeof window === 'undefined') return ''
  return new URLSearchParams(window.location.search).get('layout') || ''
}
function sync(event?: MediaQueryListEvent) {
  const forced = forcedLayout()
  if (forced === 'mobile') { isMobile.value = true; return }
  if (forced === 'desktop') { isMobile.value = false; return }
  isMobile.value = event ? event.matches : (media?.matches ?? false)
}
onMounted(() => {
  media = window.matchMedia(MOBILE_QUERY)
  sync(); syncViewport()
  media.addEventListener('change', sync)
  window.addEventListener('resize', syncViewport, { passive: true })
  window.addEventListener('orientationchange', syncViewport, { passive: true })
  void auth.validate()
})
onBeforeUnmount(() => {
  media?.removeEventListener('change', sync)
  window.removeEventListener('resize', syncViewport)
  window.removeEventListener('orientationchange', syncViewport)
  cancelAnimationFrame(viewportRaf)
})
</script>
<template>
  <LoginModal v-if="!auth.loggedIn" />
  <MobileShell v-if="isMobile" />
  <AppShell v-else />
</template>

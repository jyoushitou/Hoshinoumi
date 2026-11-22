<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import AppShell from '@/layouts/AppShell.vue'
import MobileShell from '@/layouts/MobileShell.vue'
import LoginModal from '@/components/LoginModal.vue'
import { useAuthStore } from '@/stores/auth'
const auth = useAuthStore()
const isMobile = ref(false)
let media: MediaQueryList | null = null
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
  sync()
  media.addEventListener('change', sync)
  void auth.validate()
})
onBeforeUnmount(() => { media?.removeEventListener('change', sync) })
</script>
<template>
  <LoginModal v-if="!auth.loggedIn && !auth.guest" />
  <MobileShell v-if="isMobile" />
  <AppShell v-else />
</template>

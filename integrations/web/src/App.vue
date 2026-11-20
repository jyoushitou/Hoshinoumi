<script setup lang="ts">
import { onMounted } from 'vue'
import AppShell from '@/layouts/AppShell.vue'
import LoginModal from '@/components/LoginModal.vue'
import { useAuthStore } from '@/stores/auth'
const auth = useAuthStore()
onMounted(() => { void auth.validate() })
</script>
<template><LoginModal v-if="!auth.loggedIn && !auth.guest" /><AppShell /></template>

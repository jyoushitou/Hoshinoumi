<script setup lang="ts">
import AppShell from '@/layouts/AppShell.vue'
import LoginModal from '@/components/LoginModal.vue'
import { useAuthStore } from '@/stores/auth'
const auth = useAuthStore()
</script>
<template><LoginModal v-if="!auth.loggedIn && !auth.guest" /><AppShell /></template>

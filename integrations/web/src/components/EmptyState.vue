<script setup lang="ts">
defineProps<{ text: string }>()
</script>
<template><div class="empty">{{ text }}</div></template>
<style scoped>.empty{padding:18px 12px;font-size:10px;color:#8a9bb0;text-align:center;border:1px dashed #dbe8ff;border-radius:9px;background:#f8fbff}</style>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const title = computed(() => String(route.meta.title ?? '页面'))
const desc = computed(() => String(route.meta.desc ?? '移动端页面框架'))
const sections = computed(() => {
  const map: Record<string, Array<[string, string]>> = {
    home: [['聊天', '会话与消息'], ['记忆', '记忆本 / 事件'], ['关系', '档位 / 变化'], ['存钱', '账户 / 目标'], ['周计划', '节次 / 时间'], ['信息', '运行 / 数据库'], ['人设', '导入 / 激活'], ['命令', '命令 / 参数'], ['定时任务', '新增 / 启停'], ['运行日志', '筛选 / 搜索']],
    memory: [['记忆本', '按主题浏览'], ['最近事件', '本周'], ['她的画像', '偏好 / 习惯'], ['关系记忆', '一起经历过']],
    relation: [['关系档位', '只显示档位，不显示具体数值'], ['最近变化', '相处与共同经历'], ['可见范围', '仅主人可见']],
    savings: [['账户', '仅主人可见'], ['目标', '进度'], ['定期', '记录'], ['基金', '记录']],
    weekly: [['本周计划', '节次与时间'], ['完成状态', '点击切换'], ['提醒', '定时任务']],
    info: [['运行状态', '连接 / 版本'], ['数据库', 'schema'], ['日志', '最近运行'], ['阅读', '小说 / 信息']],
    persona: [['当前人设', '激活状态'], ['导入', '角色卡'], ['导出', '备份']],
    commands: [['命令列表', '51 个命令'], ['参数', '二级命令'], ['执行', '主人权限']],
    cron: [['任务列表', '启停 / 执行'], ['新增任务', '时间 / 触发']],
    logs: [['运行日志', '一行一条'], ['筛选', 'INFO / WARN / ERROR']],
  }
  return map[String(route.name)] ?? [['页面框架', '移动端布局已接入']]
})
</script>

<template>
  <section class="mobile-page">
    <div class="head"><h1>{{ title }}</h1><p>{{ desc }}</p></div>
    <div class="hint">移动端页面框架已接入；真实数据和业务交互按 v35.7 补丁逐步接入。</div>
    <div class="grid">
      <div v-for="[name, note] in sections" :key="name" class="card">
        <b>{{ name }}</b><span>{{ note }}</span>
      </div>
    </div>
  </section>
</template>

<style scoped>
.mobile-page{padding:16px 14px 18px;background:#f7faff;min-height:100%}
.head h1{margin:0;font-size:24px;letter-spacing:-.03em;line-height:1.15}.head p{margin:4px 0 0;color:#8a9bb0;font-size:10px}
.hint{margin:12px 0 14px;border:1px dashed #d7e6ff;background:#f4f9ff;color:#7890aa;border-radius:11px;padding:10px 11px;font-size:9.5px;line-height:1.7}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:8px}
.card{background:#fff;border:1px solid #e3ebf7;border-radius:12px;padding:12px;display:flex;flex-direction:column;gap:5px}
.card b{font-size:11px;color:#314a65}.card span{font-size:8.5px;color:#9aabc0;line-height:1.5}
</style>

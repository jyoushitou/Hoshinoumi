import { createRouter, createWebHashHistory, createWebHistory } from 'vue-router'
import ChatView from '@/views/ChatView.vue'
import PageView from '@/views/PageView.vue'
import RelationView from '@/views/RelationView.vue'
import MemoryView from '@/views/MemoryView.vue'
import SavingsView from '@/views/SavingsView.vue'
import DiaryView from '@/views/DiaryView.vue'
import InfoView from '@/views/InfoView.vue'
import PersonaView from '@/views/PersonaView.vue'
import HealthView from '@/views/HealthView.vue'
import WeeklyView from '@/views/WeeklyView.vue'
import CronView from '@/views/CronView.vue'
import LogsView from '@/views/LogsView.vue'
import SettingsView from '@/views/SettingsView.vue'
import PluginsView from '@/views/PluginsView.vue'
import { useAuthStore } from '@/stores/auth'
import { useSessionStore } from '@/stores/session'
import MobilePermissionsView from '@/views/mobile/MobilePermissionsView.vue'
import CommandView from '@/views/CommandView.vue'
const meta = (title: string, desc: string) => ({ title, desc })
const router = createRouter({
  history: typeof window !== 'undefined' && window.location.protocol === 'file:' ? createWebHashHistory() : createWebHistory(),
  routes: [
    { path: '/', redirect: '/chat' },
    { path: '/chat', name: 'chat', component: ChatView },
    { path: '/home', name: 'home', component: PageView, meta: meta('主页', '10 个功能模块入口') },
    { path: '/memory', name: 'memory', component: MemoryView, meta: meta('记忆', '记忆本 / 事件 / 画像 / 关系') },
    { path: '/relation', name: 'relation', component: RelationView, meta: meta('关系', '档位 / 最近变化 / 可见范围') },
    { path: '/savings', name: 'savings', component: SavingsView, meta: { ...meta('存钱', '总余额 / 账户 / 记一笔 / CSV 导入'), ownerOnly: true } },
    { path: '/weekly', name: 'weekly', component: WeeklyView, meta: meta('周计划表', '按周配置节次与时间') },
    { path: '/info', name: 'info', component: InfoView, meta: meta('信息', '运行 / 配置 / 备份 / 账号 / 阅读 / 网关') },
    { path: '/health', name: 'health', component: HealthView, meta: meta('健康 / 热量', '摄入 / 目标 / 运动 / 体重') },
    { path: '/persona', name: 'persona', component: PersonaView, meta: meta('人设', '导入 / 导出 / 激活') },
    { path: '/commands', name: 'commands', component: CommandView, meta: meta('命令', '51 个命令 / 参数 / 二级命令') },
    { path: '/cron', name: 'cron', component: CronView, meta: meta('定时任务', '新增 / 编辑 / 启停 / 删除') },
    { path: '/diary', name: 'diary', component: DiaryView, meta: meta('日记', '按月 / 前 50 字概览 / 详情') },
    { path: '/logs', name: 'logs', component: LogsView, meta: meta('运行日志', '一行一条 / 筛选 / 搜索') },
    { path: '/plugins', name: 'plugins', component: PluginsView, meta: meta('插件', '安装 / 审批 / 权限 / 错误') },
    { path: '/settings', name: 'settings', component: SettingsView, meta: meta('设置', '登录 / 后端 / 连接 / 可见性') },
    { path: '/settings/permissions', name: 'permissions', component: MobilePermissionsView, meta: meta('权限与后台', '权限 / 自启动 / 电池') },
  ],
})
router.beforeEach((to) => {
  if (!to.meta.ownerOnly) return true
  const auth = useAuthStore()
  const session = useSessionStore()
  if (!auth.loggedIn) return '/chat'
  if (session.status && String(auth.qq).trim() !== String(session.status.master_qq || '').trim()) return '/chat'
  return true
})
export default router

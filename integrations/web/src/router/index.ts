import { createRouter, createWebHashHistory, createWebHistory } from 'vue-router'
import ChatView from '@/views/ChatView.vue'
import PageView from '@/views/PageView.vue'
import RelationView from '@/views/RelationView.vue'
const meta = (title: string, desc: string) => ({ title, desc })
const router = createRouter({
  history: typeof window !== 'undefined' && window.location.protocol === 'file:' ? createWebHashHistory() : createWebHistory(),
  routes: [
    { path: '/', redirect: '/chat' },
    { path: '/chat', name: 'chat', component: ChatView },
    { path: '/home', name: 'home', component: PageView, meta: meta('主页', '10 个功能模块入口') },
    { path: '/memory', name: 'memory', component: PageView, meta: meta('记忆', '记忆本 / 事件 / 画像 / 关系') },
    { path: '/relation', name: 'relation', component: RelationView, meta: meta('关系', '档位 / 最近变化 / 可见范围') },
    { path: '/savings', name: 'savings', component: PageView, meta: meta('存钱', '总余额 / 账户 / 记一笔 / CSV 导入') },
    { path: '/weekly', name: 'weekly', component: PageView, meta: meta('周计划表', '按周配置节次与时间') },
    { path: '/info', name: 'info', component: PageView, meta: meta('信息', '运行 / 数据库 / 日志 / 计划 / 阅读') },
    { path: '/persona', name: 'persona', component: PageView, meta: meta('人设', '导入 / 导出 / 激活') },
    { path: '/commands', name: 'commands', component: PageView, meta: meta('命令', '51 个命令 / 参数 / 二级命令') },
    { path: '/cron', name: 'cron', component: PageView, meta: meta('定时任务', '新增 / 编辑 / 启停 / 删除') },
    { path: '/logs', name: 'logs', component: PageView, meta: meta('运行日志', '一行一条 / 筛选 / 搜索') },
    { path: '/settings', name: 'settings', component: PageView, meta: meta('设置', '登录 / 后端 / 连接') },
  ],
})
export default router

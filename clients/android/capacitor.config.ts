import type { CapacitorConfig } from '@capacitor/cli'

const config: CapacitorConfig = {
  appId: 'com.hoshinoumi.mobile',
  appName: 'Hoshinoumi',
  webDir: 'www',
  server: {
    // 用户可配置任意后端 URL；允许 WebView 内导航，不跳到 Chrome
    allowNavigation: ['*'],
    // 主框架加载失败时回本地配置/登录页，不留在 Chrome 错误页
    errorPath: 'index.html?error=1',
  },
  plugins: {
    Keyboard: {
      resize: 'body',
      resizeOnFullScreen: true,
    },
  },
}

export default config

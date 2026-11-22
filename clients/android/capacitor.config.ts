import type { CapacitorConfig } from '@capacitor/cli'

const config: CapacitorConfig = {
  appId: 'com.hoshinoumi.mobile',
  appName: 'Hoshinoumi',
  webDir: 'www',
  server: {
    // 用户可配置任意后端 URL；允许 WebView 内导航，不跳到 Chrome
    allowNavigation: ['*'],
  },
}

export default config

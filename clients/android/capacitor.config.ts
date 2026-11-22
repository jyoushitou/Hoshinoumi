import type { CapacitorConfig } from '@capacitor/cli'

const config: CapacitorConfig = {
  appId: 'com.hoshinoumi.mobile',
  appName: 'Hoshinoumi',
  webDir: 'www',
  server: {
    // 开发期：Android 模拟器通过 10.0.2.2 访问电脑上的 Vite。
    // 真机请改成电脑局域网 IP；生产改成正式 https 地址。
    url: 'http://10.0.2.2:27006',
    cleartext: true,
  },
}

export default config

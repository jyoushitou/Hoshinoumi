import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import App from '@/App.vue'
import router from '@/router'
describe('App', () => {
  it('renders shell', async () => {
    const wrapper = mount(App, { global: { plugins: [createPinia(), router] } })
    expect(wrapper.text()).toContain('HOSHINOUMI')
  })
})

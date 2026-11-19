import { test, expect } from '@playwright/test'
test('shell loads', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByText('Hoshinoumi')).toBeVisible()
})

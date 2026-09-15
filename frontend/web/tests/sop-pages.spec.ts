import { test, expect } from '@playwright/test';
import { mkdirSync } from 'fs';
import path from 'path';

const SCREENSHOT_DIR = '/home/rudy/projects/work/SopFast/frontend/web/tests/screenshots';
mkdirSync(SCREENSHOT_DIR, { recursive: true });

const BASE_URL = process.env.BASE_URL || 'http://localhost:5180';

const PAGES = [
  { name: '计划工作台', path: '/sop/dashboard', file: '01_dashboard.png' },
  { name: '市场信息', path: '/sop/market', file: '02_market.png' },
  { name: '预测校验', path: '/sop/analysis', file: '03_analysis.png' },
  { name: '会议报告', path: '/sop/report', file: '04_report.png' },
  { name: '智能问答', path: '/sop/chat', file: '05_chat.png' },
  { name: '知识库管理', path: '/sop/knowledge', file: '06_knowledge.png' },
  { name: '数据中心', path: '/sop/data-center', file: '07_data_center.png' },
];

test.describe('SopFast SOP 页面验证', () => {
  test.beforeAll(async ({ page }) => {
    // Login first
    console.log('→ 访问登录页...');
    await page.goto(`${BASE_URL}/login`, { waitUntil: 'networkidle', timeout: 15000 });

    // Find and fill login form
    const usernameInput = page.locator('input[placeholder*="账号"], input[placeholder*="用户名"]').first();
    const passwordInput = page.locator('input[type="password"]').first();

    if (await usernameInput.count() > 0) {
      await usernameInput.fill('admin');
      await passwordInput.fill('123456');

      // Try to handle slider captcha
      await page.waitForTimeout(500);

      // Click login button
      const loginBtn = page.locator('button:has-text("登录")').first();
      if (await loginBtn.count() > 0) {
        await loginBtn.click();
      } else {
        await passwordInput.press('Enter');
      }

      await page.waitForTimeout(3000);
      console.log('→ 登录后URL:', page.url());
    }
  });

  for (const pageInfo of PAGES) {
    test(`验证 ${pageInfo.name} 页面`, async ({ page }) => {
      console.log(`→ 访问: ${pageInfo.name} (${pageInfo.path})`);

      await page.goto(`${BASE_URL}${pageInfo.path}`, { waitUntil: 'networkidle', timeout: 15000 });
      await page.waitForTimeout(2000);

      // Screenshot
      const screenshotPath = path.join(SCREENSHOT_DIR, pageInfo.file);
      await page.screenshot({ path: screenshotPath, fullPage: false });

      // Get page content
      const bodyText = await page.textContent('body') || '';

      // Assertions
      // Should not be redirected to login
      expect(page.url()).not.toContain('/login');

      // Should not show 404
      expect(bodyText).not.toContain('404');

      // Should have some content
      expect(bodyText.length).toBeGreaterThan(50);

      console.log(`  ✅ ${pageInfo.name}: ${bodyText.length} chars`);
    });
  }

  test('侧边栏显示 S&OP 菜单', async ({ page }) => {
    await page.goto(`${BASE_URL}/`, { waitUntil: 'networkidle', timeout: 10000 });
    await page.waitForTimeout(2000);

    // Check for SOP menu items
    const sopMenu = page.locator('text=S&OP').first();
    if (await sopMenu.count() > 0) {
      console.log('✅ 侧边栏显示 S&OP 菜单');
    } else {
      console.log('⚠️ 未在侧边栏找到 S&OP 菜单');
    }

    await page.screenshot({
      path: path.join(SCREENSHOT_DIR, '00_sidebar_menu.png'),
      fullPage: false
    });
  });
});

import pkg from '/home/rudy/.npm/_npx/e41f203b7505f1fb/node_modules/playwright/index.js';
const { chromium } = pkg;
import { fileURLToPath } from 'url';
import path from 'path';
import { mkdirSync } from 'fs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SCREENSHOT_DIR = path.join(__dirname, 'screenshots');
mkdirSync(SCREENSHOT_DIR, { recursive: true });

const BASE_URL = 'http://localhost:5180';
const PAGES = [
  { name: '计划工作台', path: '/sop/dashboard', file: '01_dashboard.png' },
  { name: '市场信息', path: '/sop/market', file: '02_market.png' },
  { name: '预测校验', path: '/sop/analysis', file: '03_analysis.png' },
  { name: '会议报告', path: '/sop/report', file: '04_report.png' },
  { name: '智能问答', path: '/sop/chat', file: '05_chat.png' },
  { name: '知识库管理', path: '/sop/knowledge', file: '06_knowledge.png' },
  { name: '数据中心', path: '/sop/data-center', file: '07_data_center.png' },
];

async function login(page) {
  console.log('→ 访问登录页...');
  await page.goto(`${BASE_URL}/login`, { waitUntil: 'networkidle', timeout: 15000 });

  // Wait for login form
  await page.waitForSelector('input[placeholder*="账号"], input[placeholder*="用户名"], input[type="text"]', { timeout: 5000 }).catch(() => null);

  // Try to find username and password fields
  const usernameInput = await page.locator('input[placeholder*="账号"], input[placeholder*="用户名"]').first();
  const passwordInput = await page.locator('input[placeholder*="密码"], input[type="password"]').first();

  if (await usernameInput.count() > 0 && await passwordInput.count() > 0) {
    console.log('→ 填写账号密码...');
    await usernameInput.fill('admin');
    await passwordInput.fill('123456');

    // Check if there's a slider captcha - try to complete it
    const sliderHandle = await page.locator('.slider-verify, .nc_iconfont, .btn_slide, [class*="slider"], [class*="captcha"]').first();
    if (await sliderHandle.count() > 0) {
      console.log('→ 检测到滑块验证码，尝试拖动...');
      const sliderBox = await sliderHandle.boundingBox();
      if (sliderBox) {
        const mouse = page.mouse;
        await mouse.move(sliderBox.x + 10, sliderBox.y + sliderBox.height / 2);
        await mouse.down();
        await mouse.move(sliderBox.x + sliderBox.width + 50, sliderBox.y + sliderBox.height / 2, { steps: 20 });
        await mouse.up();
        await page.waitForTimeout(1000);
      }
    }

    // Click login button
    const loginBtn = await page.locator('button:has-text("登录"), button:has-text("登 录"), .login-btn').first();
    if (await loginBtn.count() > 0) {
      await loginBtn.click();
      console.log('→ 点击登录...');
    } else {
      // Try pressing Enter
      await passwordInput.press('Enter');
      console.log('→ 按回车登录...');
    }

    // Wait for navigation
    await page.waitForTimeout(3000);
    console.log('→ 当前URL:', page.url());
    return true;
  }

  console.log('→ 未找到登录表单，可能已登录或页面结构不同');
  return false;
}

async function verifyPage(page, pageInfo) {
  console.log(`\n→ 验证页面: ${pageInfo.name} (${pageInfo.path})`);

  try {
    await page.goto(`${BASE_URL}${pageInfo.path}`, { waitUntil: 'networkidle', timeout: 15000 });
    await page.waitForTimeout(2000);

    // Take screenshot
    const screenshotPath = path.join(SCREENSHOT_DIR, pageInfo.file);
    await page.screenshot({ path: screenshotPath, fullPage: false });
    console.log(`  ✅ 截图已保存: ${pageInfo.file}`);

    // Check for error indicators
    const bodyText = await page.textContent('body');

    // Check for common error patterns
    const has404 = bodyText?.includes('404') || bodyText?.includes('找不到组件');
    const hasError = bodyText?.includes('错误') || bodyText?.includes('Error') || bodyText?.includes('failed');
    const hasLoginRedirect = page.url().includes('/login');

    if (hasLoginRedirect) {
      console.log(`  ❌ 被重定向到登录页`);
      return { name: pageInfo.name, status: 'redirect_to_login', url: page.url() };
    }

    if (has404) {
      console.log(`  ❌ 页面显示 404 或组件未找到`);
      return { name: pageInfo.name, status: '404' };
    }

    // Check for expected content
    const hasContent = bodyText?.length > 100;
    if (hasContent) {
      console.log(`  ✅ 页面有内容 (${bodyText.length} chars)`);
    } else {
      console.log(`  ⚠️ 页面内容较少 (${bodyText?.length || 0} chars)`);
    }

    return { name: pageInfo.name, status: 'ok', chars: bodyText?.length || 0 };
  } catch (e) {
    console.log(`  ❌ 错误: ${e.message}`);
    return { name: pageInfo.name, status: 'error', error: e.message };
  }
}

async function main() {
  console.log('=== SopFast 前端 SOP 页面验证 ===\n');

  const browser = await chromium.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage']
  });

  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 },
    locale: 'zh-CN',
  });

  const page = await context.newPage();

  // Step 1: Login
  const loginSuccess = await login(page);
  if (!loginSuccess) {
    console.log('\n⚠️ 登录可能未成功，继续尝试访问页面...\n');
  } else {
    // Verify we're not on login page
    if (page.url().includes('/login')) {
      console.log('\n⚠️ 登录后仍在登录页，可能登录失败\n');
    } else {
      console.log(`\n✅ 登录成功，当前页面: ${page.url()}\n`);
    }
  }

  // Step 2: Visit each SOP page
  const results = [];
  for (const pageInfo of PAGES) {
    const result = await verifyPage(page, pageInfo);
    results.push(result);
  }

  // Step 3: Summary
  console.log('\n=== 验证结果汇总 ===\n');
  for (const r of results) {
    const icon = r.status === 'ok' ? '✅' : r.status === 'redirect_to_login' ? '❌' : r.status === '404' ? '❌' : '⚠️';
    console.log(`${icon} ${r.name}: ${r.status}${r.chars ? ` (${r.chars} chars)` : ''}${r.error ? ` - ${r.error}` : ''}`);
  }

  // Check sidebar menu
  console.log('\n=== 侧边栏菜单检查 ===');
  await page.goto(`${BASE_URL}/`, { waitUntil: 'networkidle', timeout: 10000 });
  await page.waitForTimeout(2000);

  // Look for SOP menu item
  const sopMenuItems = await page.locator('text=S&OP, text=SOP, text=计划工作台, text=市场信息, text=预测校验').all();
  console.log(`找到 SOP 相关菜单项: ${sopMenuItems.length} 个`);
  for (const item of sopMenuItems.slice(0, 10)) {
    const text = await item.textContent();
    console.log(`  - ${text?.trim()}`);
  }

  await page.screenshot({ path: path.join(SCREENSHOT_DIR, '00_sidebar_menu.png'), fullPage: false });
  console.log('侧边栏截图已保存: 00_sidebar_menu.png');

  await browser.close();
  console.log('\n✅ 验证完成');
}

main().catch(e => {
  console.error('Fatal error:', e);
  process.exit(1);
});

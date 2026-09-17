import json
import time

from playwright.sync_api import sync_playwright


API_BASE = "http://127.0.0.1:8001/api/v1"
WEB_BASE = "http://127.0.0.1:5180/web"


def login_as_user(playwright):
    request = playwright.request.new_context(base_url=API_BASE)
    captcha = request.get("/system/auth/captcha/get").json()["data"]
    captcha_key = captcha["key"]
    if captcha.get("enable"):
        time.sleep(0.35)
        completed = request.post(
            "/system/auth/captcha/slider/complete",
            data={"captcha_key": captcha_key},
        )
        assert completed.ok, completed.text()

    response = request.post(
        "/system/auth/login",
        form={
            "username": "user",
            "password": "123456",
            "captcha_key": captcha_key,
            "login_type": "PC端",
        },
    )
    assert response.ok, response.text()
    payload = response.json()["data"]
    return request, payload["access_token"], payload["refresh_token"]


with sync_playwright() as playwright:
    api, access_token, refresh_token = login_as_user(playwright)
    auth_headers = {"Authorization": f"Bearer {access_token}"}
    forbidden = api.post("/sop/report/snapshots/generate", headers=auth_headers, data={})
    assert forbidden.status == 403, forbidden.text()

    browser = playwright.chromium.launch(
        headless=True,
        executable_path="/tmp/chrome-with-local-libs",
    )
    context = browser.new_context(viewport={"width": 1440, "height": 1000})
    page = context.new_page()
    browser_errors = []
    requested_urls = []
    page.on("pageerror", lambda error: browser_errors.append(str(error)))
    page.on("request", lambda request: requested_urls.append(request.url))
    page.add_init_script(
        """
        sessionStorage.setItem('access_token', %s);
        sessionStorage.setItem('refresh_token', %s);
        localStorage.setItem('remember_me', 'false');
        """
        % (json.dumps(access_token), json.dumps(refresh_token))
    )

    page.goto(f"{WEB_BASE}/#/sop-analysis/meeting-report")
    page.wait_for_load_state("networkidle")
    page.locator(".sop-report-root").wait_for()
    page.locator(".sop-report-paper h1").wait_for()
    assert "S&OP 需求走势与分渠道提报预测报告" in page.locator(
        ".sop-report-paper h1"
    ).inner_text()
    assert page.get_by_role("button", name="生成快照").count() == 0
    page.screenshot(
        path="dogfood-output/screenshots/fixed-user-report-permission.png",
        full_page=True,
    )

    before_memory = len(requested_urls)
    page.goto(f"{WEB_BASE}/#/ai-assistant/memory")
    page.wait_for_load_state("networkidle")
    page.get_by_role("heading", name="会话记录").wait_for()
    page.get_by_text("查看 S&OP 智能问答产生的历史会话与消息").wait_for()
    memory_requests = requested_urls[before_memory:]
    assert any("/api/v1/sop/chat/sessions" in url for url in memory_requests)
    assert not any("/api/v1/ai/chat/list" in url for url in memory_requests)
    page.screenshot(
        path="dogfood-output/screenshots/fixed-user-memory.png",
        full_page=True,
    )

    page.route("**/api/v1/sop/chat/stream", lambda route: route.abort("failed"))
    page.goto(f"{WEB_BASE}/#/ai-assistant/chat")
    page.wait_for_load_state("networkidle")
    composer = page.locator("textarea")
    composer.fill("验证网络失败后输入框恢复")
    page.locator(".send-btn").click()
    page.locator(".el-message--error").wait_for()
    assert composer.is_enabled()
    composer.fill("可以继续输入")
    assert page.locator(".send-btn").is_enabled()
    page.screenshot(
        path="dogfood-output/screenshots/fixed-user-chat-recovery.png",
        full_page=True,
    )

    assert not browser_errors, browser_errors
    print(
        json.dumps(
            {
                "snapshot_generate_status": forbidden.status,
                "report_generate_button_count": 0,
                "memory_uses_sop_sessions": True,
                "chat_composer_recovered": True,
                "page_errors": browser_errors,
            },
            ensure_ascii=False,
        )
    )
    browser.close()
    api.dispose()

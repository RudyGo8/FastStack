/**
 * 路由不变量守卫
 *
 * 全局只有一层页面级 KeepAlive（见 layouts/fa-page-content/index.vue），它成立的前提是
 * Vue Router 的「深度跳级」：RouterView 会跳过没有 component 的中间层记录，直接渲染
 * matched 中第一个带 components 的后代（即真实叶子页面）。
 *
 * 这条机制唯一的硬前提：**目录（有 children 的记录）不能挂组件**。
 * 历史上给目录挂过 NestedRouterParent 壳组件（已删除），跳级因此失效，出口渲染的是壳
 * 组件、叶子被嵌套重复挂载，表现为每次切换菜单都重复请求接口。此文件把该前提固化为断言，
 * 防止回归；运行时的兜底自检见 route-loader.ts 的 warnInvalidRouteConfig 与
 * fa-page-content/index.vue 的 dev 告警。
 */

import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { describe, it, expect, vi } from "vitest";

// ────────────── 隔离应用模块图 ──────────────
// `router/routes.ts` 直接 import 了各视图与 Layout，这些 .vue 依赖构建期的自动导入
// （unplugin-auto-import / unplugin-vue-components），单测环境无法求值。本用例只校验
// 路由记录的**结构**，故把视图全部替换为桩，避免拉起整条组件依赖链。
vi.mock("@/layouts/index.vue", () => ({ default: { name: "AppLayout" } }));
vi.mock("@views/dashboard/home/index.vue", () => ({ default: { name: "DashboardHome" } }));
vi.mock("@views/redirect/index.vue", () => ({ default: { name: "RedirectView" } }));
vi.mock("@views/module_system/auth/login/index.vue", () => ({ default: { name: "LoginView" } }));
vi.mock("@views/exception/401/index.vue", () => ({ default: { name: "Exception401" } }));
vi.mock("@views/exception/403/index.vue", () => ({ default: { name: "Exception403" } }));
vi.mock("@views/exception/404/index.vue", () => ({ default: { name: "Exception404" } }));
vi.mock("@views/exception/500/index.vue", () => ({ default: { name: "Exception500" } }));
vi.mock("@views/fastlink/current/profile.vue", () => ({ default: { name: "FastlinkProfile" } }));

type AnyRoute = {
  path?: string;
  name?: unknown;
  component?: unknown;
  children?: AnyRoute[];
  meta?: Record<string, any>;
};

/** 菜单类型：1 = CATALOG（目录），3 = BUTTON（按钮权限，`MenuProcessor.mapMenuNode` 会过滤掉） */
const MENU_TYPE_CATALOG = 1;
const MENU_TYPE_BUTTON = 3;

function flatten(routes: readonly AnyRoute[]): AnyRoute[] {
  return routes.flatMap((route) => [route, ...flatten(route.children ?? [])]);
}

function findByName(routes: readonly AnyRoute[], name: string): AnyRoute | undefined {
  for (const route of routes) {
    if (route.name === name) return route;
    const hit = findByName(route.children ?? [], name);
    if (hit) return hit;
  }
  return undefined;
}

// ══════════════════ 静态路由 ══════════════════
describe("静态路由 — 中间层不挂组件（深度跳级的前提）", () => {
  it("根 Layout 的子孙里，有 children 的记录 component 必须为 undefined", async () => {
    const { staticRoutes, ROOT_LAYOUT_ROUTE_NAME } = await import("@/router/routes");
    const root = findByName(staticRoutes as AnyRoute[], ROOT_LAYOUT_ROUTE_NAME);
    expect(root, `未找到根 Layout 路由 "${ROOT_LAYOUT_ROUTE_NAME}"`).toBeDefined();
    // depth 0 的壳必须挂 Layout，否则 App.vue 的 RouterView 无处渲染
    expect(root!.component, "根 Layout 缺少 component").toBeTruthy();

    for (const route of flatten(root!.children ?? [])) {
      if (route.children?.length) {
        expect(route.component, `目录 "${route.path}" 不应挂组件（会使深度跳级失效）`).toBeUndefined();
      }
    }
  });

  it("fastlink 多级目录保持无组件（历史壳组件的回归锚点）", async () => {
    const { staticRoutes } = await import("@/router/routes");
    for (const name of ["Fastlink"]) {
      const route = findByName(staticRoutes as AnyRoute[], name);
      expect(route, `未找到目录 "${name}"`).toBeDefined();
      expect(route!.children?.length, `"${name}" 应仍有子路由`).toBeGreaterThan(0);
      expect(route!.component, `目录 "${name}" 不应挂组件`).toBeUndefined();
    }
  });

  it("根 Layout 的子孙里，叶子记录必须能渲染出内容", async () => {
    const { staticRoutes, ROOT_LAYOUT_ROUTE_NAME } = await import("@/router/routes");
    const root = findByName(staticRoutes as AnyRoute[], ROOT_LAYOUT_ROUTE_NAME)!;
    for (const route of flatten(root!.children ?? [])) {
      if (route.children?.length) continue;
      const renderable = Boolean(route.component || route.meta?.link || route.meta?.isIframe);
      expect(renderable, `叶子 "${route.path}" 缺少 component / link / iframe`).toBe(true);
    }
  });

  it("depth 0 的壳路由：有 children 就必须挂组件（否则页面没有渲染出口）", async () => {
    const { staticRoutes } = await import("@/router/routes");
    for (const route of staticRoutes as AnyRoute[]) {
      if (route.children?.length) {
        expect(route.component, `壳路由 "${route.path}" 缺少 Layout 组件`).toBeTruthy();
      }
    }
  });
});

// ══════════════════ 后端菜单数据 ══════════════════
// `vitest` 下 `import.meta.url` 不可用于定位文件（fileURLToPath 会抛 scheme 错误），
// 因此以运行目录（frontend/web）为基准向上找仓库根下的数据文件。
const MENU_FIXTURE = [
  path.resolve(process.cwd(), "../../backend/sql/sys_menu.json"),
  path.resolve(process.cwd(), "../backend/sql/sys_menu.json"),
  path.resolve(process.cwd(), "backend/sql/sys_menu.json"),
].find((candidate) => existsSync(candidate));

describe("后端菜单数据 — 目录不挂组件", () => {
  it("找到菜单数据文件", () => {
    expect(MENU_FIXTURE, `未找到 backend/sql/sys_menu.json（基准目录 ${process.cwd()}）`).toBeTruthy();
  });

  it("目录节点（type=CATALOG）不得配 component_path", () => {
    const menus = JSON.parse(readFileSync(MENU_FIXTURE!, "utf-8")) as any[];
    const walk = (items: any[], trail: string[]): void => {
      for (const item of items) {
        const fullPath = [...trail, String(item.route_path ?? "")].join("/");
        if (item.type === MENU_TYPE_CATALOG) {
          expect(
            (item.component_path ?? "").trim(),
            `目录 "${fullPath}" 配了 component_path，会被当成目录挂组件（MenuProcessor.mapMenuNode 会忽略它）`
          ).toBe("");
        }
        walk((item.children ?? []) as any[], [...trail, String(item.route_path ?? "")]);
      }
    };
    walk(menus, []);
  });

  it("有子菜单的节点不得配 component_path（带子级即退化为目录）", () => {
    const menus = JSON.parse(readFileSync(MENU_FIXTURE!, "utf-8")) as any[];
    const walk = (items: any[], trail: string[]): void => {
      for (const item of items) {
        const fullPath = [...trail, String(item.route_path ?? "")].join("/");
        // 按钮权限不算子菜单：MenuProcessor.mapMenuNode 会把它过滤掉
        const subMenus = (item.children ?? []).filter((c: any) => c.type !== MENU_TYPE_BUTTON);
        if (subMenus.length) {
          expect(
            (item.component_path ?? "").trim(),
            `菜单 "${fullPath}" 有子菜单又配了 component_path，会被当成目录挂组件`
          ).toBe("");
        }
        walk((item.children ?? []) as any[], [...trail, String(item.route_path ?? "")]);
      }
    };
    walk(menus, []);
  });
});

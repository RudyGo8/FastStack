<!-- 布局内容 -->
<template>
  <div id="app-scroll-main" class="layout-content" :style="containerStyle">
    <div id="app-content-header">
      <!-- 节日滚动 -->
      <FaFestivalTextScroll />

      <!-- 路由信息调试 -->
      <div
        v-if="isOpenRouteInfo === 'true'"
        class="px-2 py-1.5 mb-3 text-sm text-g-500 bg-g-200 border border-(--default-border) rounded-md"
      >
        router meta：{{ route.meta }}
      </div>
    </div>

    <RouterView v-if="isRefresh" v-slot="{ Component, route: router }" :style="contentStyle">
      <Transition :name="actualTransition" mode="out-in">
        <div v-if="Component" class="route-view-shell flex min-h-0 min-w-0 w-full flex-1 flex-col">
          <!--
            单层缓存「叶子页面组件」：目录路由不挂组件，RouterView 的深度跳级让本出口
            直接渲染 matched 中第一个带 components 的后代（即真实页面）。
            此处 KeepAlive 必须常驻，不能按当前路由 meta.keepAlive 做 v-if 开关：
            卸载 KeepAlive 会连同已缓存实例一起销毁，导致每次切回都重新挂载（接口重复请求）。
            叶子的取舍由 include/exclude 表达（include 只在多标签模式下生效）。
            不要加 `:max`：缓存集合已由 include/exclude 精确表达，再叠一层 LRU 会在标签
            仍打开时悄悄挤掉最早的页面，切回时无谓重挂载，请求次数变得不可预测。
          -->
          <KeepAlive :include="keepAliveInclude" :exclude="keepAliveExclude">
            <component
              class="fa-page-view min-h-0 min-w-0 w-full flex-1"
              :is="Component"
              :key="routeViewCacheKey(router)"
            />
          </KeepAlive>
        </div>
      </Transition>
    </RouterView>

    <!-- 返回顶部：宽屏滚动容器是 #app-content；窄屏改为文档滚动，target 置空 -->
    <ElBacktop
      :key="backtopTargetKey"
      :target="backtopScrollTarget"
      :right="28"
      :bottom="28"
      class="z-90"
    >
      <FaSvgIcon icon="ri:arrow-up-circle-line" class="text-2xl text-theme" />
    </ElBacktop>
  </div>
</template>
<script setup lang="ts">
/**
 * 布局滚动容器 + 业务路由出口；与 settings.refresh 联动可整体重建 RouterView。
 *
 * 缓存为单层：目录路由不挂组件，RouterView 深度跳级后本出口直接渲染叶子页面，
 * 因此这里的 KeepAlive 就是全局唯一的页面级缓存，不存在壳实例放大问题。
 * 缓存开关数据源：后端菜单 `keep_alive` → MenuProcessor 写入 `meta.keepAlive`；工作栏 tab 随路由写入同一 meta。
 * include / exclude 均用 `!== false`，与静态路由里显式 `keepAlive: false`、后端布尔字段对齐。
 */
import type { CSSProperties } from "vue";
import { useMediaQuery } from "@vueuse/core";
import { useRoute, useRouter, type RouteLocationNormalizedLoaded } from "vue-router";
import { useSettingsStore, useWorktabStore } from "@stores";

defineOptions({ name: "FaPageContent" });

/**
 * KeepAlive 缓存键（本出口渲染的是叶子页面组件）。
 *
 * 用叶子路由 path 作键：同组件的不同 path（含动态参数）各自成一份实例，
 * query 变化不新建实例。同一 path 全局只有一个实例，切走再切回命中缓存，
 * 页面不会重新挂载、接口不会重复请求。
 */
function routeViewCacheKey(r: RouteLocationNormalizedLoaded): string {
  return r.path;
}

const route = useRoute();
const router = useRouter();

/**
 * 解析 path 在本出口（depth=1）实际渲染的组件名。
 *
 * 目录路由不挂组件，RouterView 的深度跳级会跳过它们，命中 matched 中
 * 第一个带 `components` 的后代 —— 即真实页面组件（如 /system/user → matched[2]）。
 * KeepAlive 的 include / exclude 按「组件 name」匹配，所以必须回解组件，不能用路由 name。
 */
function resolveOutletComponentName(path: string): string {
  try {
    const matched = router.resolve({ path }).matched;
    for (let i = 1; i < matched.length; i++) {
      const comp = matched[i]?.components?.default as
        | { name?: string; __name?: string }
        | undefined;
      if (comp) return comp.name ?? comp.__name ?? "";
    }
    return "";
  } catch {
    return "";
  }
}

/**
 * 开发期守卫：目录路由一旦挂了组件，本出口的深度跳级就会失效。
 *
 * 正常情况下 `matched[1]` 是目录记录（无 `components`），RouterView 会跳过它、直达叶子；
 * 若 `matched[1]` 带 `components` 且后面还有更深的记录，说明中间层挂了组件 —— 本出口
 * 渲染的将是那个目录组件，KeepAlive 的 include/exclude 全部落空，叶子被重复挂载、
 * 接口重复请求。菜单侧由 MenuProcessor / RouteTransformer 保证目录 component 为空，
 * 这里做运行时兜底自检（仅开发环境）。
 */
watch(
  () => route.path,
  (path) => {
    if (!import.meta.env.DEV) return;
    const matched = router.resolve({ path }).matched;
    const shell = matched[1] as { path?: string; components?: Record<string, unknown> } | undefined;
    if (matched.length > 2 && shell?.components?.default) {
      console.warn(
        `[路由缓存] "${path}" 的中间层路由 "${shell.path ?? ""}" 挂了组件，RouterView 深度跳级失效：` +
          "本出口渲染的是它而不是叶子页面，页面会被重复挂载。目录路由的 component 必须为 undefined。"
      );
    }
  },
  { immediate: true }
);

const isNarrowViewport = useMediaQuery("(max-width: 800px)");
const backtopScrollTarget = computed(() => (isNarrowViewport.value ? "" : "#app-content"));
const backtopTargetKey = computed(() => (isNarrowViewport.value ? "win" : "main"));

const { pageTransition, containerWidth, refresh, showWorkTab } = storeToRefs(useSettingsStore());
const { opened, keepAliveExclude: worktabKeepAliveExclude } = storeToRefs(useWorktabStore());

/**
 * 多标签开启时：只把工作栏已打开标签对应的页面组件名放进 include（组件 name，非路由 name）。
 * 关闭多标签时不传 include，避免白名单过窄误伤缓存。
 */
const keepAliveInclude = computed(() => {
  if (!showWorkTab.value) return undefined;
  const names = new Set<string>();
  for (const t of opened.value) {
    if (t.keepAlive === false) continue;
    const name = resolveOutletComponentName(t.path);
    if (name) names.add(name);
  }
  // 兜底当前路由：避免 opened 尚未写入时当前页面命中不到白名单而不被缓存
  if (route.meta.keepAlive !== false) {
    const current = resolveOutletComponentName(route.path);
    if (current) names.add(current);
  }
  return names.size ? Array.from(names) : undefined;
});

/**
 * 关闭标签时 store 会把组件名压入 exclude（按组件名累计）；
 * 另外关闭多标签时 include 为空，`meta.keepAlive === false` 的页面需在此兜底排除，避免被缓存。
 */
const keepAliveExclude = computed(() => {
  const names = new Set(worktabKeepAliveExclude.value ?? []);
  if (route.meta.keepAlive === false) {
    const name = resolveOutletComponentName(route.path);
    if (name) names.add(name);
  }
  return names.size ? Array.from(names) : undefined;
});

const isRefresh = shallowRef(true);
const isOpenRouteInfo = import.meta.env.VITE_OPEN_ROUTE_INFO;

/** 浏览器首次进入：关闭路由过渡动画，避免首屏闪动 */
const isFirstLoad = ref(true);

const actualTransition = computed(() => {
  if (isFirstLoad.value) return "";
  return pageTransition.value;
});

const containerStyle = computed(
  (): CSSProperties => ({
    width: "100%",
    minWidth: 0,
    maxWidth: containerWidth.value,
    flex: "1",
    minHeight: "0",
    display: "flex",
    flexDirection: "column",
  })
);

/** 纵向滚动由外层 `#app-content` 承担，`.layout-content` 仅做限宽居中，路由视图填满剩余高度 */
const contentStyle = computed(
  (): CSSProperties => ({ flex: "1", minHeight: "0", minWidth: 0, width: "100%" })
);

const reload = () => {
  isRefresh.value = false;
  nextTick(() => {
    isRefresh.value = true;
  });
};

watch(refresh, reload, { flush: "post" });

// 组件挂载后标记首次加载完成
onMounted(() => {
  // 延迟一帧，确保首次渲染完成
  nextTick(() => {
    isFirstLoad.value = false;
  });
});
</script>

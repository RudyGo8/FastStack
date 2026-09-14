<!--
  布局根容器：三区域结构
    - #app-sidebar  ← 左侧菜单导航（收起/展开）
    - #app-main     ← 右侧主区域（顶栏 + 页面内容）
      - #app-header  顶栏（面包屑、搜索、通知、用户菜单）
      - #app-content 页面内容（RouterView + 页签）
    - #app-global   ← 全局浮层层（Toast、Modal、新手引导）
-->
<template>
  <div class="app-layout">
    <!-- 水印覆盖层（FaWatermark 组件，内含 ElWatermark，通过 store watermarkVisible 控制显隐） -->
    <FaWatermark :content="userStore.basicInfo?.username || AppConfig.systemInfo.name" />

    <!-- 左侧菜单导航 -->
    <aside id="app-sidebar" aria-label="主菜单导航">
      <FaSidebarMenu />
    </aside>

    <!-- 右侧主区域 -->
    <main id="app-main" aria-label="主要内容区域">
      <div id="app-header">
        <FaHeaderBar />
      </div>
      <div id="app-content">
        <FaPageContent />
      </div>
    </main>

    <!-- 全局浮层层（引导、通知等跨页面组件） -->
    <div id="app-global">
      <FaGlobalComponent />
      <FaGuide v-if="guideVisible" v-model="guideVisible" @skip="onGuideFinished" />
    </div>

    <!-- AI 助手 -->
    <FaAiAssistant v-if="enableAiAssistant" />
  </div>
</template>

<script setup lang="ts">
/**
 * 布局根组件 —— 组装侧栏、顶栏、页面内容、全局浮层。
 *
 * 依赖：
 *   appStore.guideVisible    ← 控制新手指引显隐（session 级状态）
 *   settingStore.showGuide   ← 用户是否关闭指引（持久化）
 *
 * 流程：
 *   首次访问 → guideVisible=true → 用户完成/跳过指引 → onGuideFinished()
 *   → settingStore.showGuide=false → 后续不再显示
 */
import { computed } from "vue";
import { useAppStore, useSettingsStore, useUserStore } from "@stores";
import AppConfig from "@/config";

defineOptions({ name: "AppLayout" });

const appStore = useAppStore();
const settingStore = useSettingsStore();
const userStore = useUserStore();

// ── AI 助手 ──
const enableAiAssistant = computed(() => {
  const isEnabled = settingStore.userEnableAi;
  const isLoggedIn = userStore.basicInfo && Object.keys(userStore.basicInfo).length > 0;
  return isEnabled && isLoggedIn;
});

/** 新手指引显隐 —— session 级状态，首次登录/注册后自动弹出 */
const guideVisible = computed({
  get: () => appStore.guideVisible,
  set: (v: boolean) => appStore.showGuide(v),
});

/** 指引完成后持久化标记「不再显示」 */
function onGuideFinished(): void {
  settingStore.updateSetting("showGuide", false);
}
</script>

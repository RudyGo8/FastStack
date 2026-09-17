/**
 * 系统配置状态管理模块
 *
 * 提供系统配置参数的状态管理
 *
 * ## 主要功能
 *
 * - 网站基础信息管理（标题、版本、描述）
 * - 网站图标配置（登录背景、favicon、Logo）
 * - 安全隐私配置（服务条款、版权、隐私政策）
 * - 接口安全配置（白名单、黑名单）
 * - 演示环境配置
 *
 * ## 使用场景
 *
 * - 系统初始化配置加载
 * - 登录页背景和Logo显示
 * - 底部版权信息展示
 * - 接口安全控制
 *
 * ## 持久化
 *
 * - 使用 localStorage 存储
 * - 自动缓存已加载的配置
 * - 支持强制刷新配置
 *
 * @module store/modules/config.store
 * @author FastapiAdmin Team
 */
import { store } from "@stores";
import ParamsAPI, { ConfigTable } from "@/api/module_system/params";

import { defineStore } from "pinia";
import { ref } from "vue";

export const useConfigStore = defineStore(
  "configStore",
  () => {
    // 配置数据
    const configData = ref<Record<string, ConfigTable>>({});
    // 是否已加载配置
    const isConfigLoaded = ref(false);
    // 是否正在加载配置
    const configLoading = ref(false);
    // 最近一次 fetch 时间戳，用于 force=true 时防止短期重复请求
    let _lastFetchedAt = 0;
    const MIN_FETCH_INTERVAL_MS = 5000;

    /**
     * 获取系统配置
     * @param force 是否强制刷新配置
     */
    async function getConfig(force = false) {
      if (configLoading.value) {
        return;
      }
      if (force && Date.now() - _lastFetchedAt < MIN_FETCH_INTERVAL_MS) {
        return;
      }

      // 已加载且数据非空时，先轻量对比版本号，版本变更自动失效缓存
      let preFetchedList: ConfigTable[] | undefined;
      if (!force && isConfigLoaded.value && Object.keys(configData.value).length > 0) {
        try {
          const resp = await ParamsAPI.getInitConfig();
          const list = resp?.data?.data;
          if (!Array.isArray(list)) return;
          const remoteVer = list.find((i) => i.config_key === "version")?.config_value;
          const localVer = configData.value["version"]?.config_value;
          if (!remoteVer || remoteVer === localVer) return;
          // 版本不同，走强制刷新
          preFetchedList = list;
          force = true;
        } catch {
          return;
        }
      }

      configLoading.value = true;
      try {
        if (force) {
          configData.value = {};
        }

        const list = preFetchedList ?? (await ParamsAPI.getInitConfig())?.data?.data;
        if (!Array.isArray(list)) {
          console.warn("[configStore] getInitConfig: 响应 data 非数组");
          return;
        }
        applyConfigList(list);
      } catch (error) {
        console.warn("[configStore] 获取配置失败:", error);
      } finally {
        configLoading.value = false;
      }
    }

    function applyConfigList(list: ConfigTable[]) {
      list.forEach((item: ConfigTable) => {
        if (item.config_value !== undefined && item.config_key) {
          configData.value[item.config_key] = item;
        }
      });
      isConfigLoaded.value = true;
      _lastFetchedAt = Date.now();
    }

    return {
      configData,
      isConfigLoaded,
      configLoading,
      getConfig,
    };
  },
  {
    persist: {
      key: "config-v2",
      storage: localStorage,
      pick: ["isConfigLoaded"],
    },
  }
);

export function useConfigStoreHook() {
  return useConfigStore(store);
}

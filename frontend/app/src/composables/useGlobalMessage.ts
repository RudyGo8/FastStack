import { defineStore } from 'pinia'

export interface GlobalMessageOptions {
  title?: string
  content?: string
  type?: 'alert' | 'confirm'
  showCancel?: boolean
  confirmText?: string
  cancelText?: string
  success?: (res: { confirm: boolean, cancel: boolean }) => void
  fail?: (err: unknown) => void
}

/**
 * 全局消息 store：GlobalMessage 组件监听 messageOptions，
 * 仅当触发页面与 currentPage 一致时展示，避免跨页误弹
 */
export const useGlobalMessage = defineStore('global-message', {
  state: () => ({
    messageOptions: null as GlobalMessageOptions | null,
    currentPage: '',
  }),
  actions: {
    show(options: GlobalMessageOptions) {
      this.currentPage = getCurrentPath()
      this.messageOptions = options
    },
    close() {
      this.messageOptions = null
    },
  },
})

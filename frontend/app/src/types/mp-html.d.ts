/**
 * mp-html 富文本组件类型声明（uni_modules easycom 自动注册，需手动补充 GlobalComponents）
 * 仅声明本项目实际用到的属性，完整列表见 uni_modules/mp-html/components/mp-html/mp-html.vue
 */
declare module 'vue' {
  interface GlobalComponents {
    MpHtml: {
      /** 用于渲染的 html 字符串 */
      content?: string
      /** 是否解析 markdown（需 markdown 插件） */
      markdown?: boolean
      /** 标签默认样式 */
      tagStyle?: Record<string, string>
      /** 容器的样式 */
      containerStyle?: string
      /** 是否允许外部链接被点击时自动复制 */
      copyLink?: boolean | string
      /** 主域名，用于拼接链接 */
      domain?: string
      /** 图片出错时的占位图链接 */
      errorImg?: string
      /** 是否开启图片懒加载 */
      lazyLoad?: boolean | string
      /** 是否允许图片被点击时自动预览 */
      previewImg?: boolean | string
      /** 是否给每个表格添加一个滚动层使其能单独横向滚动 */
      scrollTable?: boolean | string
      /** 是否开启长按复制 */
      selectable?: boolean | string
      /** 是否将 title 标签的内容设置到页面标题 */
      setTitle?: boolean | string
      /** 是否允许图片被长按时显示菜单 */
      showImgMenu?: boolean | string
      /** 是否使用锚点链接 */
      useAnchor?: boolean | number
      /** 是否在播放一个视频时自动暂停其他视频 */
      pauseVideo?: boolean | string
    }
  }
}

export {}

/**
 * @fileoverview markdown 插件（ESM 版，适配本项目 Vue3 CLI 环境）
 * 原版来自 mp-html 官方仓库 plugins/markdown/index.js
 * 差异：CommonJS 改为 ESM；this.vm.properties.markdown 改为 this.vm.markdown（Vue3 组件无 properties）
 */
import marked from './marked.min.js'

let index = 0

function Markdown (vm) {
  this.vm = vm
  vm._ids = {}
}

Markdown.prototype.onUpdate = function (content) {
  // 仅当组件开启 markdown 属性时才做转换
  if (this.vm.markdown) {
    return marked(content)
  }
}

Markdown.prototype.onParse = function (node, vm) {
  if (vm.options.markdown) {
    // 中文 id 需要转换，否则无法跳转
    if (vm.options.useAnchor && node.attrs && /[\u4e00-\u9fa5]/.test(node.attrs.id)) {
      const id = 't' + index++
      this.vm._ids[node.attrs.id] = id
      node.attrs.id = id
    }
    // 为常见块级标签打上样式标记 class，便于外部统一样式
    if (node.name === 'p' || node.name === 'table' || node.name === 'tr' || node.name === 'th' || node.name === 'td' || node.name === 'blockquote' || node.name === 'pre' || node.name === 'code') {
      node.attrs.class = `md-${node.name} ${node.attrs.class || ''}`
    }
  }
}

export default Markdown

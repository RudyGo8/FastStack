<script setup lang="ts">
onLaunch(() => {})
</script>

<style lang="scss">
/* 全局样式按职责拆分：
   - theme.scss：玻璃水滴渐变主题变量（6 套主题色）
   - base.scss：页面容器 / 暗色背景等基础全局样式
   页面级样式（登录表单输入框、滑块等）保留在各页面 scoped 内 */
@import './styles/theme.scss';
@import './styles/base.scss';
</style>

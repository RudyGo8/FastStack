/// <reference types="@uni-helper/vite-plugin-uni-pages/client" />
import { createRouter } from '@wot-ui/router'
import { pages, subPackages } from 'virtual:uni-pages'
import { useUserStore } from '@/store/userStore'

function generateRoutes() {
  const routes = pages.map((page) => {
    const newPath = `/${page.path}`
    return { ...page, path: newPath }
  })
  if (subPackages && subPackages.length > 0) {
    subPackages.forEach((subPackage) => {
      const subRoutes = subPackage.pages.map((page: (typeof pages)[number]) => {
        const newPath = `/${subPackage.root}/${page.path}`
        return { ...page, path: newPath }
      })
      routes.push(...subRoutes)
    })
  }
  return routes
}

const router = createRouter({
  routes: generateRoutes(),
})

// 鉴权守卫：未登录访问受保护页面 → 重定向到登录页（启动无 token 时也会被拦截）
// 注意：wot-ui router 重定向会沿用原导航类型（如 pushTab），
// 因此必须通过 navType 显式指定跳转方式，否则会对非 tabBar 页执行 switchTab 而报错。
router.beforeEach((to, from, next) => {
  const userStore = useUserStore()
  const isAuthPage = to.name === 'login' || to.name === 'register' || to.name === 'forget'
  if (!isAuthPage && !userStore.isLoggedIn()) {
    next({
      path: '/pages/login/index',
      navType: 'replace',
      query: to.fullPath && to.fullPath !== '/' ? { redirect: to.fullPath } : {},
    })
    return
  }
  // 已登录访问登录/注册页 → 回到首页
  if (isAuthPage && userStore.isLoggedIn()) {
    next({ path: '/pages/index/index', navType: 'pushTab' })
    return
  }
  next()
})

// 导航完成钩子：预留页面切换记录 / 埋点上报 / 动态标题等能力，按需启用
router.afterEach((to, from) => {
  if (to.path && from.path && to.path !== from.path) {
    console.log(`📍 页面切换: ${from.path} → ${to.path}`)
  }
})

export default router

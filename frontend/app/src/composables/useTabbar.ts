export interface TabbarItem {
  name: string
  value?: number
  active: boolean
  titleKey: string
  icon: string
}

const tabbarItems = ref<TabbarItem[]>([
  { name: 'home', active: true, titleKey: 'common.tab.home', icon: 'home' },
  { name: 'work', active: false, titleKey: 'common.tab.work', icon: 'apps' },
  { name: 'mine', active: false, titleKey: 'common.tab.mine', icon: 'user' },
])

export function useTabbar() {
  const tabbarList = computed(() => tabbarItems.value)

  const activeTabbar = computed(() => {
    const item = tabbarItems.value.find(item => item.active)
    return item || tabbarItems.value[0]
  })

  const getTabbarItemValue = (name: string) => {
    const item = tabbarItems.value.find(item => item.name === name)
    return item?.value
  }

  const setTabbarItem = (name: string, value: number) => {
    const tabbarItem = tabbarItems.value.find(item => item.name === name)
    if (tabbarItem) {
      tabbarItem.value = value
    }
  }

  const setTabbarItemActive = (name: string) => {
    tabbarItems.value.forEach((item) => {
      if (item.name === name) {
        item.active = true
      }
      else {
        item.active = false
      }
    })
  }

  return {
    tabbarList,
    activeTabbar,
    getTabbarItemValue,
    setTabbarItem,
    setTabbarItemActive,
  }
}

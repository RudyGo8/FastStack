/*
 * @Author: weisheng
 * @Date: 2025-06-23 22:23:05
 * @LastEditTime: 2025-06-27 13:04:54
 * @LastEditors: weisheng
 * @Description:
 * @FilePath: /wot-starter/pages.config.ts
 * 记得注释
 */
import process from 'node:process'
import { defineUniPages } from '@uni-helper/vite-plugin-uni-pages'

// 按构建平台动态裁剪配置（vite-plugin-uni-pages 不处理条件编译注释，用 JS 逻辑）
const UNI_PLATFORM = process.env.UNI_PLATFORM || ''
const isWeixin = UNI_PLATFORM === 'mp-weixin'
const isAlipay = UNI_PLATFORM === 'mp-alipay'

export default defineUniPages({
  pages: [],
  globalStyle: {
    // 导航栏配置
    navigationBarBackgroundColor: '@navBgColor',
    navigationBarTextStyle: '@navTxtStyle',
    navigationBarTitleText: 'FastapiAdmin',

    // 页面背景配置
    backgroundColor: '@bgColor',
    backgroundTextStyle: '@bgTxtStyle',
    backgroundColorTop: '@bgColorTop',
    backgroundColorBottom: '@bgColorBottom',

    // 下拉刷新配置
    enablePullDownRefresh: false,
    onReachBottomDistance: 50,

    // 页面切换动画（微信小程序 window 不支持 animationType/animationDuration，构建时排除）
    ...(isWeixin ? {} : { animationType: 'pop-in', animationDuration: 300 }),
  },
  tabBar: {
    custom: true,
    // customize/overlay 为支付宝小程序 tabBar 配置（微信端编译进 app.json 会告警，按平台裁剪）
    ...(isAlipay ? { customize: true, overlay: true } : {}),
    height: '0',
    color: '@tabColor',
    selectedColor: '@tabSelectedColor',
    backgroundColor: '@tabBgColor',
    borderStyle: '@tabBorderStyle',
    list: [{
      pagePath: 'pages/index/index',
    }, {
      pagePath: 'pages/work/index',
    }, {
      pagePath: 'pages/mine/index',
    }],
  },
})

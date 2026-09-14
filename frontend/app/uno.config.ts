import { presetUni } from '@uni-helper/unocss-preset-uni'
import { presetWot } from '@wot-ui/unocss-preset'

import {
  defineConfig,
  extractorDefault,
  presetIcons,
  transformerDirectives,
  transformerVariantGroup,
} from 'unocss'

// 默认 extractorSplit 会把普通代码（减法、注释等）拆出纯连字符 token（如 "-"），
// 被 presetIcons 误当作图标名加载并产生 warn 日志；包装一层过滤掉无意义 token
const splitFiltered: Extractor = {
  ...extractorDefault,
  name: '@unocss/core/extractor-split:filtered',
  extract({ code }) {
    const tokens = extractorDefault.extract({ code })
    return Array.isArray(tokens) ? tokens.filter(t => !/^-+$/.test(t)) : tokens
  },
}

export default defineConfig({
  extractorDefault: splitFiltered,
  presets: [
    presetWot({
      baseTokens: true,
    }),
    presetUni({
      attributify: {
        prefixedOnly: true,
      },
    }),
    presetIcons({
      scale: 1.2,
      warn: true,
      extraProperties: {
        'display': 'inline-block',
        'vertical-align': 'middle',
      },
      // HBuilderX 必须针对要使用的 Collections 做异步导入
      // collections: {
      //   carbon: () => import('@iconify-json/carbon/icons.json').then(i => i.default),
      // },
    }),
  ],
  transformers: [
    transformerDirectives(),
    transformerVariantGroup(),
  ],
  content: {
    pipeline: {
      // 排除 node_modules：避免 attributify 提取器把 wot-ui 源码中
      // 的头部注释时间戳、update:modelValue 等字符串误提为 [name=""] 候选，
      // 生成 [\30 5_a_24=""]{05:24=""} 之类的垃圾 CSS
      exclude: ['node_modules/**'],
    },
  },
})

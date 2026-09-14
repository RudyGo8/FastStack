/**
 * markdown 渲染公共配置（配合 mp-html 组件使用）
 * 中性 rgba 色可自适应亮暗主题；使用 wot 语义色可随品牌主题联动
 */
export const MARKDOWN_TAG_STYLE: Record<string, string> = {
  h1: 'font-size:17px;font-weight:700;margin:10px 0 6px;line-height:1.5;',
  h2: 'font-size:16px;font-weight:700;margin:9px 0 5px;line-height:1.5;',
  h3: 'font-size:15px;font-weight:700;margin:8px 0 4px;line-height:1.5;',
  p: 'margin:6px 0;line-height:1.7;',
  ul: 'margin:6px 0;padding-left:18px;',
  ol: 'margin:6px 0;padding-left:18px;',
  li: 'margin:3px 0;line-height:1.7;',
  code: 'font-family:ui-monospace,SFMono-Regular,Consolas,monospace;font-size:85%;background:rgba(127,127,127,.14);padding:2px 5px;border-radius:4px;',
  pre: 'background:rgba(127,127,127,.10);padding:10px 12px;border-radius:8px;overflow-x:auto;margin:8px 0;',
  blockquote: 'margin:8px 0;padding:2px 12px;border-left:3px solid rgba(127,127,127,.35);color:rgba(127,127,127,.9);',
  table: 'width:100%;border-collapse:collapse;margin:8px 0;',
  th: 'border:1px solid rgba(127,127,127,.25);padding:6px 10px;text-align:left;font-weight:600;',
  td: 'border:1px solid rgba(127,127,127,.25);padding:6px 10px;text-align:left;',
  a: 'color:#4F8CFF;',
  img: 'max-width:100%;border-radius:8px;',
}

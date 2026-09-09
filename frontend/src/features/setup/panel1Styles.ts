/** 设置模拟面板样式（对照 panel1.png / design），统一字体、尺寸、颜色与间距 */

export const panel1 = {
  font: {
    family: '"Inria Sans", sans-serif',
    label: 14,
    body: 12,
  },
  colors: {
    /** 区块标题：预览、环境参数、Agent Profile，字号 14 */
    label: "#353536",
    /** 环境参数子项：最大深度、Agent数量，字号 12 */
    envParamLabel: "#697281",
    secondary: "#808993",
    dashBorder: "#D0D3D8",
    /** 上传框/预览框内部背景，与右侧偏移分析预览框一致 */
    uploadBg: "#F4F5F7",
    uploadText: "#808993",
    previewBg: "#F4F5F7",
    /** 内嵌边框：BDC9D1，inside，dashed 2，weight 1（与右侧预览框一致） */
    insetBorder: "1px dashed #BDC9D1",
    descBorder: "#D0D3D8",
    divider: "#E5E7EA",
    envPanelBg: "#F3F4F5",
    sliderTrack: "#DADCE0",
    sliderFilled: "#6B767E",
    sliderThumb: "#FFFFFF",
    sliderThumbStroke: "#0C91BE",
    sliderThumbInnerStroke: "#D1D4EA",
    agentPoolBorder: "#E5E7EA",
    agentCardBorder: "#E5E7EA",
    agentCardBg: "#F5F6F8",
    agentCardSelectedBg: "#E8EEF5",
    startButton: "#3D4450",
  },
  sizes: {
    /** 上传框高度（缩小以让 Agent profile 池可见区域更大） */
    uploadHeight: 32,
    uploadRadius: 8,
    /** 内嵌边框向内偏移（px），与 insetBorder 配合 */
    insetBorderOffset: -1,
    previewMinHeight: 160,
    /** 图表理解输入框最小高度（缩小以让整页在框内完整显示） */
    descMinHeight: 40,
    sliderThumb: 16,
    /** 环境参数每行滑动条容器高度 */
    sliderRowHeight: 20,
    agentCardHeight: 64,
    agentCircle: 36,
    agentIconInCircle: 20,
    /** Auto Generate 按钮高度（可单独缩小，不影响 Start Simulation） */
    autoGenerateButtonHeight: 32,
    /** Start Simulation 按钮高度（不随其他调整改变） */
    startButtonHeight: 36,
  },
  borders: {
    dividerWeight: 1,
    sliderStrokeWeight: 1,
    sliderThumbInnerStrokeWeight: 0.6,
    agentCardStroke: 1,
  },
  spacing: {
    section: 12,
    block: 8,
    /** 左侧面板紧凑间距，便于整页在框内完整显示 */
    blockSmall: 6,
    panelPaddingX: 26,
  },
} as const;

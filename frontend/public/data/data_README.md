# 模拟数据集

10 data visualization cases designed for simulating framing shifts in online discourse.

## 目录

```

├── data/
│   ├── 01_global_temperature/   # NOAA temperature anomaly — bar chart
│   ├── 02_xx/
│   ├── ...
│   
│
│   Each case contains:
│   ├── data.csv                 # 原始数据
│   ├── chart_spec.json          # Vega-Lite代码 (数据已嵌入,可渲染，后续agent主要修改的是这个文件)
│   ├── metadata.json            # 图表的原始信息(可作为输入的辅助信息)
│   └── visualization.html             # Standalone preview (open in browser)可视化展示
│   └── visualization.svg              # svg format svg格式可视化图展示
```


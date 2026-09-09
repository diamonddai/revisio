# Evaluation Report

## Per-Case Metrics

| Case   | Topic      |   GT Ops |   JSD (System) |   JSD (Random) |   DTW (System) |   DTW (Random) |
|--------|------------|----------|----------------|----------------|----------------|----------------|
| C01    | 新冠每日新增确诊趋势 |        9 |         0.0176 |         0.0447 |            2.5 |           3.74 |
| C02    | 气候温度变化     |        9 |         0.0034 |         0.0212 |            0   |           2    |


## Aggregate Comparison

| Metric   |   System (mean) |   Random (mean) |   Delta |
|----------|-----------------|-----------------|---------|
| JSD      |          0.0105 |           0.033 | -0.0224 |
| DTW      |          1.25   |           2.87  | -1.62   |


## Statistical Significance (Wilcoxon Signed-Rank Test)

- **JSD**: Not enough paired samples (need >= 5, have 2)
- **DTW**: Not enough paired samples (need >= 5, have 2)

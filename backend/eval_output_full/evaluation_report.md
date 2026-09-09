# Quantitative Evaluation: Simulated vs. Real-World Lineages

> **Metric interpretation**:
> - JSD (Jensen-Shannon Divergence): range [0, 1]. 0 = identical operation distributions; 1 = completely disjoint. Lower is better.
> - DTW (Dynamic Time Warping on cumulative op-count trajectory): range [0, inf). 0 = identical drift curves. Lower is better.
> - Wilcoxon signed-rank test used for paired significance testing (non-parametric).

## Table 1. Per-Case Framing Fidelity Metrics

| Case    | Topic                 | #GT Ops   | JSD_sys           | JSD_rand          | DTW_sys       | DTW_rand      |
|---------|-----------------------|-----------|-------------------|-------------------|---------------|---------------|
| C01     | COVID Excess Deaths   | 9         | 0.0176 +/- 0.0000 | 0.0294 +/- 0.0032 | 2.50 +/- 0.00 | 2.84 +/- 0.73 |
| C02     | Global Temperature    | 9         | 0.0034 +/- 0.0000 | 0.0529 +/- 0.0102 | 0.00 +/- 0.00 | 0.89 +/- 0.68 |
| C04     | Amazon Deforestation  | 9         | 0.0264 +/- 0.0000 | 0.0549 +/- 0.0167 | 2.00 +/- 0.00 | 2.06 +/- 0.91 |
| C07     | US Unemployment       | 7         | 0.0101 +/- 0.0000 | 0.0215 +/- 0.0026 | 2.00 +/- 0.00 | 1.17 +/- 0.85 |
| C08     | US Immigration        | 11        | 0.0359 +/- 0.0000 | 0.0328 +/- 0.0057 | 4.00 +/- 0.00 | 2.17 +/- 0.54 |
| C11     | CO2 Concentration     | 2         | 0.0150 +/- 0.0000 | 0.0217 +/- 0.0037 | 3.32 +/- 0.00 | 2.08 +/- 1.47 |
| C22     | Voter Turnout         | 5         | 0.0188 +/- 0.0000 | 0.0233 +/- 0.0034 | 1.67 +/- 0.00 | 1.12 +/- 0.00 |
| C23     | Recession Probability | 7         | 0.0215 +/- 0.0000 | 0.0486 +/- 0.0079 | 2.26 +/- 0.00 | 2.85 +/- 1.52 |
| **Avg** | *N=8*                 | -         | 0.0186 +/- 0.0092 | 0.0356 +/- 0.0134 | 2.22 +/- 1.11 | 1.90 +/- 0.71 |

*Values reported as mean +/- std across N=3 runs per condition. Lower values indicate higher similarity to ground truth.*

## Table 2. Statistical Comparison (Wilcoxon Signed-Rank Test)

| Metric   |   System (mean) |   Random (mean) |   W |   p-value | Sig.   |
|----------|-----------------|-----------------|-----|-----------|--------|
| JSD      |          0.0186 |          0.0356 |   1 |    0.0156 | *      |
| DTW      |          2.22   |          1.90   |  13 |    0.5469 | n.s.   |

*Significance: \*\*\* p<0.001, \*\* p<0.01, \* p<0.05, n.s. p>=0.05.*

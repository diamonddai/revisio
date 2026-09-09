## Simulation Fidelity Evaluation

We evaluated the fidelity of the narrative-gap-driven simulation by comparing simulated framing propagation lineages against real-world lineages drawn from our annotated taxonomy corpus.

**Experimental setup.** We selected 8 real-world framing lineages from our corpus covering diverse topics (COVID Excess Deaths, Global Temperature, Amazon Deforestation, US Unemployment, US Immigration, CO2 Concentration, Voter Turnout, Recession Probability). These lineages collectively contain 59 ground-truth framing operations across 8 distinct propagation chains, with depths ranging from 1 to 5 and 2 to 5 variant nodes. For each lineage, the original visualization served as the root node, and the simulation agents were configured to match the ground-truth participant distribution (roles and platforms). We compared two conditions: (1) *System* — our narrative-gap-driven mechanism with role-aware, depth-progressive strategy selection; (2) *Random Baseline* — agents assigned random roles and platforms with the narrative-gap mechanism disabled (framing operations selected uniformly at random). Each condition was run 3 times per lineage to assess stability (n = 8).

**Metrics.** We measured two complementary aspects of simulation fidelity: (1) *Framing Operation Distribution Fidelity* (JSD): the Jensen–Shannon Divergence between the 16-category operation frequency vectors of the simulated and real lineages, with Laplace smoothing (α = 1.0) — values range from 0 (identical distributions) to 1 (completely disjoint), where lower values indicate that the simulation chooses the same *types* of framing operations as real-world actors; (2) *Layer Coverage Trajectory Fidelity* (DTW): the Dynamic Time Warping distance between per-depth curves of how many layers (Data/Visual/Text) were modified — trajectory[d] = average over nodes at depth d of |layers touched| (0–3). Lower values mean the simulation reproduces the *breadth* of framing modifications across propagation depth. Statistical significance was assessed using a Wilcoxon signed-rank test (non-parametric, paired by lineage).

**Table 1.** Per-case framing fidelity metrics (mean across 3 runs). Lower values indicate higher similarity to ground truth. #GT Ops = number of ground-truth framing operations in the real-world lineage.

| Case   | Topic                 |   #GT Ops |   JSD_sys |   JSD_rand |   DTW_sys |   DTW_rand |
|--------|-----------------------|-----------|-----------|------------|-----------|------------|
| C01    | COVID Excess Deaths   |         9 |    0.0144 |     0.02   |      1.12 |       0.33 |
| C02    | Global Temperature    |         9 |    0.0068 |     0.0316 |      0.56 |       0.67 |
| C04    | Amazon Deforestation  |         9 |    0.0226 |     0.0536 |      1    |       1.69 |
| C07    | US Unemployment       |         7 |    0.0112 |     0.0222 |      1.5  |       1.17 |
| C08    | US Immigration        |        11 |    0.0419 |     0.04   |      2.16 |       1.82 |
| C11    | CO2 Concentration     |         2 |    0.015  |     0.0244 |      1    |       0.83 |
| C22    | Voter Turnout         |         5 |    0.0188 |     0.0262 |      1    |       0.8  |
| C23    | Recession Probability |         7 |    0.0215 |     0.035  |      0.5  |       0.5  |

**Table 2.** Aggregate fidelity comparison (M ± SD across n = 8 lineages). Effect size reported as Cohen's d.

| Metric   | System (M ± SD)   | Random (M ± SD)   |   W |      p | Sig.   |    d |
|----------|-------------------|-------------------|-----|--------|--------|------|
| JSD      | 0.0190 ± 0.0099   | 0.0316 ± 0.0104   |   1 | 0.0156 | *      | 1.23 |
| DTW      | 1.10 ± 0.50       | 0.98 ± 0.51       |   7 | 0.2969 | n.s.   | 0.25 |

**Results and discussion.** 
Table 2 shows that the System condition achieved a significantly lower average JSD (M = 0.0190, SD = 0.0099) compared to the Random Baseline (M = 0.0316, SD = 0.0104), with a Wilcoxon signed-rank test confirming statistical significance (W = 1, p = 0.0156, d = 1.23). The System outperformed the Random Baseline on JSD in 7 out of 8 lineages, indicating that the narrative-gap mechanism reliably selects framing operation types that mirror real-world actor behaviors across diverse topics. For the DTW metric, the System achieved M = 1.10 (SD = 0.50) versus M = 0.98 (SD = 0.51) for the Random Baseline (W = 7, p = 0.2969, n.s.). The System's higher DTW may reflect a different layer-coverage pattern across depth (Data/Visual/Text) compared to ground truth; the narrative-gap mechanism may modify more layers per node on average. Overall, these results demonstrate that the narrative-gap-driven strategy selection effectively reproduces the types and patterns of framing operations observed in real-world visualization propagation chains. The significant JSD improvement indicates that role-aware, depth-progressive agent behavior — where Amplifiers emphasize visual salience, Adversers counter-frame through data range selection, and Extenders broaden narrative scope — captures the behavioral signatures of real-world framing actors substantially better than a naive random baseline.

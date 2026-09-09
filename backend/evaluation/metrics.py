"""Evaluation metrics: JSD for operation distribution and DTW for drift trajectory."""

from __future__ import annotations

import numpy as np
from scipy.spatial.distance import jensenshannon

from evaluation.ground_truth import get_operation_vector


def compute_jsd(gt_ops: list[str], sim_ops: list[str], alpha: float = 1.0) -> float:
    """Compute Jensen-Shannon Divergence between two operation distributions.

    Both inputs are flat lists of canonical operation names.
    Uses Laplace smoothing with strength alpha.
    Returns JSD in [0, 1].
    """
    gt_vec = get_operation_vector(gt_ops) + alpha
    sim_vec = get_operation_vector(sim_ops) + alpha

    gt_dist = gt_vec / gt_vec.sum()
    sim_dist = sim_vec / sim_vec.sum()

    # scipy.jensenshannon returns sqrt(JSD); square to get JSD in [0,1]
    return float(jensenshannon(gt_dist, sim_dist) ** 2)


def compute_dtw(trajectory_a: list[float], trajectory_b: list[float]) -> float:
    """Compute DTW distance between two cumulative ops trajectories.

    Each trajectory is a list of floats: [cum_ops_depth_0, cum_ops_depth_1, ...].
    Uses dtaidistance for the computation.
    """
    if not trajectory_a or not trajectory_b:
        return float("inf")

    try:
        from dtaidistance import dtw
        return float(dtw.distance(
            np.array(trajectory_a, dtype=np.float64),
            np.array(trajectory_b, dtype=np.float64),
        ))
    except ImportError:
        return _dtw_fallback(trajectory_a, trajectory_b)


def _dtw_fallback(a: list[float], b: list[float]) -> float:
    """Pure-Python DTW when dtaidistance is not available."""
    n, m = len(a), len(b)
    dtw_matrix = np.full((n + 1, m + 1), np.inf)
    dtw_matrix[0, 0] = 0.0

    for i in range(1, n + 1):
        for j in range(1, m + 1):
            cost = abs(a[i - 1] - b[j - 1])
            dtw_matrix[i, j] = cost + min(
                dtw_matrix[i - 1, j],
                dtw_matrix[i, j - 1],
                dtw_matrix[i - 1, j - 1],
            )
    return float(dtw_matrix[n, m])

"""Scenario reduction algorithms for stochastic optimization.

Compresses high-dimensional Monte Carlo scenarios to a reduced representative set
while minimizing the Kantorovich / Wasserstein probability metric distance.
"""

import numpy as np
from sklearn.cluster import KMeans
import structlog

logger = structlog.get_logger(__name__)


class ScenarioReducer:
    """Reduces Monte Carlo scenarios using cluster centroids and Voronoi cell probability mass."""

    def __init__(self, target_scenarios: int = 100, seed: int = 42) -> None:
        self.target_scenarios = target_scenarios
        self.seed = seed

    def reduce(
        self,
        D_scenarios: np.ndarray,
        probabilities: np.ndarray | None = None,
    ) -> tuple[np.ndarray, np.ndarray]:
        """Reduces D_scenarios of shape (S, N) to (K, N) where K << S.

        Returns:
            reduced_scenarios: shape (K, N)
            reduced_probabilities: shape (K,) summing to 1.0
        """
        S, N = D_scenarios.shape
        K = min(self.target_scenarios, S)

        if K == S:
            probs = probabilities if probabilities is not None else np.ones(S) / S
            return D_scenarios, probs

        logger.info("Executing scenario reduction", original_scenarios=S, target_scenarios=K)

        kmeans = KMeans(n_clusters=K, random_state=self.seed, n_init=5)
        cluster_labels = kmeans.fit_predict(D_scenarios)
        reduced_scenarios = kmeans.cluster_centers_

        # Calculate cluster probabilities (mass of each Voronoi cluster)
        if probabilities is None:
            probabilities = np.ones(S) / S

        reduced_probs = np.zeros(K)
        for cluster_idx in range(K):
            mask = cluster_labels == cluster_idx
            reduced_probs[cluster_idx] = float(np.sum(probabilities[mask]))

        # Re-normalize to ensure exact sum == 1.0
        reduced_probs /= np.sum(reduced_probs)

        logger.info("Scenario reduction complete", reduced_shape=reduced_scenarios.shape)
        return np.maximum(0.0, np.round(reduced_scenarios, 1)), reduced_probs

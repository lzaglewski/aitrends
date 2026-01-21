"""
Temporal weighting for embeddings to prioritize recent content.

Applies exponential decay to embeddings based on article age,
ensuring more recent articles have stronger influence on topic clustering.
"""

from typing import List
from datetime import datetime
import numpy as np
from loguru import logger


class TemporalWeightCalculator:
    """
    Calculates temporal weights using exponential decay.

    Recent articles get higher weights, older articles decay exponentially.
    Formula: w = exp(-λ * days_ago)

    Example with λ=0.05:
    - Today: weight = 1.0
    - 7 days ago: weight = 0.70
    - 14 days ago: weight = 0.50
    - 30 days ago: weight = 0.22
    """

    def __init__(self, lambda_decay: float = 0.05):
        """
        Initialize the calculator.

        Args:
            lambda_decay: Decay rate (higher = faster decay)
                         0.05 gives ~14 day half-life
                         0.1 gives ~7 day half-life
        """
        self.lambda_decay = lambda_decay

    def calculate_weight(self, published_date: datetime, reference_date: datetime = None) -> float:
        """
        Calculate temporal weight for an article.

        Args:
            published_date: When the article was published
            reference_date: Reference date (default: now)

        Returns:
            Weight between 0 and 1
        """
        if reference_date is None:
            reference_date = datetime.utcnow()

        # Handle timezone-naive dates
        if published_date.tzinfo is not None:
            published_date = published_date.replace(tzinfo=None)
        if reference_date.tzinfo is not None:
            reference_date = reference_date.replace(tzinfo=None)

        # Calculate days ago
        delta = reference_date - published_date
        days_ago = max(0, delta.total_seconds() / 86400)  # Ensure non-negative

        # Exponential decay: w = exp(-λ * t)
        weight = np.exp(-self.lambda_decay * days_ago)

        return float(weight)

    def calculate_weights(
        self,
        published_dates: List[datetime],
        reference_date: datetime = None
    ) -> np.ndarray:
        """
        Calculate temporal weights for multiple articles.

        Args:
            published_dates: List of publication dates
            reference_date: Reference date (default: now)

        Returns:
            Numpy array of weights
        """
        weights = np.array([
            self.calculate_weight(date, reference_date)
            for date in published_dates
        ])

        return weights

    def apply_weights_to_embeddings(
        self,
        embeddings: np.ndarray,
        dates: List[datetime],
        reference_date: datetime = None
    ) -> np.ndarray:
        """
        Apply temporal weights to embeddings.

        Multiplies each embedding vector by its temporal weight,
        giving recent articles more influence in clustering.

        Args:
            embeddings: Numpy array of embeddings (shape: [n_docs, embedding_dim])
            dates: List of publication dates
            reference_date: Reference date (default: now)

        Returns:
            Weighted embeddings (same shape as input)
        """
        if embeddings.shape[0] != len(dates):
            raise ValueError(
                f"Embeddings count ({embeddings.shape[0]}) "
                f"doesn't match dates count ({len(dates)})"
            )

        # Calculate weights
        weights = self.calculate_weights(dates, reference_date)

        # Apply weights (broadcast multiplication)
        weighted_embeddings = embeddings * weights[:, np.newaxis]

        # Log statistics
        logger.info(
            f"⏰ Applied temporal weighting: "
            f"mean weight = {weights.mean():.3f}, "
            f"min = {weights.min():.3f}, "
            f"max = {weights.max():.3f}"
        )

        return weighted_embeddings

    def get_half_life_days(self) -> float:
        """
        Calculate the half-life in days for current decay rate.

        Half-life is when weight = 0.5
        Solving: 0.5 = exp(-λ * t) => t = ln(2) / λ

        Returns:
            Half-life in days
        """
        return np.log(2) / self.lambda_decay

    def visualize_decay_curve(self, max_days: int = 60) -> str:
        """
        Generate ASCII visualization of decay curve.

        Args:
            max_days: Maximum days to show

        Returns:
            ASCII string visualization
        """
        days = list(range(0, max_days + 1, 5))
        weights = [self.calculate_weight(
            datetime.utcnow() - timedelta(days=d)
        ) for d in days]

        lines = ["Temporal Decay Curve:"]
        lines.append(f"λ = {self.lambda_decay:.3f}, half-life = {self.get_half_life_days():.1f} days\n")

        for day, weight in zip(days, weights):
            bar_length = int(weight * 50)
            bar = "█" * bar_length
            lines.append(f"{day:3d} days: {bar} {weight:.3f}")

        return "\n".join(lines)


# For import convenience
from datetime import timedelta

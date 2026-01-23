"""
Trend lifecycle analyzer for multi-period trend analysis.

Analyzes trends across multiple time periods to determine lifecycle stages
and calculate velocity metrics.
"""

from typing import List, Dict, Tuple, Optional
from datetime import datetime, timedelta
from loguru import logger

from ..storage.database import Database


class TrendLifecycleAnalyzer:
    """
    Analyzes topic trends across multiple time periods to determine lifecycle stages.

    Stages:
    - emerging: New topic, rapid initial growth (velocity > 0.2)
    - growing: Sustained positive growth (growth > 0.3, velocity > 0)
    - peak: High count but slowing growth (growth > 0, velocity < 0)
    - declining: Negative growth (growth < -0.2)
    - stable: Low variance in counts (|growth| < 0.2)
    """

    def __init__(self, db: Database):
        """
        Initialize the lifecycle analyzer.

        Args:
            db: Database instance
        """
        self.db = db

    def analyze_lifecycle(
        self,
        topic_id: int,
        periods: List[Tuple[datetime, datetime]],
        use_weighted_counts: bool = False
    ) -> Dict:
        """
        Analyze lifecycle for a topic across multiple periods.

        Args:
            topic_id: Topic ID to analyze
            periods: List of (start, end) date tuples for each period
            use_weighted_counts: Whether to use source-weighted counts

        Returns:
            Dict with lifecycle metrics:
                - counts: List of counts for each period
                - growth_rates: List of growth rates
                - velocity: Rate of change of growth rate
                - stage: Lifecycle stage classification
                - trend_direction: 'up', 'down', or 'stable'
        """
        if len(periods) < 2:
            logger.warning("Need at least 2 periods for lifecycle analysis")
            return None

        # Get counts for each period
        counts = []
        for period_start, period_end in periods:
            if use_weighted_counts:
                period_counts = self.db.get_weighted_topic_counts(period_start, period_end)
            else:
                period_counts = self.db.get_topic_counts(period_start, period_end)

            count = period_counts.get(topic_id, 0)
            counts.append(count)

        # Calculate growth rates between consecutive periods
        growth_rates = []
        for i in range(1, len(counts)):
            prev_count = counts[i - 1]
            curr_count = counts[i]

            if prev_count > 0:
                growth_rate = (curr_count - prev_count) / prev_count
            elif curr_count > 0:
                growth_rate = 1.0  # New topic
            else:
                growth_rate = 0.0

            growth_rates.append(growth_rate)

        # Calculate velocity (change in growth rate)
        velocity = self._calculate_velocity(growth_rates)

        # Classify lifecycle stage
        current_count = counts[-1]
        current_growth = growth_rates[-1] if growth_rates else 0.0
        stage = self._classify_stage(current_count, current_growth, velocity, growth_rates)

        # Determine trend direction
        if len(growth_rates) >= 2:
            recent_trend = sum(growth_rates[-2:]) / 2
        else:
            recent_trend = growth_rates[0] if growth_rates else 0.0

        if recent_trend > 0.15:
            trend_direction = 'up'
        elif recent_trend < -0.15:
            trend_direction = 'down'
        else:
            trend_direction = 'stable'

        return {
            'topic_id': topic_id,
            'counts': counts,
            'growth_rates': growth_rates,
            'velocity': velocity,
            'stage': stage,
            'trend_direction': trend_direction,
            'current_count': current_count,
            'average_growth': sum(growth_rates) / len(growth_rates) if growth_rates else 0.0
        }

    def _calculate_velocity(self, growth_rates: List[float]) -> float:
        """
        Calculate velocity (rate of change of growth rate).

        Velocity is the derivative of growth rate, indicating acceleration/deceleration.

        Args:
            growth_rates: List of growth rates

        Returns:
            Velocity value
        """
        if len(growth_rates) < 2:
            return 0.0

        # Calculate differences between consecutive growth rates
        deltas = [growth_rates[i] - growth_rates[i - 1] for i in range(1, len(growth_rates))]

        # Average velocity
        velocity = sum(deltas) / len(deltas)

        return velocity

    def _classify_stage(
        self,
        current_count: int,
        current_growth: float,
        velocity: float,
        growth_rates: List[float]
    ) -> str:
        """
        Classify lifecycle stage based on metrics.

        Args:
            current_count: Current period count
            current_growth: Most recent growth rate
            velocity: Growth rate velocity
            growth_rates: Historical growth rates

        Returns:
            Stage name: 'emerging', 'growing', 'peak', 'declining', 'stable'
        """
        # No activity
        if current_count == 0:
            return 'dormant'

        # Very low activity
        if current_count < 3:
            if current_growth > 0:
                return 'emerging'
            else:
                return 'stable'

        # Emerging: new topic with strong initial growth
        if len(growth_rates) <= 2 and current_growth > 0.5 and velocity > 0.2:
            return 'emerging'

        # Declining: consistent negative growth
        if current_growth < -0.2 and velocity <= 0:
            return 'declining'

        # Growing: positive growth with acceleration
        if current_growth > 0.3 and velocity > 0:
            return 'growing'

        # Peak: high activity but slowing
        if current_count >= 10 and current_growth > 0 and velocity < -0.1:
            return 'peak'

        # Peak: very high activity even if growth is slowing
        if current_count >= 20 and current_growth > -0.1:
            return 'peak'

        # Stable: low variance
        if abs(current_growth) < 0.2:
            return 'stable'

        # Default: classify by current growth
        if current_growth > 0.2:
            return 'growing'
        elif current_growth < -0.2:
            return 'declining'
        else:
            return 'stable'

    def get_stage_emoji(self, stage: str) -> str:
        """
        Get emoji representation for a lifecycle stage.

        Args:
            stage: Stage name

        Returns:
            Emoji string
        """
        stage_emojis = {
            'emerging': '🌱',
            'growing': '📈',
            'peak': '⭐',
            'declining': '📉',
            'stable': '➡️',
            'dormant': '💤'
        }
        return stage_emojis.get(stage, '❓')

    def batch_analyze(
        self,
        topic_ids: List[int],
        periods: List[Tuple[datetime, datetime]],
        use_weighted_counts: bool = False
    ) -> Dict[int, Dict]:
        """
        Analyze lifecycle for multiple topics.

        Args:
            topic_ids: List of topic IDs
            periods: List of period tuples
            use_weighted_counts: Whether to use weighted counts

        Returns:
            Dict mapping topic_id to lifecycle analysis
        """
        results = {}

        for topic_id in topic_ids:
            try:
                analysis = self.analyze_lifecycle(topic_id, periods, use_weighted_counts)
                if analysis:
                    results[topic_id] = analysis
            except Exception as e:
                logger.warning(f"Failed to analyze lifecycle for topic {topic_id}: {e}")

        return results

    def get_lifecycle_summary(
        self,
        analyses: Dict[int, Dict]
    ) -> Dict[str, List[int]]:
        """
        Group topics by lifecycle stage.

        Args:
            analyses: Dict of topic analyses from batch_analyze()

        Returns:
            Dict mapping stage to list of topic_ids
        """
        summary = {
            'emerging': [],
            'growing': [],
            'peak': [],
            'declining': [],
            'stable': [],
            'dormant': []
        }

        for topic_id, analysis in analyses.items():
            stage = analysis.get('stage', 'stable')
            if stage in summary:
                summary[stage].append(topic_id)

        return summary

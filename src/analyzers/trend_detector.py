import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from loguru import logger

from ..storage.database import Database
from ..config import settings


class TrendDetector:
    def __init__(self, database: Database):
        self.db = database

    def calculate_trends(
        self,
        window_days: int = 30,
        min_count: int = 3,
        min_growth_rate: float = 0.2
    ) -> List[Dict]:
        """
        Calculate trends based on keyword frequency changes.

        Method:
        1. Get keyword counts from current period (last window_days)
        2. Get keyword counts from previous period (previous window_days)
        3. Calculate growth rate: (current - previous) / previous
        4. Mark as trending if growth_rate > min_growth_rate

        Args:
            window_days: Size of the analysis window in days
            min_count: Minimum occurrences in current period to be considered
            min_growth_rate: Minimum growth rate to be marked as trending (0.2 = 20%)

        Returns:
            List of trend dictionaries
        """
        logger.info(f"Calculating trends for {window_days}-day window")

        now = datetime.utcnow()
        current_end = now
        current_start = now - timedelta(days=window_days)
        previous_end = current_start
        previous_start = current_start - timedelta(days=window_days)

        # Get keyword counts for both periods
        current_counts = self.db.get_keyword_counts(current_start, current_end)
        previous_counts = self.db.get_keyword_counts(previous_start, previous_end)

        logger.debug(f"Current period keywords: {len(current_counts)}")
        logger.debug(f"Previous period keywords: {len(previous_counts)}")

        trends = []

        for keyword, current_count in current_counts.items():
            # Skip if below minimum count
            if current_count < min_count:
                continue

            previous_count = previous_counts.get(keyword, 0)

            # Calculate growth rate
            if previous_count > 0:
                growth_rate = (current_count - previous_count) / previous_count
            else:
                # New keyword (didn't exist before)
                growth_rate = 1.0

            is_trending = growth_rate >= min_growth_rate

            trend = {
                'keyword': keyword,
                'count': current_count,
                'previous_count': previous_count,
                'growth_rate': growth_rate,
                'is_trending': is_trending,
                'period_start': current_start,
                'period_end': current_end
            }

            trends.append(trend)

        # Sort by growth rate (descending)
        trends.sort(key=lambda x: x['growth_rate'], reverse=True)

        logger.info(f"Found {len(trends)} keywords with activity")
        trending_count = sum(1 for t in trends if t['is_trending'])
        logger.info(f"Marked {trending_count} as trending (growth >= {min_growth_rate:.0%})")

        return trends

    def get_emerging_keywords(
        self,
        window_days: int = 30,
        top_n: int = 20
    ) -> List[Dict]:
        """
        Get keywords that are completely new in the current period.

        Args:
            window_days: Size of the analysis window
            top_n: Number of top emerging keywords

        Returns:
            List of emerging keywords
        """
        logger.info(f"Finding emerging keywords (new in last {window_days} days)")

        now = datetime.utcnow()
        current_end = now
        current_start = now - timedelta(days=window_days)
        previous_end = current_start
        previous_start = current_start - timedelta(days=window_days * 2)

        current_counts = self.db.get_keyword_counts(current_start, current_end)
        previous_counts = self.db.get_keyword_counts(previous_start, previous_end)

        # Find keywords that exist now but didn't exist before
        emerging = []

        for keyword, count in current_counts.items():
            if keyword not in previous_counts:
                emerging.append({
                    'keyword': keyword,
                    'count': count,
                    'first_seen': current_start
                })

        # Sort by count
        emerging.sort(key=lambda x: x['count'], reverse=True)

        logger.info(f"Found {len(emerging)} emerging keywords")

        return emerging[:top_n]

    def get_declining_keywords(
        self,
        window_days: int = 30,
        min_decline_rate: float = -0.3,
        top_n: int = 20
    ) -> List[Dict]:
        """
        Get keywords that are declining in frequency.

        Args:
            window_days: Size of the analysis window
            min_decline_rate: Minimum decline rate to be considered (e.g., -0.3 = -30%)
            top_n: Number of top declining keywords

        Returns:
            List of declining keywords
        """
        logger.info(f"Finding declining keywords (decline > {min_decline_rate:.0%})")

        trends = self.calculate_trends(window_days, min_count=1, min_growth_rate=-1.0)

        # Filter for declining keywords
        declining = [
            t for t in trends
            if t['growth_rate'] < 0 and t['growth_rate'] <= min_decline_rate
        ]

        # Sort by decline rate (most negative first)
        declining.sort(key=lambda x: x['growth_rate'])

        logger.info(f"Found {len(declining)} declining keywords")

        return declining[:top_n]

    def get_trending_summary(
        self,
        window_days: int = 30
    ) -> Dict:
        """
        Get a comprehensive summary of trends.

        Returns:
            Dictionary with trending statistics
        """
        logger.info("Generating trending summary")

        trends = self.calculate_trends(window_days)

        trending = [t for t in trends if t['is_trending']]
        declining = [t for t in trends if t['growth_rate'] < -0.2]
        stable = [t for t in trends if -0.2 <= t['growth_rate'] < 0.2]

        summary = {
            'period_days': window_days,
            'total_keywords': len(trends),
            'trending_count': len(trending),
            'declining_count': len(declining),
            'stable_count': len(stable),
            'top_trending': trending[:10] if trending else [],
            'top_declining': sorted(declining, key=lambda x: x['growth_rate'])[:10] if declining else [],
            'generated_at': datetime.utcnow()
        }

        return summary

    def compare_periods(
        self,
        period1_start: datetime,
        period1_end: datetime,
        period2_start: datetime,
        period2_end: datetime
    ) -> pd.DataFrame:
        """
        Compare keyword frequencies between two time periods.

        Args:
            period1_start: Start of first period
            period1_end: End of first period
            period2_start: Start of second period
            period2_end: End of second period

        Returns:
            DataFrame with comparison
        """
        logger.info("Comparing two time periods")

        counts1 = self.db.get_keyword_counts(period1_start, period1_end)
        counts2 = self.db.get_keyword_counts(period2_start, period2_end)

        # Get all unique keywords
        all_keywords = set(counts1.keys()) | set(counts2.keys())

        data = []
        for keyword in all_keywords:
            count1 = counts1.get(keyword, 0)
            count2 = counts2.get(keyword, 0)

            if count1 > 0:
                change = (count2 - count1) / count1
            else:
                change = 1.0 if count2 > 0 else 0.0

            data.append({
                'keyword': keyword,
                'period1_count': count1,
                'period2_count': count2,
                'change': change,
                'change_pct': change * 100
            })

        df = pd.DataFrame(data)
        df = df.sort_values('change', ascending=False)

        return df

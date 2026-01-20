"""
Trend Summarizer - Formats topic trends for email/Slack delivery.
"""

from typing import List, Dict
from datetime import datetime
from loguru import logger


class TrendSummarizer:
    """
    Formats trending topics into human-readable summaries for
    email newsletters or Slack notifications.
    """

    def __init__(self):
        pass

    def format_for_email(
        self,
        trends: List[Dict],
        max_trends: int = 10,
        period_days: int = 30
    ) -> str:
        """
        Format trends as HTML email content.

        Args:
            trends: List of trend dictionaries from TrendDetector
            max_trends: Maximum number of trends to include
            period_days: Analysis period in days

        Returns:
            HTML formatted email content
        """
        if not trends:
            return "<p>No significant trends detected in this period.</p>"

        # Filter for trending and new topics only
        significant_trends = [
            t for t in trends
            if t.get('is_trending') or t.get('is_new')
        ][:max_trends]

        if not significant_trends:
            return "<p>No significant trends detected in this period.</p>"

        # Build HTML
        html = f"""
<h2>🔥 Marketing & AI Trends ({period_days} days)</h2>
<p><em>Generated on {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}</em></p>

<table style="width: 100%; border-collapse: collapse; margin-top: 20px;">
    <thead>
        <tr style="background-color: #f2f2f2;">
            <th style="padding: 12px; text-align: left; border: 1px solid #ddd;">Trend</th>
            <th style="padding: 12px; text-align: left; border: 1px solid #ddd;">Key Terms</th>
            <th style="padding: 12px; text-align: center; border: 1px solid #ddd;">Articles</th>
            <th style="padding: 12px; text-align: center; border: 1px solid #ddd;">Growth</th>
            <th style="padding: 12px; text-align: center; border: 1px solid #ddd;">Status</th>
        </tr>
    </thead>
    <tbody>
"""

        for i, trend in enumerate(significant_trends):
            # Alternate row colors
            bg_color = "#ffffff" if i % 2 == 0 else "#f9f9f9"

            topic_name = trend.get('topic_name', trend.get('keyword', 'Unknown'))
            top_words = trend.get('top_words', [])
            count = trend.get('count', 0)
            growth_rate = trend.get('growth_rate', 0)
            status = trend.get('status', '➡️ Stabilne')

            # Format top words
            words_str = ", ".join(top_words[:5]) if top_words else "N/A"

            # Format growth rate
            if growth_rate >= 1.0:
                growth_str = "NEW"
                growth_color = "#4CAF50"
            elif growth_rate > 0:
                growth_str = f"+{growth_rate:.0%}"
                growth_color = "#2196F3"
            else:
                growth_str = f"{growth_rate:.0%}"
                growth_color = "#F44336"

            html += f"""
        <tr style="background-color: {bg_color};">
            <td style="padding: 12px; border: 1px solid #ddd;"><strong>{topic_name}</strong></td>
            <td style="padding: 12px; border: 1px solid #ddd; font-size: 0.9em; color: #666;">{words_str}</td>
            <td style="padding: 12px; border: 1px solid #ddd; text-align: center;">{count}</td>
            <td style="padding: 12px; border: 1px solid #ddd; text-align: center; color: {growth_color}; font-weight: bold;">{growth_str}</td>
            <td style="padding: 12px; border: 1px solid #ddd; text-align: center;">{status}</td>
        </tr>
"""

        html += """
    </tbody>
</table>

<p style="margin-top: 30px; font-size: 0.9em; color: #666;">
    <em>Trends are detected using semantic topic modeling with BERTopic. Growth rates compare the last {period_days} days with the previous {period_days} days.</em>
</p>
""".format(period_days=period_days)

        return html

    def format_for_slack(
        self,
        trends: List[Dict],
        max_trends: int = 5,
        period_days: int = 30
    ) -> str:
        """
        Format trends as Slack message (markdown).

        Args:
            trends: List of trend dictionaries from TrendDetector
            max_trends: Maximum number of trends to include
            period_days: Analysis period in days

        Returns:
            Slack-formatted markdown
        """
        if not trends:
            return "No significant trends detected in this period."

        # Filter for trending and new topics only
        significant_trends = [
            t for t in trends
            if t.get('is_trending') or t.get('is_new')
        ][:max_trends]

        if not significant_trends:
            return "No significant trends detected in this period."

        # Build message
        message = f"*🔥 Marketing & AI Trends ({period_days} days)*\n\n"

        for i, trend in enumerate(significant_trends, 1):
            topic_name = trend.get('topic_name', trend.get('keyword', 'Unknown'))
            top_words = trend.get('top_words', [])
            count = trend.get('count', 0)
            growth_rate = trend.get('growth_rate', 0)
            status = trend.get('status', '➡️ Stabilne')

            # Format top words
            words_str = ", ".join(top_words[:3]) if top_words else "N/A"

            # Format growth rate
            if growth_rate >= 1.0:
                growth_str = "*NEW*"
            elif growth_rate > 0:
                growth_str = f"+{growth_rate:.0%}"
            else:
                growth_str = f"{growth_rate:.0%}"

            message += f"{i}. *{topic_name}* {status}\n"
            message += f"   • Keywords: _{words_str}_\n"
            message += f"   • {count} articles | Growth: {growth_str}\n\n"

        message += f"\n_Generated on {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}_"

        return message

    def format_for_console(
        self,
        trends: List[Dict],
        max_trends: int = 20,
        period_days: int = 30
    ) -> str:
        """
        Format trends for console/terminal output.

        Args:
            trends: List of trend dictionaries from TrendDetector
            max_trends: Maximum number of trends to include
            period_days: Analysis period in days

        Returns:
            Formatted console output
        """
        if not trends:
            return "No significant trends detected in this period."

        # Filter for trending and new topics only
        significant_trends = [
            t for t in trends
            if t.get('is_trending') or t.get('is_new')
        ][:max_trends]

        if not significant_trends:
            return "No significant trends detected in this period."

        # Build output
        output = f"\n{'='*80}\n"
        output += f"🔥 MARKETING & AI TRENDS ({period_days} days)\n"
        output += f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}\n"
        output += f"{'='*80}\n\n"

        for i, trend in enumerate(significant_trends, 1):
            topic_name = trend.get('topic_name', trend.get('keyword', 'Unknown'))
            top_words = trend.get('top_words', [])
            count = trend.get('count', 0)
            prev_count = trend.get('previous_count', 0)
            growth_rate = trend.get('growth_rate', 0)
            status = trend.get('status', '➡️ Stabilne')

            # Format top words
            words_str = ", ".join(top_words[:5]) if top_words else "N/A"

            # Format growth rate
            if growth_rate >= 1.0:
                growth_str = "NEW"
            elif growth_rate > 0:
                growth_str = f"+{growth_rate:.0%}"
            else:
                growth_str = f"{growth_rate:.0%}"

            output += f"{i}. {status} {topic_name}\n"
            output += f"   Keywords: {words_str}\n"
            output += f"   Articles: {count} (previous: {prev_count}) | Growth: {growth_str}\n"
            output += f"   {'-'*76}\n\n"

        return output

    def generate_summary_dict(
        self,
        trends: List[Dict],
        period_days: int = 30
    ) -> Dict:
        """
        Generate a structured summary dictionary (for API/JSON export).

        Args:
            trends: List of trend dictionaries from TrendDetector
            period_days: Analysis period in days

        Returns:
            Dictionary with summary data
        """
        if not trends:
            return {
                'generated_at': datetime.now().isoformat(),
                'period_days': period_days,
                'total_trends': 0,
                'trending': [],
                'new': [],
                'stable': []
            }

        trending = [t for t in trends if t.get('is_trending') and not t.get('is_new')]
        new = [t for t in trends if t.get('is_new')]
        stable = [t for t in trends if not t.get('is_trending') and not t.get('is_new')]

        return {
            'generated_at': datetime.now().isoformat(),
            'period_days': period_days,
            'total_trends': len(trends),
            'trending_count': len(trending),
            'new_count': len(new),
            'stable_count': len(stable),
            'trending': trending[:10],
            'new': new[:10],
            'stable': stable[:10]
        }


def format_trends_for_output(
    trends: List[Dict],
    output_format: str = 'console',
    max_trends: int = 10,
    period_days: int = 30
) -> str:
    """
    Convenience function to format trends in the specified format.

    Args:
        trends: List of trend dictionaries
        output_format: 'console', 'email', 'slack', or 'json'
        max_trends: Maximum number of trends to include
        period_days: Analysis period in days

    Returns:
        Formatted output string
    """
    summarizer = TrendSummarizer()

    if output_format == 'email':
        return summarizer.format_for_email(trends, max_trends, period_days)
    elif output_format == 'slack':
        return summarizer.format_for_slack(trends, max_trends, period_days)
    elif output_format == 'json':
        import json
        summary = summarizer.generate_summary_dict(trends, period_days)
        return json.dumps(summary, indent=2, default=str)
    else:  # console
        return summarizer.format_for_console(trends, max_trends, period_days)

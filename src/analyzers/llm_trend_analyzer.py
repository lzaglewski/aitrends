"""
LLM Trend Analyzer - Uses LLM to understand context and name trends intelligently.
"""

from typing import List, Dict, Optional
from openai import OpenAI
from loguru import logger
import json
import os

from ..config import settings


class LLMTrendAnalyzer:
    """
    Analyzes clustered articles using LLM to:
    1. Determine if cluster represents a real trend
    2. Generate meaningful trend names
    3. Extract relevant keywords
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize LLM analyzer.

        Args:
            api_key: OpenAI API key (if None, reads from env/config)
        """
        self.api_key = api_key or settings.OPENAI_API_KEY or os.getenv("OPENAI_API_KEY")

        if not self.api_key:
            logger.warning("No OpenAI API key provided. LLM enhancement will be disabled.")
            self.client = None
        else:
            self.client = OpenAI(api_key=self.api_key)
            logger.info(f"LLM Trend Analyzer initialized with model: {settings.LLM_MODEL}")

    def analyze_topic_cluster(
        self,
        topic_id: int,
        articles: List[Dict],
        bert_topic_words: List[str]
    ) -> Optional[Dict]:
        """
        Analyze a cluster of articles to determine if it's a trend.

        Args:
            topic_id: BERTopic topic ID
            articles: List of article dicts with 'title' and 'content'
            bert_topic_words: Top words from BERTopic for this cluster

        Returns:
            Dict with trend info or None if not a trend
        """
        if not self.client:
            logger.warning("LLM client not initialized, skipping analysis")
            return None

        if not articles:
            return None

        # Limit number of articles to analyze (cost control)
        sample_articles = articles[:settings.LLM_MAX_ARTICLES_PER_TOPIC]

        # Build prompt
        prompt = self._build_analysis_prompt(sample_articles, bert_topic_words)

        try:
            logger.debug(f"Analyzing topic {topic_id} with {len(sample_articles)} articles")

            # Log the full prompt being sent to LLM
            logger.debug("=" * 80)
            logger.debug(f"LLM PROMPT for Topic {topic_id}:")
            logger.debug("-" * 80)
            logger.debug(prompt)
            logger.debug("=" * 80)

            response = self.client.chat.completions.create(
                model=settings.LLM_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": """You are an expert marketing and AI industry analyst.
Your job is to identify emerging TRENDS (patterns, shifts, or movements in the industry),
not just news about individual companies or events.

A TREND is a broader pattern seen across multiple organizations or contexts.
NEWS is a single event or announcement from one company."""
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=settings.LLM_TEMPERATURE,
                max_tokens=settings.LLM_MAX_TOKENS,
                response_format={"type": "json_object"}
            )

            result = response.choices[0].message.content
            parsed = json.loads(result)

            # Log the full LLM response
            logger.debug("=" * 80)
            logger.debug(f"LLM RESPONSE for Topic {topic_id}:")
            logger.debug("-" * 80)
            logger.debug(json.dumps(parsed, indent=2, ensure_ascii=False))
            logger.debug("=" * 80)

            # Check if it's a trend
            if parsed.get("is_trend", False):
                return {
                    "topic_id": topic_id,
                    "trend_name": parsed.get("trend_name", "Unknown Trend"),
                    "description": parsed.get("description", ""),
                    "keywords": parsed.get("keywords", []),
                    "confidence": parsed.get("confidence", 0.5),
                    "bert_words": bert_topic_words
                }
            else:
                logger.info(f"Topic {topic_id} identified as NOT A TREND: {parsed.get('reason', 'No reason given')}")
                return None

        except Exception as e:
            logger.error(f"Error analyzing topic {topic_id} with LLM: {e}")
            return None

    def _build_analysis_prompt(
        self,
        articles: List[Dict],
        bert_words: List[str]
    ) -> str:
        """
        Build the prompt for LLM analysis.

        Args:
            articles: List of article dicts
            bert_words: Top words from BERTopic

        Returns:
            Formatted prompt string
        """
        # Build articles summary
        articles_text = ""
        for i, article in enumerate(articles, 1):
            title = article.get('title', 'No title')
            content = article.get('content', '')

            # Take first 200 characters of content
            snippet = content[:200] + "..." if len(content) > 200 else content

            articles_text += f"{i}. **{title}**\n   {snippet}\n\n"

        # BERTopic keywords
        bert_keywords_str = ", ".join(bert_words) if bert_words else "None"

        prompt = f"""Analyze these {len(articles)} marketing/AI industry articles that were clustered together:

{articles_text}

**BERTopic Keywords**: {bert_keywords_str}

**Task**: Determine if these articles represent an emerging TREND in marketing or AI.

**Instructions**:
1. If they represent a TREND (a pattern/shift seen across multiple contexts):
   - Provide a concise trend name (3-6 words, e.g., "AI-Generated Content in Advertising")
   - Brief description (1-2 sentences explaining the trend)
   - 3-5 relevant keywords
   - Confidence score (0.0-1.0)

2. If they're just NEWS (single company announcements, isolated events):
   - Mark as not a trend
   - Explain why

**Output Format** (JSON):
{{
  "is_trend": true/false,
  "trend_name": "Concise Trend Name" (if is_trend=true),
  "description": "Brief explanation" (if is_trend=true),
  "keywords": ["keyword1", "keyword2", ...] (if is_trend=true),
  "confidence": 0.0-1.0 (if is_trend=true),
  "reason": "Why not a trend" (if is_trend=false)
}}
"""

        return prompt

    def batch_analyze_topics(
        self,
        topics_data: Dict[int, Dict]
    ) -> Dict[int, Optional[Dict]]:
        """
        Analyze multiple topics in batch.

        Args:
            topics_data: Dict mapping topic_id to {
                'articles': List[Dict],
                'bert_words': List[str]
            }

        Returns:
            Dict mapping topic_id to trend info (or None if not a trend)
        """
        results = {}

        for topic_id, data in topics_data.items():
            articles = data.get('articles', [])
            bert_words = data.get('bert_words', [])

            result = self.analyze_topic_cluster(topic_id, articles, bert_words)
            results[topic_id] = result

        # Log summary
        trend_count = sum(1 for r in results.values() if r is not None)
        logger.info(f"LLM Analysis: {trend_count}/{len(topics_data)} topics identified as trends")

        return results


def enhance_topics_with_llm(
    topic_info: Dict[int, Dict],
    articles_by_topic: Dict[int, List[Dict]]
) -> Dict[int, Dict]:
    """
    Convenience function to enhance BERTopic results with LLM analysis.

    Args:
        topic_info: Topic metadata from BERTopic
        articles_by_topic: Articles grouped by topic_id

    Returns:
        Enhanced topic info with LLM-generated names and filtering
    """
    if not settings.USE_LLM_ENHANCEMENT:
        logger.info("LLM enhancement disabled in config")
        return topic_info

    analyzer = LLMTrendAnalyzer()

    if not analyzer.client:
        logger.warning("LLM client not available, returning original topics")
        return topic_info

    # Prepare data for batch analysis
    topics_data = {}
    for topic_id, info in topic_info.items():
        if topic_id in articles_by_topic:
            topics_data[topic_id] = {
                'articles': articles_by_topic[topic_id],
                'bert_words': info.get('top_words', [])
            }

    # Analyze with LLM
    llm_results = analyzer.batch_analyze_topics(topics_data)

    # Update topic info with LLM results
    enhanced_topics = {}
    for topic_id, info in topic_info.items():
        llm_result = llm_results.get(topic_id)

        if llm_result:
            # This topic is a real trend - enhance it
            enhanced_topics[topic_id] = {
                **info,  # Keep original BERTopic metadata
                'name': llm_result['trend_name'],  # Override name with LLM
                'description': llm_result['description'],
                'top_words': llm_result['keywords'],  # Use LLM keywords
                'llm_confidence': llm_result['confidence'],
                'llm_enhanced': True
            }
            logger.info(f"Enhanced topic {topic_id}: {llm_result['trend_name']}")
        else:
            # Not a trend - skip this topic
            logger.debug(f"Filtered out topic {topic_id} (not a trend)")

    logger.info(f"LLM Enhancement: {len(enhanced_topics)}/{len(topic_info)} topics retained")

    return enhanced_topics

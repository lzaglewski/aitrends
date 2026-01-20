"""
Semantic clustering and named entity filtering.
"""

from typing import List, Set, Tuple
from loguru import logger
import re


class NamedEntityFilter:
    """
    Filters out named entities (companies, people, products) from topics.

    This prevents topics like "Google" or "CEO John Doe" and focuses on
    thematic concepts like "AI Marketing Automation".
    """

    def __init__(self):
        """Initialize the named entity filter with blacklists."""
        self.company_blacklist = self._load_company_blacklist()
        self.person_patterns = self._load_person_patterns()

    def _load_company_blacklist(self) -> Set[str]:
        """
        Load common company/brand names to filter out.

        Returns:
            Set of company names (lowercase)
        """
        companies = {
            # Tech companies
            'google', 'facebook', 'meta', 'microsoft', 'apple', 'amazon',
            'openai', 'anthropic', 'netflix', 'twitter', 'x', 'linkedin',
            'instagram', 'tiktok', 'snapchat', 'youtube', 'tesla',

            # Marketing/Ad tech
            'publicis', 'wpp', 'omnicom', 'dentsu', 'havas', 'interpublic',
            'adweek', 'adage', 'marketing week', 'digiday',
            'salesforce', 'hubspot', 'adobe', 'oracle',

            # Products
            'chatgpt', 'gemini', 'claude', 'gpt-4', 'copilot',
            'search console', 'google analytics', 'facebook ads',

            # Polish companies
            'allegro', 'onet', 'wp', 'interia', 'gazeta', 'tvn',
            'polsat', 'orange', 'play', 't-mobile', 'plus',

            # General
            'inc', 'corp', 'ltd', 'llc', 'gmbh', 'sa', 'sp'
        }

        return companies

    def _load_person_patterns(self) -> List[str]:
        """
        Load regex patterns that match person names.

        Returns:
            List of regex patterns
        """
        patterns = [
            # CEO/CTO/etc Title patterns
            r'\b(ceo|cto|cfo|cmo|coo|vp|director|president|founder)\s+\w+',
            r'\w+\s+(ceo|cto|cfo|cmo|coo|vp|director|president|founder)',

            # Name with title patterns (Mr., Dr., Prof.)
            r'\b(mr|mrs|ms|dr|prof|sir)\.\s+\w+',

            # Initials (J. Smith, John D. Smith)
            r'\b\w\.\s+\w+',
            r'\b\w+\s+\w\.\s+\w+',
        ]

        return patterns

    def is_named_entity(self, text: str) -> bool:
        """
        Check if text is likely a named entity (company/person/product).

        Args:
            text: Text to check

        Returns:
            True if likely a named entity, False otherwise
        """
        text_lower = text.lower().strip()

        # Check company blacklist
        for company in self.company_blacklist:
            if company in text_lower:
                return True

        # Check person patterns
        for pattern in self.person_patterns:
            if re.search(pattern, text_lower):
                return True

        # Check for all-caps acronyms (likely company/product names)
        words = text.split()
        for word in words:
            if len(word) > 1 and word.isupper() and not word in ['AI', 'ML', 'AR', 'VR', 'SEO', 'SEM', 'ROI', 'KPI']:
                return True

        # Check for patterns like "X announced", "Y launches", etc.
        announcement_patterns = [
            r'\w+\s+(announced|launches|reveals|introduces|unveils)',
            r'(according to|says|reports)\s+\w+',
        ]
        for pattern in announcement_patterns:
            if re.search(pattern, text_lower):
                return True

        return False

    def filter_topics(
        self,
        topics: List[Tuple[str, float]]
    ) -> List[Tuple[str, float]]:
        """
        Filter out named entities from a list of topics.

        Args:
            topics: List of (topic_name, score) tuples

        Returns:
            Filtered list of topics
        """
        filtered = []

        for topic_name, score in topics:
            if not self.is_named_entity(topic_name):
                filtered.append((topic_name, score))
            else:
                logger.debug(f"Filtered out named entity: {topic_name}")

        logger.info(f"Filtered {len(topics) - len(filtered)} named entities from topics")

        return filtered


class ConceptNormalizer:
    """
    Normalizes and merges similar concepts.

    For example:
    - "AI Marketing" + "Artificial Intelligence Marketing" → "AI Marketing"
    - "Marketing Automation" + "Automated Marketing" → "Marketing Automation"
    """

    def __init__(self):
        """Initialize the concept normalizer."""
        self.synonyms = self._load_synonyms()

    def _load_synonyms(self) -> dict:
        """
        Load synonym mappings for common marketing/AI terms.

        Returns:
            Dictionary mapping variants to canonical forms
        """
        synonyms = {
            # AI terms
            'artificial intelligence': 'ai',
            'machine learning': 'ml',
            'generative ai': 'ai',
            'gen ai': 'ai',
            'llm': 'ai',
            'large language model': 'ai',

            # Marketing terms
            'digital marketing': 'marketing',
            'online marketing': 'marketing',
            'internet marketing': 'marketing',
            'performance marketing': 'marketing',

            # Automation
            'automated': 'automation',
            'automatic': 'automation',

            # Advertising
            'advertisement': 'advertising',
            'advertisements': 'advertising',
            'ad': 'advertising',
            'ads': 'advertising',

            # Content
            'content creation': 'content',
            'content generation': 'content',

            # Personalization
            'personalisation': 'personalization',
            'customization': 'personalization',
            'customisation': 'personalization',

            # Data/Analytics
            'data analysis': 'analytics',
            'data analytics': 'analytics',
            'business intelligence': 'analytics',
        }

        return synonyms

    def normalize_concept(self, concept: str) -> str:
        """
        Normalize a concept to its canonical form.

        Args:
            concept: Original concept text

        Returns:
            Normalized concept
        """
        concept_lower = concept.lower().strip()

        # Apply synonym mappings
        for variant, canonical in self.synonyms.items():
            concept_lower = concept_lower.replace(variant, canonical)

        # Remove extra whitespace
        concept_lower = re.sub(r'\s+', ' ', concept_lower).strip()

        # Capitalize first letter of each word
        words = concept_lower.split()
        normalized = ' '.join(word.capitalize() for word in words)

        return normalized

    def merge_similar_topics(
        self,
        topics: List[Tuple[str, float]]
    ) -> List[Tuple[str, float]]:
        """
        Merge topics that are similar after normalization.

        Args:
            topics: List of (topic_name, score) tuples

        Returns:
            Merged list of topics with aggregated scores
        """
        # Normalize and group
        normalized_groups = {}

        for topic_name, score in topics:
            normalized = self.normalize_concept(topic_name)

            if normalized in normalized_groups:
                # Average the scores
                old_score = normalized_groups[normalized]
                normalized_groups[normalized] = (old_score + score) / 2
            else:
                normalized_groups[normalized] = score

        # Convert back to list
        merged = [(name, score) for name, score in normalized_groups.items()]

        # Sort by score
        merged.sort(key=lambda x: x[1], reverse=True)

        logger.info(f"Merged {len(topics)} topics into {len(merged)} unique concepts")

        return merged


def filter_and_normalize_topics(
    topics: List[Tuple[str, float]]
) -> List[Tuple[str, float]]:
    """
    Apply both filtering and normalization to topics.

    Args:
        topics: List of (topic_name, score) tuples

    Returns:
        Filtered and normalized topics
    """
    # Filter named entities
    entity_filter = NamedEntityFilter()
    filtered = entity_filter.filter_topics(topics)

    # Normalize and merge similar concepts
    normalizer = ConceptNormalizer()
    normalized = normalizer.merge_similar_topics(filtered)

    return normalized

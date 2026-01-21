"""
Source credibility weight manager.

Manages source credibility weights from YAML configuration to influence
trend detection and prioritize high-quality sources.
"""

from typing import Dict, List, Optional
import yaml
from loguru import logger
from urllib.parse import urlparse


class SourceWeightManager:
    """
    Manages source credibility weights for trend detection.

    Weights are loaded from YAML configuration and applied based on domain matching.
    Higher weights indicate more credible/authoritative sources.
    """

    def __init__(self, config_path: str = "data/source_weights.yaml"):
        """
        Initialize the weight manager.

        Args:
            config_path: Path to source weights YAML file
        """
        self.config_path = config_path
        self.default_weight = 1.0
        self.weight_map = {}  # Domain -> weight
        self.blacklist = set()
        self._load_weights()

    def _load_weights(self) -> Dict[str, float]:
        """
        Load weights from YAML configuration.

        Returns:
            Dict mapping domain to weight
        """
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)

            if not config:
                logger.warning(f"Empty source weights config at {self.config_path}")
                return {}

            # Load default weight
            self.default_weight = config.get('default_weight', 1.0)

            # Load weight categories
            categories = [
                'high_credibility',
                'medium_credibility',
                'low_credibility',
                'blacklist'
            ]

            for category in categories:
                if category not in config:
                    continue

                category_data = config[category]

                # Extract weight and domains
                if isinstance(category_data, dict):
                    domains = category_data.get('domains', category_data.keys())
                    weight = category_data.get('weight', 1.0)

                    # Handle old format where domains are at root level
                    domain_list = []
                    for key, value in category_data.items():
                        if key not in ['weight', 'domains']:
                            if isinstance(value, str):
                                domain_list.append(value)
                            elif value is None:
                                domain_list.append(key)

                    if not domain_list and isinstance(domains, list):
                        domain_list = domains

                elif isinstance(category_data, list):
                    # Simple list format
                    domain_list = category_data
                    weight = 1.5 if category == 'high_credibility' else 1.0
                    weight = 0.5 if category == 'low_credibility' else weight
                    weight = 0.0 if category == 'blacklist' else weight
                else:
                    continue

                # Store weights
                for domain in domain_list:
                    if weight == 0:
                        self.blacklist.add(domain.lower())
                    else:
                        self.weight_map[domain.lower()] = weight

            # Check if we loaded from new format with explicit weights
            for category_key in config:
                if isinstance(config[category_key], dict) and 'weight' in config[category_key]:
                    weight = config[category_key]['weight']
                    domains = [k for k in config[category_key].keys() if k != 'weight']

                    for domain in domains:
                        if weight == 0:
                            self.blacklist.add(domain.lower())
                        else:
                            self.weight_map[domain.lower()] = weight

            logger.info(
                f"Loaded source weights: {len(self.weight_map)} weighted sources, "
                f"{len(self.blacklist)} blacklisted"
            )

            return self.weight_map

        except FileNotFoundError:
            logger.warning(f"Source weights config not found: {self.config_path}, using defaults")
            return {}

        except Exception as e:
            logger.error(f"Error loading source weights: {e}")
            return {}

    def get_weight(self, source_url: str) -> float:
        """
        Get credibility weight for a source URL.

        Args:
            source_url: Source URL

        Returns:
            Credibility weight (0 = blacklisted, >1 = high credibility)
        """
        if not source_url:
            return self.default_weight

        # Extract domain
        domain = self._extract_domain(source_url)

        # Check blacklist
        if self.is_blacklisted(source_url):
            return 0.0

        # Check exact match
        if domain in self.weight_map:
            return self.weight_map[domain]

        # Check partial matches (for subdomains)
        for weighted_domain, weight in self.weight_map.items():
            if weighted_domain in domain or domain in weighted_domain:
                return weight

        # Return default
        return self.default_weight

    def is_blacklisted(self, source_url: str) -> bool:
        """
        Check if a source is blacklisted.

        Args:
            source_url: Source URL

        Returns:
            True if blacklisted
        """
        if not source_url:
            return False

        domain = self._extract_domain(source_url)

        # Check exact match
        if domain in self.blacklist:
            return True

        # Check partial matches
        for blacklisted_domain in self.blacklist:
            if blacklisted_domain in domain or domain in blacklisted_domain:
                return True

        return False

    def _extract_domain(self, url: str) -> str:
        """
        Extract domain from URL.

        Args:
            url: Full URL

        Returns:
            Domain string (lowercase)
        """
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()

            # Remove 'www.' prefix
            if domain.startswith('www.'):
                domain = domain[4:]

            return domain

        except Exception:
            return url.lower()

    def get_weighted_count(self, articles: List[Dict]) -> float:
        """
        Calculate weighted article count.

        Args:
            articles: List of article dicts with 'source_url' or 'url'

        Returns:
            Weighted count (sum of weights)
        """
        if not articles:
            return 0.0

        total_weight = 0.0
        for article in articles:
            url = article.get('source_url') or article.get('url', '')
            weight = self.get_weight(url)
            total_weight += weight

        return total_weight

    def get_all_weights(self) -> Dict[str, float]:
        """
        Get all configured weights.

        Returns:
            Dict mapping domain to weight
        """
        return self.weight_map.copy()

    def get_blacklist(self) -> List[str]:
        """
        Get all blacklisted domains.

        Returns:
            List of blacklisted domains
        """
        return list(self.blacklist)

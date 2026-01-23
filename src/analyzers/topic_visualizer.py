"""
Topic Visualizer - Generates 2D visualization data from topic embeddings.

Reduces 5D UMAP space to 2D for visualization using another UMAP pass.
"""

from typing import List, Dict, Optional, Tuple
import numpy as np
from loguru import logger
from datetime import datetime, timedelta


class TopicVisualizer:
    """
    Generates visualization data for topic clusters.

    Takes embeddings and topic assignments, reduces to 2D,
    and returns data ready for plotting with Plotly.js.
    """

    def __init__(self, db):
        """
        Initialize visualizer with database connection.

        Args:
            db: Database instance
        """
        self.db = db

    def generate_visualization_data(
        self,
        days: int = 60,
        max_articles: int = 500,
        include_outliers: bool = True
    ) -> Dict:
        """
        Generate 2D visualization data for recent articles.

        Args:
            days: Number of days to look back
            max_articles: Maximum articles to visualize
            include_outliers: Whether to include topic -1

        Returns:
            Dictionary with visualization data for Plotly.js
        """
        from ..storage.models import Article, Topic
        from sentence_transformers import SentenceTransformer
        from umap import UMAP
        from sqlalchemy import outerjoin

        logger.info(f"📊 Generating visualization data for last {days} days...")

        try:
            with self.db.get_session() as session:
                # Get recent articles with topic assignments
                cutoff_date = datetime.utcnow() - timedelta(days=days)

                # Query articles with their topics (left join to include articles without topic names)
                query = session.query(
                    Article.id,
                    Article.title,
                    Article.url,
                    Article.cleaned_content,
                    Article.published_date,
                    Article.topic_id,
                    Topic.topic_name
                ).outerjoin(
                    Topic, Article.topic_id == Topic.topic_id
                ).filter(
                    Article.published_date >= cutoff_date,
                    Article.topic_id.isnot(None)  # Must have topic assignment
                )

                if not include_outliers:
                    query = query.filter(Article.topic_id != -1)

                query = query.order_by(Article.published_date.desc()).limit(max_articles)

                results = query.all()

                if not results:
                    logger.warning("No articles with topics found")
                    return self._empty_response()

                logger.info(f"Found {len(results)} articles with topic assignments")

                # Extract data
                articles_data = []
                contents = []

                for row in results:
                    content = row.cleaned_content or row.title
                    if content and len(content) >= 50:
                        articles_data.append({
                            'id': row.id,
                            'title': row.title[:100] + '...' if len(row.title) > 100 else row.title,
                            'url': row.url,
                            'topic_id': row.topic_id,
                            'topic_name': row.topic_name or f'Topic {row.topic_id}',
                            'date': row.published_date.isoformat() if row.published_date else None
                        })
                        contents.append(content[:1000])  # Limit content length for speed

                if len(contents) < 10:
                    logger.warning(f"Not enough articles ({len(contents)}) for meaningful visualization")
                    return self._empty_response()

                # Generate embeddings
                logger.info(f"🧠 Generating embeddings for {len(contents)} articles...")
                embedding_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
                embeddings = embedding_model.encode(contents, show_progress_bar=False)

                # Reduce to 2D with UMAP
                logger.info("📉 Reducing to 2D with UMAP...")
                umap_2d = UMAP(
                    n_neighbors=min(15, len(contents) - 1),
                    n_components=2,
                    min_dist=0.1,
                    metric='cosine',
                    random_state=42
                )

                coords_2d = umap_2d.fit_transform(embeddings)

                # Prepare visualization data
                visualization_data = self._prepare_plotly_data(
                    articles_data, coords_2d
                )

                # Add metadata
                visualization_data['metadata'] = {
                    'total_articles': len(articles_data),
                    'days_covered': days,
                    'generated_at': datetime.utcnow().isoformat(),
                    'unique_topics': len(set(a['topic_id'] for a in articles_data if a['topic_id'] != -1))
                }

                logger.info(f"✅ Visualization data ready: {len(articles_data)} points")

                return visualization_data

        except Exception as e:
            logger.error(f"Error generating visualization: {e}")
            raise

    def _prepare_plotly_data(
        self,
        articles: List[Dict],
        coords: np.ndarray
    ) -> Dict:
        """
        Prepare data in Plotly.js format.

        Args:
            articles: List of article metadata
            coords: 2D coordinates from UMAP

        Returns:
            Data structure for Plotly.js scatter plot
        """
        # Group by topic
        topics = {}

        for i, article in enumerate(articles):
            topic_id = article['topic_id']

            if topic_id not in topics:
                topics[topic_id] = {
                    'name': article['topic_name'],
                    'x': [],
                    'y': [],
                    'titles': [],
                    'urls': [],
                    'ids': [],
                    'dates': []
                }

            topics[topic_id]['x'].append(float(coords[i, 0]))
            topics[topic_id]['y'].append(float(coords[i, 1]))
            topics[topic_id]['titles'].append(article['title'])
            topics[topic_id]['urls'].append(article['url'])
            topics[topic_id]['ids'].append(article['id'])
            topics[topic_id]['dates'].append(article['date'])

        # Convert to Plotly traces
        traces = []

        # Color palette for topics
        colors = [
            '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7',
            '#DDA0DD', '#98D8C8', '#F7DC6F', '#BB8FCE', '#85C1E9',
            '#F8B500', '#00CED1', '#FF69B4', '#32CD32', '#FFD700'
        ]

        # Sort topics: outliers last
        sorted_topic_ids = sorted(topics.keys(), key=lambda x: (x == -1, x))

        for i, topic_id in enumerate(sorted_topic_ids):
            topic_data = topics[topic_id]

            # Outliers get special styling
            if topic_id == -1:
                color = '#CCCCCC'
                name = '🔸 Outliers (bez tematu)'
                size = 6
                opacity = 0.5
            else:
                color = colors[i % len(colors)]
                name = f'📌 {topic_data["name"]} ({len(topic_data["x"])} art.)'
                size = 10
                opacity = 0.8

            trace = {
                'type': 'scatter',
                'mode': 'markers',
                'name': name,
                'x': topic_data['x'],
                'y': topic_data['y'],
                'text': topic_data['titles'],
                'customdata': list(zip(
                    topic_data['urls'],
                    topic_data['ids'],
                    topic_data['dates']
                )),
                'hovertemplate': (
                    '<b>%{text}</b><br>'
                    '<extra></extra>'
                ),
                'marker': {
                    'size': size,
                    'color': color,
                    'opacity': opacity,
                    'line': {
                        'width': 1,
                        'color': 'white'
                    }
                }
            }

            traces.append(trace)

        # Layout
        layout = {
            'title': {
                'text': '🗺️ Mapa Tematów - Przestrzeń Semantyczna Artykułów',
                'font': {'size': 18}
            },
            'xaxis': {
                'title': 'UMAP Dimension 1',
                'showgrid': True,
                'gridcolor': '#E5E5E5',
                'zeroline': False
            },
            'yaxis': {
                'title': 'UMAP Dimension 2',
                'showgrid': True,
                'gridcolor': '#E5E5E5',
                'zeroline': False
            },
            'hovermode': 'closest',
            'legend': {
                'orientation': 'v',
                'yanchor': 'top',
                'y': 1,
                'xanchor': 'left',
                'x': 1.02
            },
            'plot_bgcolor': '#FAFAFA',
            'paper_bgcolor': 'white',
            'margin': {'l': 60, 'r': 200, 't': 60, 'b': 60}
        }

        return {
            'traces': traces,
            'layout': layout
        }

    def _empty_response(self) -> Dict:
        """Return empty visualization response."""
        return {
            'traces': [],
            'layout': {
                'title': 'Brak danych do wizualizacji',
                'annotations': [{
                    'text': 'Uruchom scraping, aby zebrać artykuły',
                    'showarrow': False,
                    'font': {'size': 16}
                }]
            },
            'metadata': {
                'total_articles': 0,
                'days_covered': 0,
                'generated_at': datetime.utcnow().isoformat(),
                'unique_topics': 0
            }
        }

    def get_topic_centroids(self, days: int = 60) -> List[Dict]:
        """
        Get centroid positions for each topic.

        Args:
            days: Number of days to analyze

        Returns:
            List of topic centroids with metadata
        """
        # This would calculate mean position for each topic
        # Useful for adding labels to the plot
        pass

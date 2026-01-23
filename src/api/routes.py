from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
from typing import Optional, List
from pydantic import BaseModel
from loguru import logger
import os

from ..storage.database import Database
from ..analyzers.trend_detector import TrendDetector
from ..config import settings


app = FastAPI(
    title="Ad Trends Monitor API",
    description="Monitor advertising industry trends from public sources",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for admin panel
admin_panel_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "admin-panel")
if os.path.exists(admin_panel_path):
    app.mount("/admin", StaticFiles(directory=admin_panel_path, html=True), name="admin")

# Initialize database
db = Database()


# Pydantic models
class SourceCreate(BaseModel):
    name: str
    url: str
    source_type: str  # blog/rss/sitemap


class SourceResponse(BaseModel):
    id: int
    name: str
    url: str
    source_type: str
    last_scraped: Optional[datetime]
    active: bool

    class Config:
        from_attributes = True


class ArticleResponse(BaseModel):
    id: int
    title: str
    url: str
    published_date: Optional[datetime]
    word_count: int
    source_name: str

    class Config:
        from_attributes = True


class TrendResponse(BaseModel):
    keyword: str
    count: int
    growth_rate: float
    is_trending: bool
    topic_id: Optional[int] = None


class KeywordResponse(BaseModel):
    keyword: str
    count: int


# Routes
@app.get("/")
def root():
    """API root endpoint."""
    return {
        "name": "Ad Trends Monitor API",
        "version": "1.0.0",
        "endpoints": [
            "/trends",
            "/keywords",
            "/articles",
            "/sources",
            "/stats"
        ]
    }


@app.get("/trends", response_model=List[TrendResponse])
def get_trends(
    days: int = Query(30, description="Analysis period in days", ge=1, le=365),
    limit: int = Query(20, description="Number of trends to return", ge=1, le=100),
    min_growth: float = Query(0.2, description="Minimum growth rate (0.2 = 20%)", ge=0.0)
):
    """
    Get current trends based on keyword growth.

    Returns keywords that have increased in frequency compared to the previous period.
    """
    try:
        detector = TrendDetector(db)
        trends = detector.calculate_trends(
            window_days=days,
            min_growth_rate=min_growth
        )

        # Filter and limit
        trending = [t for t in trends if t['is_trending']]
        trending = trending[:limit]

        return trending

    except Exception as e:
        logger.error(f"Error getting trends: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/trends/emerging", response_model=List[dict])
def get_emerging_trends(
    days: int = Query(30, description="Analysis period in days", ge=1, le=365),
    limit: int = Query(20, description="Number of trends to return", ge=1, le=100)
):
    """
    Get emerging keywords (new keywords that didn't exist in previous period).
    """
    try:
        detector = TrendDetector(db)
        emerging = detector.get_emerging_keywords(window_days=days, top_n=limit)
        return emerging

    except Exception as e:
        logger.error(f"Error getting emerging trends: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/trends/declining", response_model=List[dict])
def get_declining_trends(
    days: int = Query(30, description="Analysis period in days", ge=1, le=365),
    limit: int = Query(20, description="Number of trends to return", ge=1, le=100)
):
    """
    Get declining keywords (keywords decreasing in frequency).
    """
    try:
        detector = TrendDetector(db)
        declining = detector.get_declining_keywords(window_days=days, top_n=limit)
        return declining

    except Exception as e:
        logger.error(f"Error getting declining trends: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/trends/summary")
def get_trends_summary(
    days: int = Query(30, description="Analysis period in days", ge=1, le=365)
):
    """
    Get comprehensive trends summary with statistics.
    """
    try:
        detector = TrendDetector(db)
        summary = detector.get_trending_summary(window_days=days)
        return summary

    except Exception as e:
        logger.error(f"Error getting trends summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/keywords", response_model=List[KeywordResponse])
def get_top_keywords(
    start_date: Optional[datetime] = Query(None, description="Start date filter"),
    end_date: Optional[datetime] = Query(None, description="End date filter"),
    limit: int = Query(50, description="Number of keywords to return", ge=1, le=200)
):
    """
    Get most frequent keywords.
    """
    try:
        keywords = db.get_top_keywords(
            start_date=start_date,
            end_date=end_date,
            limit=limit
        )

        return [
            {"keyword": kw, "count": count}
            for kw, count in keywords
        ]

    except Exception as e:
        logger.error(f"Error getting keywords: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/articles")
def get_articles(
    keyword: Optional[str] = Query(None, description="Filter by keyword"),
    topic_id: Optional[int] = Query(None, description="Filter by topic ID"),
    source_id: Optional[int] = Query(None, description="Filter by source ID"),
    days: Optional[int] = Query(None, description="Filter by days back", ge=1),
    limit: int = Query(20, description="Number of articles to return", ge=1, le=100)
):
    """
    Search and filter articles.
    """
    try:
        # If topic_id is provided, use specialized method
        if topic_id is not None:
            articles = db.get_articles_by_topic(topic_id=topic_id, limit=limit)
            return [
                {
                    "id": article.id,
                    "title": article.title,
                    "url": article.url,
                    "published_date": article.published_date,
                    "word_count": article.word_count,
                    "source_name": article.source.name
                }
                for article in articles
            ]

        start_date = None
        end_date = None

        if days:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)

        articles = db.get_articles(
            keyword=keyword,
            source_id=source_id,
            start_date=start_date,
            end_date=end_date,
            limit=limit
        )

        return [
            {
                "id": article.id,
                "title": article.title,
                "url": article.url,
                "published_date": article.published_date,
                "word_count": article.word_count,
                "source_name": article.source.name
            }
            for article in articles
        ]

    except Exception as e:
        logger.error(f"Error getting articles: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/sources", response_model=List[SourceResponse])
def get_sources(
    active_only: bool = Query(True, description="Return only active sources")
):
    """
    List all monitored sources.
    """
    try:
        with db.get_session() as session:
            from ..storage.models import Source

            query = session.query(Source)
            if active_only:
                query = query.filter(Source.active == True)

            sources = query.all()
            return sources

    except Exception as e:
        logger.error(f"Error getting sources: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/sources", response_model=SourceResponse)
def add_source(source: SourceCreate):
    """
    Add a new source to monitor.
    """
    try:
        # Validate source type
        if source.source_type not in ['blog', 'rss', 'sitemap']:
            raise HTTPException(
                status_code=400,
                detail="source_type must be one of: blog, rss, sitemap"
            )

        new_source = db.add_source(
            name=source.name,
            url=source.url,
            source_type=source.source_type
        )

        return new_source

    except Exception as e:
        logger.error(f"Error adding source: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/sources/{source_id}", response_model=SourceResponse)
def update_source(source_id: int, source: SourceCreate):
    """
    Update an existing source.
    """
    try:
        # Validate source type
        if source.source_type not in ['blog', 'rss', 'sitemap']:
            raise HTTPException(
                status_code=400,
                detail="source_type must be one of: blog, rss, sitemap"
            )

        with db.get_session() as session:
            from ..storage.models import Source

            existing_source = session.query(Source).filter(Source.id == source_id).first()

            if not existing_source:
                raise HTTPException(status_code=404, detail="Source not found")

            existing_source.name = source.name
            existing_source.url = source.url
            existing_source.source_type = source.source_type

            session.commit()
            session.refresh(existing_source)

            return existing_source

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating source: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/sources/{source_id}")
def deactivate_source(source_id: int):
    """
    Deactivate a source (soft delete).
    """
    try:
        with db.get_session() as session:
            from ..storage.models import Source

            source = session.query(Source).filter(Source.id == source_id).first()

            if not source:
                raise HTTPException(status_code=404, detail="Source not found")

            source.active = False
            session.commit()

            return {"message": f"Source {source_id} deactivated successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deactivating source: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/scrape/trigger")
def trigger_scraping():
    """
    Manually trigger a scraping job.
    Note: This runs synchronously and may take several minutes.
    """
    try:
        import subprocess
        import sys

        # Get the Python executable from the current environment
        python_exe = sys.executable

        # Run scraping in background
        result = subprocess.Popen(
            [python_exe, "main.py", "--once"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        return {
            "message": "Scraping job triggered successfully",
            "pid": result.pid,
            "status": "running"
        }

    except Exception as e:
        logger.error(f"Error triggering scraping: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stats")
def get_stats():
    """
    Get system statistics.
    """
    try:
        stats = db.get_stats()
        return stats

    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
def health_check():
    """
    Health check endpoint.
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow()
    }


@app.get("/topics/visualization")
def get_topic_visualization(
    days: int = Query(60, description="Number of days to analyze", ge=7, le=180),
    max_articles: int = Query(500, description="Maximum articles to visualize", ge=50, le=1000),
    include_outliers: bool = Query(True, description="Include outlier articles (topic -1)")
):
    """
    Get 2D visualization data for topic clusters.

    Returns Plotly.js compatible data structure with:
    - traces: Array of scatter plot traces (one per topic)
    - layout: Plot configuration
    - metadata: Statistics about the visualization

    The visualization shows articles as points in 2D space,
    where similar articles are clustered together.
    Uses UMAP to reduce high-dimensional embeddings to 2D.
    """
    try:
        from ..analyzers.topic_visualizer import TopicVisualizer

        visualizer = TopicVisualizer(db)
        data = visualizer.generate_visualization_data(
            days=days,
            max_articles=max_articles,
            include_outliers=include_outliers
        )

        return data

    except Exception as e:
        logger.error(f"Error generating visualization: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Error handlers
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

"""
Fix database type issues - convert bytes to int for size column.
"""

from src.storage.database import Database
from src.storage.models import Topic
from loguru import logger

def fix_topic_sizes():
    """Fix topic size column - convert bytes to int."""
    db = Database()

    with db.get_session() as session:
        topics = session.query(Topic).all()
        fixed_count = 0

        for topic in topics:
            if isinstance(topic.size, bytes):
                # Convert bytes to int
                try:
                    if topic.size:
                        topic.size = int.from_bytes(topic.size, 'big')
                    else:
                        topic.size = 0
                    fixed_count += 1
                    logger.info(f"Fixed topic {topic.topic_id}: converted bytes to int (size={topic.size})")
                except Exception as e:
                    logger.error(f"Failed to convert topic {topic.topic_id} size: {e}")
                    topic.size = 0
                    fixed_count += 1
            elif not isinstance(topic.size, int):
                # Convert any other type to int
                try:
                    topic.size = int(topic.size) if topic.size else 0
                    fixed_count += 1
                    logger.info(f"Fixed topic {topic.topic_id}: converted to int (size={topic.size})")
                except Exception as e:
                    logger.error(f"Failed to convert topic {topic.topic_id} size: {e}")
                    topic.size = 0
                    fixed_count += 1

        if fixed_count > 0:
            session.commit()
            logger.info(f"Fixed {fixed_count} topic size entries")
        else:
            logger.info("No topics needed fixing")

    logger.info("Database type fix completed")

if __name__ == "__main__":
    logger.info("Starting database type fix...")
    fix_topic_sizes()
    logger.info("Done!")

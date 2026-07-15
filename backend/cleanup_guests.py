#!/usr/bin/env python3
"""
Guest account cleanup script.

Deletes guest accounts (is_guest=True) older than 24 hours, along with:
- All their documents from the DB
- All their Qdrant vector points
- All their conversations and messages (via cascade)

Run this as a cron job or scheduled task:
  - Heroku Scheduler: daily at 2am
  - Railway: cron job addon
  - HuggingFace Spaces: manual cronjob trigger
  - Docker: add to crontab in container

Usage:
  python cleanup_guests.py [--dry-run] [--age-hours 24]
"""

import asyncio
import sys
import os
from datetime import datetime, timezone, timedelta

# Add parent directory to path so imports work
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import select, delete
from dotenv import load_dotenv

from db.database import AsyncSessionLocal
from db.models import User, Document
from qdrant_client import QdrantClient

load_dotenv()

# Qdrant connection
COLLECTION_NAME = "research_documents"
qdrant = QdrantClient(
    url=os.getenv("QDRANT_URL"),
    api_key=os.getenv("QDRANT_API_KEY"),
)


async def cleanup_old_guests(age_hours: int = 24, dry_run: bool = False):
    """
    Remove guest accounts older than age_hours and their associated data.
    
    Args:
        age_hours: Delete guests created more than this many hours ago
        dry_run: If True, only print what would be deleted without actually deleting
    """
    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=age_hours)
    
    print(f"{'[DRY RUN] ' if dry_run else ''}Cleaning up guest accounts older than {age_hours} hours")
    print(f"Cutoff time: {cutoff_time.isoformat()}")
    
    async with AsyncSessionLocal() as db:
        # Find old guest accounts
        result = await db.execute(
            select(User).where(
                User.is_guest == True,
                User.created_at < cutoff_time
            )
        )
        old_guests = list(result.scalars().all())
        
        if not old_guests:
            print("No guest accounts to clean up.")
            return
        
        print(f"\nFound {len(old_guests)} guest account(s) to delete:")
        
        for guest in old_guests:
            age = datetime.now(timezone.utc) - guest.created_at
            print(f"  - {guest.email} (created {age.days}d {age.seconds//3600}h ago)")
            
            # Get document count for this guest
            doc_result = await db.execute(
                select(Document).where(Document.user_id == guest.id)
            )
            documents = list(doc_result.scalars().all())
            print(f"    Documents: {len(documents)}")
            
            if not dry_run:
                # Delete Qdrant vectors for this guest's documents
                user_id_str = str(guest.id)
                try:
                    # Qdrant filter: delete all points with this user_id
                    from qdrant_client.models import Filter, FieldCondition, MatchValue
                    qdrant.delete(
                        collection_name=COLLECTION_NAME,
                        points_filter=Filter(
                            must=[FieldCondition(key="user_id", match=MatchValue(value=user_id_str))]
                        )
                    )
                    print(f"    ✓ Deleted Qdrant vectors for user {user_id_str}")
                except Exception as e:
                    print(f"    ⚠ Failed to delete Qdrant vectors: {e}")
                
                # Delete user from DB (cascade will delete documents, conversations, messages)
                await db.delete(guest)
                print(f"    ✓ Deleted user and all associated data")
        
        if not dry_run:
            await db.commit()
            print(f"\n✅ Cleanup complete: {len(old_guests)} guest account(s) deleted")
        else:
            print(f"\n[DRY RUN] Would delete {len(old_guests)} guest account(s)")


async def get_guest_stats():
    """Print statistics about guest accounts."""
    async with AsyncSessionLocal() as db:
        # Total guests
        result = await db.execute(select(User).where(User.is_guest == True))
        all_guests = list(result.scalars().all())
        
        if not all_guests:
            print("No guest accounts found.")
            return
        
        print(f"\nGuest Account Statistics:")
        print(f"  Total guests: {len(all_guests)}")
        
        # Age distribution
        now = datetime.now(timezone.utc)
        age_buckets = {"< 1h": 0, "1-6h": 0, "6-12h": 0, "12-24h": 0, "> 24h": 0}
        
        for guest in all_guests:
            age = now - guest.created_at
            hours = age.total_seconds() / 3600
            
            if hours < 1:
                age_buckets["< 1h"] += 1
            elif hours < 6:
                age_buckets["1-6h"] += 1
            elif hours < 12:
                age_buckets["6-12h"] += 1
            elif hours < 24:
                age_buckets["12-24h"] += 1
            else:
                age_buckets["> 24h"] += 1
        
        print("\n  Age distribution:")
        for bucket, count in age_buckets.items():
            print(f"    {bucket}: {count}")
        
        # Document count
        total_docs = 0
        for guest in all_guests:
            doc_result = await db.execute(
                select(Document).where(Document.user_id == guest.id)
            )
            total_docs += len(list(doc_result.scalars().all()))
        
        print(f"\n  Total documents uploaded by guests: {total_docs}")
        print(f"  Average documents per guest: {total_docs / len(all_guests):.1f}")


def main():
    """CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Clean up old guest accounts")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deleted without actually deleting"
    )
    parser.add_argument(
        "--age-hours",
        type=int,
        default=24,
        help="Delete guests older than this many hours (default: 24)"
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show guest account statistics without deleting anything"
    )
    
    args = parser.parse_args()
    
    if args.stats:
        asyncio.run(get_guest_stats())
    else:
        asyncio.run(cleanup_old_guests(age_hours=args.age_hours, dry_run=args.dry_run))


if __name__ == "__main__":
    main()

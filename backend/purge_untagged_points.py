"""
purge_untagged_points.py
------------------------
One-shot cleanup: deletes every Qdrant point in the research_documents
collection that has NO user_id payload field.

These are documents uploaded before user-isolation was enforced. Because
they carry no user_id, the retriever's FieldCondition filter never matched
them -- meaning they leaked to EVERY user's queries.

Run once from the backend/ directory, then delete this script.

Usage:
    cd backend
    python purge_untagged_points.py
"""

import os
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, IsEmptyCondition, PayloadField

load_dotenv()

COLLECTION_NAME = "research_documents"

qdrant = QdrantClient(
    url=os.getenv("QDRANT_URL"),
    api_key=os.getenv("QDRANT_API_KEY"),
)


def purge_untagged():
    # IsEmptyCondition matches points where the field is missing or null
    orphan_filter = Filter(
        must=[
            IsEmptyCondition(is_empty=PayloadField(key="user_id"))
        ]
    )

    # Count first so we know what we are deleting
    count_result = qdrant.count(
        collection_name=COLLECTION_NAME,
        count_filter=orphan_filter,
        exact=True,
    )
    total = count_result.count
    print(f"Found {total} untagged points (no user_id) -- deleting...")

    if total == 0:
        print("Nothing to delete. Collection is already clean.")
        return

    # Delete all matching points
    qdrant.delete(
        collection_name=COLLECTION_NAME,
        points_selector=orphan_filter,
    )

    # Verify
    remaining = qdrant.count(
        collection_name=COLLECTION_NAME,
        count_filter=orphan_filter,
        exact=True,
    ).count

    if remaining == 0:
        print(f"Done. Successfully deleted {total} untagged points.")
        print("  All remaining points are properly user-scoped.")
    else:
        print(f"WARNING: {remaining} untagged points still remain -- re-run this script.")


if __name__ == "__main__":
    purge_untagged()

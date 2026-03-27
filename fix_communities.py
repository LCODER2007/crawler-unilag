"""
Merge duplicate communities: 'Science' -> 'Faculty of Science', 'Engineering' -> 'Faculty of Engineering'
"""
import sys; sys.path.insert(0,'.')
from uraas.database import SessionLocal
from sqlalchemy import text

s = SessionLocal()

# Move all collections from old community to new
merges = [
    (1, 5),   # 'Science' -> 'Faculty of Science'
    (2, 6),   # 'Engineering' -> 'Faculty of Engineering'
]

for old_id, new_id in merges:
    # Move collections
    s.execute(text(f"UPDATE collections SET community_id = {new_id} WHERE community_id = {old_id}"))
    # Move item_collections via collections
    print(f"Merged community {old_id} -> {new_id}")

# Delete old communities
for old_id, _ in merges:
    s.execute(text(f"DELETE FROM communities WHERE id = {old_id}"))

s.commit()
s.close()
print("Done.")

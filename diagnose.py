import sys; sys.path.insert(0,'.')
from uraas.database import SessionLocal, Item, Collection, Community
from sqlalchemy import func, text

s = SessionLocal()
rows = s.execute(text('''
  SELECT c2.name, COUNT(DISTINCT i.id) as cnt
  FROM items i
  JOIN item_collections ic ON i.id = ic.item_id
  JOIN collections c ON ic.collection_id = c.id
  JOIN communities c2 ON c.community_id = c2.id
  GROUP BY c2.name ORDER BY cnt DESC
''')).fetchall()
print('Papers per faculty (classified):')
for r in rows: print(f'  {r[0]}: {r[1]}')
total = s.query(Item).count()
classified = s.execute(text('SELECT COUNT(DISTINCT item_id) FROM item_collections')).fetchone()[0]
print(f'\nTotal papers: {total}')
print(f'Classified: {classified}')
print(f'Unclassified: {total - classified}')

# Sample 5 unclassified papers
unclassified = s.execute(text('''
  SELECT title FROM items 
  WHERE id NOT IN (SELECT DISTINCT item_id FROM item_collections)
  LIMIT 5
''')).fetchall()
print('\nSample unclassified:')
for r in unclassified: print(f'  - {r[0][:80]}')
s.close()

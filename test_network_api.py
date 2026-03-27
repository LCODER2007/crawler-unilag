import requests

# Test with specific author
r = requests.get('http://localhost:8080/api/analytics/author-network?author=Solomon Prince Nathaniel')
data = r.json()
print(f'Status: {r.status_code}')
print(f'Edges: {len(data["edges"])}')
print(f'Nodes: {len(data["nodes"])}')
print(f'\nFirst 5 edges:')
for e in data['edges'][:5]:
    print(f'  {e["source"]} <-> {e["target"]} ({e["weight"]} papers)')

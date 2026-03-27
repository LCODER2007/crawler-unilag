import requests

r = requests.get('http://localhost:8080/api/analytics/language-research')
print(f'Status: {r.status_code}')
data = r.json()
print(f'Total papers: {data["total_language_papers"]}')
print(f'Top keywords: {len(data["top_keywords"])}')
print(f'Papers: {len(data["papers"])}')
if data["papers"]:
    print(f'First paper: {data["papers"][0]["title"]}')

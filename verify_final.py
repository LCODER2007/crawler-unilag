import sys
sys.path.insert(0, '.')

from uraas.dashboard.app import app
client = app.test_client()
routes = ['/', '/api/analytics/overview', '/api/analytics/search?q=cancer', '/api/papers/1']
for r in routes:
    resp = client.get(r)
    print(f'  {resp.status_code}  {r}')

from uraas.utils.staff_validator import staff_validator
print(f'  Staff loaded: {len(staff_validator.staff_names)}')
print(f'  Surname->faculty entries: {len(staff_validator._surname_to_faculty)}')
hint = staff_validator.get_faculty_hint('Rose Anorlu')
dept = staff_validator.get_department_hint('Rose Anorlu')
print(f'  Faculty hint for Rose Anorlu: {hint}')
print(f'  Dept hint for Rose Anorlu: {dept}')
hint2 = staff_validator.get_faculty_hint('Matthew O. Ilori')
print(f'  Faculty hint for Matthew O. Ilori: {hint2}')

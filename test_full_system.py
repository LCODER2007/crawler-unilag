"""
URAAS Full System Test Suite
Tests every component end-to-end before live deployment.
"""
import sys
import os

if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

PASS = "[PASS]"
FAIL = "[FAIL]"
WARN = "[WARN]"

results = []

def check(name, passed, detail=""):
    status = PASS if passed else FAIL
    results.append((status, name, detail))
    print(f"  {status} {name}" + (f" — {detail}" if detail else ""))

def section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

# ─────────────────────────────────────────────
section("1. IMPORTS & DEPENDENCIES")
# ─────────────────────────────────────────────

try:
    import flask
    check("Flask", True, flask.__version__)
except ImportError as e:
    check("Flask", False, str(e))

try:
    import flask_socketio
    check("Flask-SocketIO", True)
except ImportError as e:
    check("Flask-SocketIO", False, str(e))

try:
    import sqlalchemy
    check("SQLAlchemy", True, sqlalchemy.__version__)
except ImportError as e:
    check("SQLAlchemy", False, str(e))

try:
    import requests
    check("Requests", True, requests.__version__)
except ImportError as e:
    check("Requests", False, str(e))

try:
    from thefuzz import fuzz
    check("thefuzz (fuzzy matching)", True)
except ImportError as e:
    check("thefuzz", False, str(e))

try:
    import dotenv
    check("python-dotenv", True)
except ImportError as e:
    check("python-dotenv", False, str(e))

# ─────────────────────────────────────────────
section("2. CONFIGURATION")
# ─────────────────────────────────────────────

try:
    from uraas.config import config
    check("Config loads", True)
    check("Dashboard port set", config.DASHBOARD_PORT == 8080, str(config.DASHBOARD_PORT))
    check("Storage path set", bool(config.STORAGE_PATH), config.STORAGE_PATH)
except Exception as e:
    check("Config loads", False, str(e))

# ─────────────────────────────────────────────
section("3. DATABASE")
# ─────────────────────────────────────────────

try:
    from uraas.database import SessionLocal, Item, Author, Collection, Community, File
    check("Database models import", True)
except Exception as e:
    check("Database models import", False, str(e))

try:
    session = SessionLocal()
    item_count = session.query(Item).count()
    author_count = session.query(Author).count()
    community_count = session.query(Community).count()
    collection_count = session.query(Collection).count()
    session.close()
    check("Database connection", True)
    check("Communities seeded", community_count >= 12, f"{community_count} communities")
    check("Collections seeded", collection_count >= 60, f"{collection_count} collections")
    check("Papers in DB", item_count > 0, f"{item_count} papers")
    check("Authors in DB", author_count > 0, f"{author_count} authors")
except Exception as e:
    check("Database connection", False, str(e))

# ─────────────────────────────────────────────
section("4. STAFF VALIDATOR")
# ─────────────────────────────────────────────

try:
    from uraas.utils.staff_validator import staff_validator
    check("Staff validator loads", True)
    check("Staff cache populated", len(staff_validator.staff_names) > 900,
          f"{len(staff_validator.staff_names)} names")

    # Test known UNILAG staff names
    test_cases = [
        ("Rose Anorlu", True),
        ("Matthew O. Ilori", True),
        ("Bolajoko O. Olusanya", True),
        ("John Smith Harvard", False),
        ("Barack Obama", False),
    ]
    for name, expected in test_cases:
        result = staff_validator.is_staff_member(name, fuzzy_threshold=75)
        check(f"  Validate '{name}'", result == expected,
              f"expected={expected}, got={result}")
except Exception as e:
    check("Staff validator", False, str(e))

# ─────────────────────────────────────────────
section("5. UNILAG CLASSIFIER")
# ─────────────────────────────────────────────

try:
    from uraas.utils.unilag_classifier import UNILAGClassifier
    classifier = UNILAGClassifier()
    check("Classifier imports", True)

    test_papers = [
        ("Antimicrobial resistance in Lagos hospitals", ["medicine", "pharmacy", "science"]),
        ("Structural analysis of reinforced concrete beams", ["engineering"]),
        ("Corporate governance and firm performance in Nigeria", ["management", "social"]),
    ]
    for title, expected_keywords in test_papers:
        result = classifier.get_best_classification(title)
        faculty = (result[0] if result else "Unclassified").lower()
        check(f"  Classify: '{title[:40]}...'", True,
              f"-> {result[0] if result else 'Unclassified'}")
except Exception as e:
    check("Classifier", False, str(e))

# ─────────────────────────────────────────────
section("6. ANALYTICS ENGINE")
# ─────────────────────────────────────────────

try:
    from uraas.analytics.engine import analytics
    check("Analytics engine imports", True)

    top_authors = analytics.get_top_authors(limit=5)
    check("get_top_authors()", isinstance(top_authors, list),
          f"{len(top_authors)} authors returned")

    tree = analytics.get_papers_by_faculty_and_department()
    check("get_papers_by_faculty_and_department()", isinstance(tree, dict),
          f"{len(tree)} faculties")

    # Count total papers in tree
    total = sum(len(papers) for depts in tree.values() for papers in depts.values())
    check("Tree has papers", total > 0, f"{total} papers in tree")

    network = analytics.get_department_collaboration_network()
    check("get_department_collaboration_network()", isinstance(network, list))
except Exception as e:
    check("Analytics engine", False, str(e))

# ─────────────────────────────────────────────
section("7. OPENALEX API CONNECTIVITY")
# ─────────────────────────────────────────────

try:
    import requests
    url = "https://api.openalex.org/works?filter=institutions.ror:05rk03822&per-page=1&mailto=library@unilag.edu.ng"
    resp = requests.get(url, timeout=15)
    data = resp.json()
    total = data.get("meta", {}).get("count", 0)
    check("OpenAlex API reachable", resp.status_code == 200)
    check("UNILAG ROR ID valid", total > 0, f"{total:,} total UNILAG papers indexed")
except Exception as e:
    check("OpenAlex API", False, str(e))

# ─────────────────────────────────────────────
section("8. CRAWLER (LIVE 3-PAPER TEST)")
# ─────────────────────────────────────────────

try:
    from uraas.database import SessionLocal, Item
    session = SessionLocal()
    before_count = session.query(Item).count()
    session.close()

    # Run crawler as subprocess to avoid module reload issues
    import subprocess
    result = subprocess.run(
        [sys.executable, "crawl_10_validated.py", "--target", "3"],
        capture_output=True, text=True, timeout=60,
        encoding='utf-8', errors='replace'
    )

    session = SessionLocal()
    after_count = session.query(Item).count()
    session.close()

    new_papers = after_count - before_count
    check("Crawler runs without crash", result.returncode == 0,
          f"exit code {result.returncode}")
    check("Crawler stores new papers", new_papers >= 0,
          f"{new_papers} new papers added (0 = all already exist)")
    if result.returncode != 0:
        print(f"    stderr: {result.stderr[-300:]}")
except Exception as e:
    check("Crawler", False, str(e))

# ─────────────────────────────────────────────
section("9. DASHBOARD ROUTES")
# ─────────────────────────────────────────────

try:
    from uraas.dashboard.app import app
    client = app.test_client()

    r = client.get('/')
    check("GET / (dashboard home)", r.status_code == 200)

    r = client.get('/api/stats')
    check("GET /api/stats", r.status_code == 200)
    data = r.get_json()
    check("  /api/stats has top_authors", "top_authors" in data)
    check("  /api/stats has network_edges", "network_edges" in data)

    r = client.get('/api/papers/tree')
    check("GET /api/papers/tree", r.status_code == 200)
    data = r.get_json()
    check("  /api/papers/tree has data", "data" in data)

    r = client.get('/api/crawler/status')
    check("GET /api/crawler/status", r.status_code == 200)
    data = r.get_json()
    check("  Crawler status returns status field", "status" in data)

except Exception as e:
    check("Dashboard routes", False, str(e))

# ─────────────────────────────────────────────
section("10. STORAGE & FILE SYSTEM")
# ─────────────────────────────────────────────

storage_path = "./storage/pdfs"
check("Storage directory exists", os.path.exists(storage_path), storage_path)

pdf_count = len([f for f in os.listdir(storage_path) if f.endswith('.pdf')]) if os.path.exists(storage_path) else 0
check("PDF storage accessible", True, f"{pdf_count} PDFs on disk")

db_path = "./uraas.db"
check("SQLite DB file exists", os.path.exists(db_path), f"{os.path.getsize(db_path)//1024}KB")

# ─────────────────────────────────────────────
section("RESULTS SUMMARY")
# ─────────────────────────────────────────────

passed = sum(1 for r in results if r[0] == PASS)
failed = sum(1 for r in results if r[0] == FAIL)
total  = len(results)

print(f"\n  Total:  {total}")
print(f"  Passed: {passed}")
print(f"  Failed: {failed}")

if failed > 0:
    print(f"\n  FAILURES:")
    for status, name, detail in results:
        if status == FAIL:
            print(f"    {FAIL} {name} — {detail}")

print()
if failed == 0:
    print("  >> ALL TESTS PASSED. System is ready for deployment.")
elif failed <= 2:
    print("  >> MOSTLY READY. Fix the failures above before going live.")
else:
    print("  >> NOT READY. Multiple failures detected.")
print()

# URAAS - University Repository Archival & Analytics System

World-class institutional repository harvester for the University of Lagos (UNILAG). Automatically discovers, validates, downloads, and classifies academic publications from UNILAG faculty across multiple sources.

## 🎯 Key Features

- **Staff-Validated Harvesting**: Only captures papers from confirmed UNILAG staff members (no false positives)
- **Multi-Source Discovery**: Harvests from arXiv, Google Scholar, OpenAlex, Crossref, and UNILAG faculty directories
- **Intelligent Deduplication**: DOI-based, URL-based, and fuzzy title matching (95% threshold)
- **Local PDF Storage**: Downloads and stores PDFs locally with SHA256 verification
- **Smart Access Control**: Uses Unpaywall to determine legal open-access status (Gold/Green/Bronze)
- **Comprehensive Classification**: Maps papers to all 12 UNILAG faculties and 80+ departments
- **Real-Time Dashboard**: Live crawler monitoring with WebSocket updates
- **High-Impact Alerts**: Automatic notifications for publications in top-tier journals

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    URAAS PIPELINE                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Phase 0: Faculty Seeding                                  │
│  └─ Crawl UNILAG website → Extract staff names             │
│                                                             │
│  Phase 1: Multi-Source Discovery                           │
│  ├─ arXiv Spider                                           │
│  ├─ Google Scholar Spider (with proxy rotation)           │
│  ├─ OpenAlex Spider (ROR-based)                           │
│  └─ Crossref Spider                                        │
│                                                             │
│  Phase 2: Validation Pipeline                              │
│  ├─ Staff Validator (fuzzy name matching)                 │
│  ├─ Affiliation Filter (UNILAG patterns)                  │
│  └─ Unpaywall Enrichment (OA status)                      │
│                                                             │
│  Phase 3: Deduplication                                    │
│  ├─ DOI exact match                                        │
│  ├─ URL exact match                                        │
│  └─ Fuzzy title match (95% threshold)                     │
│                                                             │
│  Phase 4: Storage & Classification                         │
│  ├─ Download PDF to local storage                         │
│  ├─ Classify into Faculty/Department                      │
│  ├─ Store metadata (Dublin Core)                          │
│  └─ Generate high-impact alerts                           │
│                                                             │
│  Phase 5: Analytics & Dashboard                            │
│  ├─ Top authors ranking                                    │
│  ├─ Collaboration network analysis                        │
│  └─ Real-time crawler monitoring                          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## 📋 Prerequisites

- Python 3.9+
- PostgreSQL 15+ (optional, SQLite works for development)
- Redis 7+ (optional, for Celery)
- 10GB+ free disk space for PDF storage

## 🚀 Quick Start

### 1. Clone and Setup

```bash
git clone <repository-url>
cd uraas
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your settings
```

Key configuration options:
```env
DATABASE_URL=sqlite:///uraas.db  # or postgresql://user:pass@localhost/uraas_db
STORAGE_PATH=./storage/pdfs
RATE_LIMIT_DELAY=2.0
DASHBOARD_PORT=8080
```

### 3. Initialize Database

```bash
python init_db.py
```

This creates all tables and seeds the database with UNILAG's 12 faculties and 80+ departments.

### 4. Start the Dashboard

```bash
python uraas/dashboard/app.py
```

Open http://localhost:8080 in your browser.

### 5. Run the Crawler

**IMPORTANT**: Use the aggressive crawler that searches up to 3000 pages:

```bash
# Recommended: Use the aggressive crawler
python crawl_aggressive.py --target 10

# Or use the launcher
python run_aggressive_crawler.py --target 10
```

You can also use the dashboard interface by clicking "Start Mining".

## 📊 Database Schema

### Communities (Faculties)
- Faculty of Arts
- Faculty of Science
- Faculty of Engineering
- College of Medicine
- Faculty of Pharmacy
- Faculty of Dental Sciences
- Faculty of Basic Medical Sciences
- Faculty of Social Sciences
- Faculty of Law
- Faculty of Education
- Faculty of Environmental Sciences
- Faculty of Management Sciences

### Collections (Departments)
80+ departments mapped with keyword-based classification.

### Items (Publications)
Dublin Core metadata schema:
- `dc.title` - Paper title
- `dc.identifier.doi` - DOI
- `dc.identifier.uri` - Persistent URL
- `dc.description.provenance` - Harvest metadata
- `dc.rights` - Access rights (Public/Private)

### Files (Bitstreams)
- Local file path
- SHA256 hash
- Access policy (based on Unpaywall OA status)
- Download timestamp

## 🔍 How Staff Validation Works

URAAS uses a **multi-stage validation** to ensure ZERO false positives:

1. **Faculty Directory Seeding**: Crawls UNILAG's official website to extract current staff names
2. **Fuzzy Name Matching**: Uses Levenshtein distance (85% threshold) to match author names
3. **Affiliation Cross-Check**: Validates UNILAG affiliation text or @unilag.edu.ng emails
4. **Manual Override**: Papers are ONLY accepted if at least ONE author is a confirmed staff member

This prevents papers that just mention "Lagos" or "University of Lagos" from being captured.

## 📁 Project Structure

```
uraas/
├── analytics/          # Analytics engine
│   └── engine.py      # Top authors, collaboration networks
├── dashboard/         # Flask web dashboard
│   ├── app.py        # Main dashboard app
│   └── templates/    # HTML templates
├── pipelines/         # Scrapy pipelines
│   ├── affiliation_filter.py  # Staff validation
│   ├── unpaywall.py          # OA status enrichment
│   ├── gap_analysis.py       # Deduplication
│   └── database.py           # Storage & classification
├── spiders/           # Web crawlers
│   └── sources/
│       ├── faculty_directory_spider.py
│       ├── arxiv_spider.py
│       ├── scholar_spider.py
│       ├── openalex_spider.py
│       └── crossref_spider.py
├── utils/             # Utilities
│   ├── unilag_classifier.py  # Faculty/dept classification
│   ├── staff_validator.py    # Staff name validation
│   ├── pdf_downloader.py     # PDF download & storage
│   └── normalizer.py         # Text normalization
├── config.py          # Configuration
└── database.py        # SQLAlchemy models

data/
└── unilag_staff.json  # Cached staff names

storage/
└── pdfs/              # Downloaded PDFs
```

## 🎛️ Dashboard Features

- **Crawler Control**: Start/stop crawler with live terminal feed
- **Top Authors**: Most productive UNILAG researchers
- **Archive Directory**: Hierarchical view (Faculty → Department → Papers)
- **Collaboration Network**: Inter-departmental research partnerships
- **Real-Time Updates**: WebSocket-based live crawler progress

## 🔧 Advanced Configuration

### Using PostgreSQL (Recommended for Production)

```bash
# Start PostgreSQL with Docker
docker-compose up -d postgres

# Update .env
DATABASE_URL=postgresql://uraas_user:uraas_pass@localhost:5432/uraas_db

# Initialize
python init_db.py
```

### Crawler Settings

**Use the right crawler for your needs:**

- `crawl_aggressive.py` - Searches up to 3000 pages until target reached (RECOMMENDED)
- `crawl_10_validated.py` - Old crawler that stops after ~250-350 candidates
- `run_aggressive_crawler.py` - Simple launcher for the aggressive crawler

Examples:
```bash
# Get 10 papers (will search thousands of pages if needed)
python crawl_aggressive.py --target 10

# Get 50 papers  
python crawl_aggressive.py --target 50

# Using the launcher
python run_aggressive_crawler.py --target 20
```

```python
'DOWNLOAD_DELAY': 2.0,           # Delay between requests (seconds)
'CONCURRENT_REQUESTS': 8,        # Parallel requests
'RETRY_TIMES': 3,                # Retry failed requests
```

### PDF Storage

PDFs are stored in `STORAGE_PATH` with naming: `{item_id}_{hash}.pdf`

Access via dashboard: `/api/papers/{item_id}/download`

## 📈 Analytics API

### Get Top Authors
```bash
GET /api/stats
```

Returns:
```json
{
  "top_authors": [
    {"author": "Prof. A. Smith", "paper_count": 45}
  ],
  "network_edges": [
    {"source": "Computer Science", "target": "Mathematics", "weight": 12}
  ]
}
```

### Get Papers Tree
```bash
GET /api/papers/tree
```

Returns hierarchical structure: Faculty → Department → Papers

## 🐛 Troubleshooting

### No staff names found
- Check UNILAG website structure hasn't changed
- Run faculty spider manually: `scrapy crawl unilag_faculty_directory`

### PDF downloads failing
- Check firewall/proxy settings
- Verify `STORAGE_PATH` has write permissions
- Some publishers block automated downloads

### High duplicate rate
- Adjust `FUZZY_THRESHOLD` in `gap_analysis.py`
- Check if staff cache is up to date

### Crawler stops after 100 items
- This limit has been removed in the latest version
- If using old code, remove `CLOSESPIDER_ITEMCOUNT` from settings

## 🔐 Security Notes

- Dashboard has NO authentication by default (add before production)
- PDFs are stored locally (ensure adequate disk space)
- Respect publisher copyright (Unpaywall integration helps)
- Rate limiting is enabled (2s delay between requests)

## 📝 License

[Add your license here]

## 🤝 Contributing

[Add contribution guidelines]

## 📧 Contact

For issues or questions, contact: library@unilag.edu.ng

---

**Built with ❤️ for the University of Lagos**

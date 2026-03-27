# URAAS Quick Start Guide

Get URAAS up and running in 5 minutes.

## Prerequisites

- Python 3.9 or higher
- 10GB free disk space
- Internet connection

## Installation

### Windows

```powershell
# Run setup script
.\setup.ps1

# Or manual setup:
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python init_db.py
```

### Linux/Mac

```bash
# Run setup script
chmod +x setup.sh
./setup.sh

# Or manual setup:
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python init_db.py
```

## Running URAAS

### 1. Start the Dashboard

```bash
# Activate virtual environment first
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Start dashboard
python uraas/dashboard/app.py
```

Open your browser to: **http://localhost:8080**

### 2. Start Harvesting

Click the **"▶ Start Mining"** button on the dashboard, or run manually:

```bash
python run_crawler.py
```

## What Happens Next?

1. **Phase 0**: Crawls UNILAG website to extract staff names (~2-5 minutes)
2. **Phase 1**: Searches arXiv, Google Scholar, OpenAlex, Crossref (~10-30 minutes)
3. **Phase 2**: Validates authors against staff list (real-time)
4. **Phase 3**: Deduplicates papers (real-time)
5. **Phase 4**: Downloads PDFs and classifies into departments (real-time)

## Monitoring Progress

Watch the dashboard for:
- **Live terminal feed**: Shows papers being discovered
- **Top Authors**: Updates as papers are added
- **Archive Directory**: Browse by Faculty → Department
- **High-Impact Alerts**: Notifications for top-tier publications

## Accessing Papers

Papers are stored in two ways:

1. **Metadata**: Searchable in the database
2. **PDFs**: Downloaded to `storage/pdfs/` directory

Click **"Download PDF"** links in the dashboard to access local copies.

## Stopping the Crawler

- Click **"■ Stop Processing"** on the dashboard, or
- Press `Ctrl+C` in the terminal running the crawler

## Troubleshooting

### No papers found
- Check that `data/unilag_staff.json` has staff names
- Verify internet connection
- Check logs in terminal

### PDF downloads failing
- Some publishers block automated downloads
- Check `storage/pdfs/` directory permissions
- Verify disk space available

### Database errors
- Run `python init_db.py` again
- Delete `uraas.db` and reinitialize

## Configuration

Edit `.env` file to customize:

```env
# Database
DATABASE_URL=sqlite:///uraas.db

# Storage
STORAGE_PATH=./storage/pdfs

# Crawler
RATE_LIMIT_DELAY=2.0
CONCURRENT_REQUESTS=8

# Dashboard
DASHBOARD_PORT=8080
```

## Next Steps

- Review papers in the dashboard
- Export data via API endpoints
- Set up PostgreSQL for production
- Configure automated scheduling

## Support

For issues, check:
1. README.md for detailed documentation
2. Logs in terminal output
3. GitHub issues (if applicable)

---

**Happy Harvesting! 🎓**

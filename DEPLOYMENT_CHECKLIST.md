# URAAS Deployment Checklist

Use this checklist to ensure URAAS is properly configured before production deployment.

## ✅ Pre-Deployment

### 1. Environment Setup
- [ ] Python 3.9+ installed
- [ ] Virtual environment created
- [ ] All dependencies installed (`pip install -r requirements.txt`)
- [ ] `.env` file configured with production values
- [ ] Database initialized (`python init_db.py`)

### 2. Directory Structure
- [ ] `storage/pdfs/` directory exists with write permissions
- [ ] `data/` directory exists
- [ ] `logs/` directory created (optional)
- [ ] Sufficient disk space (10GB+ recommended)

### 3. Database Configuration
- [ ] Database URL configured in `.env`
- [ ] For production: PostgreSQL recommended over SQLite
- [ ] Database tables created and seeded
- [ ] Test database connection

### 4. Staff Cache
- [ ] `data/unilag_staff.json` exists
- [ ] Contains current UNILAG staff names
- [ ] Run faculty directory spider to update: `scrapy crawl unilag_faculty_directory`
- [ ] Verify staff count (should be 500+)

### 5. Configuration Review
- [ ] `STORAGE_PATH` points to correct directory
- [ ] `RATE_LIMIT_DELAY` appropriate for your network
- [ ] `DASHBOARD_PORT` not conflicting with other services
- [ ] `DASHBOARD_SECRET_KEY` changed from default

## 🔒 Security (IMPORTANT)

### Before Production Deployment
- [ ] **Add authentication to dashboard** (currently open)
- [ ] Change `DASHBOARD_SECRET_KEY` to strong random value
- [ ] Add CSRF protection to POST endpoints
- [ ] Configure firewall rules
- [ ] Set up HTTPS/SSL if exposing publicly
- [ ] Review file permissions on storage directory
- [ ] Implement rate limiting on API endpoints

## 🧪 Testing

### 1. Staff Validator Test
```bash
python test_staff_validator.py
```
- [ ] All tests pass
- [ ] Staff names loaded correctly
- [ ] Fuzzy matching works

### 2. Database Test
```bash
python init_db.py
```
- [ ] No errors
- [ ] Communities and Collections created
- [ ] Can query database

### 3. Crawler Test
```bash
# Run with limited items for testing
python run_crawler.py
```
- [ ] Faculty directory spider completes
- [ ] At least one spider finds papers
- [ ] Papers validated against staff list
- [ ] PDFs downloaded successfully
- [ ] Papers classified into departments
- [ ] No crashes or errors

### 4. Dashboard Test
```bash
python uraas/dashboard/app.py
```
- [ ] Dashboard loads at http://localhost:8080
- [ ] Can start/stop crawler
- [ ] Live feed shows progress
- [ ] Papers appear in archive directory
- [ ] PDF download links work
- [ ] Top authors display correctly

## 📊 Performance Tuning

### For Large-Scale Harvesting
- [ ] Increase `CONCURRENT_REQUESTS` (default: 8)
- [ ] Adjust `DOWNLOAD_DELAY` based on network
- [ ] Consider PostgreSQL for better performance
- [ ] Monitor disk space usage
- [ ] Set up log rotation

### For Slow Networks
- [ ] Decrease `CONCURRENT_REQUESTS` to 4
- [ ] Increase `DOWNLOAD_DELAY` to 3.0
- [ ] Increase retry timeouts

## 🔄 Maintenance

### Regular Tasks
- [ ] Update staff cache monthly (run faculty spider)
- [ ] Monitor disk space in `storage/pdfs/`
- [ ] Review and clean up logs
- [ ] Backup database regularly
- [ ] Check for duplicate papers

### Monitoring
- [ ] Set up disk space alerts
- [ ] Monitor crawler success rate
- [ ] Track papers harvested per day
- [ ] Review high-impact alerts

## 🚀 Production Deployment

### Option 1: Local Server
```bash
# Activate environment
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Start dashboard (use screen/tmux for persistence)
python uraas/dashboard/app.py

# Or use gunicorn for production
gunicorn -w 4 -b 0.0.0.0:8080 uraas.dashboard.app:app
```

### Option 2: Docker (Future)
- [ ] Create Dockerfile
- [ ] Set up docker-compose with PostgreSQL
- [ ] Configure volumes for storage
- [ ] Set up reverse proxy (nginx)

### Option 3: Scheduled Crawling
```bash
# Add to crontab (Linux/Mac)
0 2 * * * cd /path/to/uraas && venv/bin/python run_crawler.py >> logs/crawler.log 2>&1

# Or use Windows Task Scheduler
# Run: venv\Scripts\python.exe run_crawler.py
# Schedule: Daily at 2:00 AM
```

## 📝 Post-Deployment

### Verify Everything Works
- [ ] Dashboard accessible
- [ ] Crawler can be started/stopped
- [ ] Papers are being harvested
- [ ] PDFs downloading correctly
- [ ] Classification working
- [ ] No errors in logs

### Documentation
- [ ] Document any custom configuration
- [ ] Note any issues encountered
- [ ] Create backup/restore procedures
- [ ] Document maintenance schedule

## 🆘 Troubleshooting

### Common Issues

**No papers found:**
- Check staff cache has names
- Verify internet connection
- Check spider logs for errors

**PDF downloads failing:**
- Check storage directory permissions
- Verify disk space available
- Some publishers block automated downloads

**Database errors:**
- Verify DATABASE_URL is correct
- Check database service is running
- Try reinitializing: `python init_db.py`

**Dashboard not loading:**
- Check port 8080 is not in use
- Verify Flask dependencies installed
- Check firewall settings

**High memory usage:**
- Reduce CONCURRENT_REQUESTS
- Increase DOWNLOAD_DELAY
- Consider running spiders separately

## 📞 Support

For issues:
1. Check logs in terminal output
2. Review README.md and QUICKSTART.md
3. Run test scripts to isolate issues
4. Check GitHub issues (if applicable)

## ✨ Optional Enhancements

### Future Improvements
- [ ] Set up Celery for scheduled crawling
- [ ] Add user authentication
- [ ] Implement full-text search
- [ ] Add export functionality
- [ ] Set up email notifications
- [ ] Create admin panel
- [ ] Add API documentation (Swagger)
- [ ] Implement caching (Redis)

---

**Last Updated:** [Current Date]
**Version:** 1.0.0
**Status:** Production Ready (with security additions)

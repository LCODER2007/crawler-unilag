# Design Document: Live Deployment to Render

## Overview

This design specifies the architecture and implementation for deploying the URAAS (University Research Analytics System) Flask dashboard to Render.com as a production web service. The system currently runs locally with PostgreSQL database, staff validation, crawler components, and includes Docker configuration. This deployment will transform it into a publicly accessible web application with automatic HTTPS, managed database, persistent storage, and production-grade infrastructure.

### Goals

- Deploy URAAS dashboard to Render.com as a web service accessible via public HTTPS URL
- Use Render's managed PostgreSQL database for reliable data storage
- Configure persistent disk storage for PDF files that survives redeployments
- Implement Gunicorn WSGI server with WebSocket support for real-time crawler output
- Enable automatic deployments from Git repository pushes
- Ensure mobile-responsive interface works correctly in production
- Provide health checks for automatic service monitoring and restart

### Non-Goals

- Implementing authentication/authorization (can be added later if needed)
- Setting up custom domain (Render provides .onrender.com subdomain by default)
- Implementing CDN or advanced caching (Render's infrastructure handles this)
- Migrating to microservices architecture (monolithic Flask app is sufficient)
- Setting up separate staging environment (single production environment for now)

### Target Platform: Render.com

Render.com is chosen as the deployment platform because:
- Free tier includes web service + PostgreSQL database
- Automatic HTTPS with managed SSL certificates
- Native Python/Flask support with simple configuration
- Git-based deployments (auto-deploy on push)
- Persistent disk storage for PDFs
- Built-in health checks and auto-restart
- Easy environment variable management
- No credit card required for free tier

## Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────────┐
│                         Internet                                │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         │ HTTPS (Port 443)
                         │
┌────────────────────────▼────────────────────────────────────────┐
│                   Render Load Balancer                          │
│         (Automatic SSL, HTTP→HTTPS Redirect, DDoS)             │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         │ HTTP (Internal)
                         │
┌────────────────────────▼────────────────────────────────────────┐
│              Render Web Service Container                       │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │         Gunicorn (2-4 workers, eventlet)                 │  │
│  │                                                          │  │
│  │  ┌────────────────────────────────────────────────────┐ │  │
│  │  │      Flask Application (app.py)                    │ │  │
│  │  │                                                    │ │  │
│  │  │  • Dashboard routes (/, /api/*)                   │ │  │
│  │  │  • Analytics engine                               │ │  │
│  │  │  • WebSocket (Flask-SocketIO)                     │ │  │
│  │  │  • Crawler subprocess control                     │ │  │
│  │  │  • PDF serving                                    │ │  │
│  │  │  • Health check endpoint (/health)                │ │  │
│  │  └────────────────────────────────────────────────────┘ │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  Persistent Disk: /opt/render/project/storage (10GB)           │
│  └─ pdfs/  (Downloaded PDF files)                              │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         │ PostgreSQL Protocol
                         │
┌────────────────────────▼────────────────────────────────────────┐
│           Render PostgreSQL Database (Free Tier)                │
│                                                                 │
│  • Database: uraas_production                                   │
│  • Tables: communities, collections, items, authors, files      │
│  • Connection pooling (5-10 connections)                        │
│  • Automatic backups (managed by Render)                        │
│  • Network isolated (only accessible from web service)          │
└─────────────────────────────────────────────────────────────────┘
```

### Deployment Flow

```
Developer → Git Push → GitHub → Render Webhook → Build Phase → Deploy Phase → Live
                                                      │              │
                                                      │              └─ Health Check
                                                      │              └─ Start Gunicorn
                                                      │
                                                      ├─ pip install -r requirements.txt
                                                      ├─ python init_db.py
                                                      └─ mkdir -p storage/pdfs
```

### Component Responsibilities

**Render Load Balancer**
- Terminates SSL/TLS connections (automatic certificate management)
- Redirects HTTP to HTTPS automatically
- Routes requests to web service container
- Provides DDoS protection

**Gunicorn Process Manager**
- Manages 2-4 Flask worker processes (configurable based on plan)
- Uses eventlet worker class for WebSocket support (Flask-SocketIO)
- Handles graceful worker restart on crashes
- Binds to PORT environment variable provided by Render
- Implements request timeouts (120 seconds for long-running requests)

**Flask Application**
- Serves dashboard UI (HTML templates, static assets)
- Provides REST API endpoints for analytics data
- Streams crawler output via WebSocket (Flask-SocketIO)
- Controls crawler subprocess (start/stop via dashboard)
- Serves PDF files from persistent disk
- Implements health check endpoint for Render monitoring

**PostgreSQL Database**
- Stores all research data (papers, authors, faculties, departments)
- Managed by Render (automatic backups, monitoring)
- Connection string provided via DATABASE_URL environment variable
- Network isolated (only accessible from web service)
- Connection pooling configured in SQLAlchemy

**Persistent Disk**
- Mounted at /opt/render/project/storage
- Stores downloaded PDF files
- Survives application restarts and redeployments
- 10GB capacity (expandable to 50GB if needed)

**Crawler Subprocess**
- Spawned by Flask app when user clicks "Start Mining"
- Runs crawl_aggressive.py or crawl_10_validated.py
- Streams output to dashboard via WebSocket
- Respects rate limits configured in environment variables
- Terminates gracefully when dashboard stops it or on disconnect

## Components and Interfaces

### 1. Render Configuration File

**File:** `render.yaml`

This file defines all Render services and their configuration. Render reads this file from the repository root to automatically provision services.

```yaml
services:
  # Web service running the Flask dashboard
  - type: web
    name: uraas-dashboard
    env: python
    region: oregon  # or singapore for closer to Nigeria
    plan: free  # or starter ($7/month) for better performance
    buildCommand: "pip install -r requirements.txt && python init_db.py && mkdir -p storage/pdfs"
    startCommand: "gunicorn --config gunicorn_config.py uraas.dashboard.app:app"
    healthCheckPath: /health
    envVars:
      - key: PYTHON_VERSION
        value: "3.11"
      - key: DATABASE_URL
        fromDatabase:
          name: uraas-db
          property: connectionString
      - key: DASHBOARD_SECRET_KEY
        generateValue: true
      - key: STORAGE_PATH
        value: "/opt/render/project/storage"
      - key: DASHBOARD_PORT
        value: "10000"  # Render's default internal port
    disk:
      name: uraas-storage
      mountPath: /opt/render/project/storage
      sizeGB: 10

databases:
  # PostgreSQL database for storing research data
  - name: uraas-db
    databaseName: uraas_production
    user: uraas_user
    plan: free  # 90-day expiry, but can be renewed
```

**Key Configuration Points:**
- `buildCommand`: Runs during deployment to install dependencies and initialize database
- `startCommand`: Launches Gunicorn with Flask app
- `healthCheckPath`: Render pings this endpoint to check if service is healthy
- `envVars`: Environment variables injected into the application
- `disk`: Persistent storage that survives redeployments
- `fromDatabase`: Automatically injects DATABASE_URL from the PostgreSQL service

### 2. Gunicorn Configuration

**File:** `gunicorn_config.py`

Gunicorn is the production WSGI server that runs the Flask application. This configuration optimizes it for Render's environment and WebSocket support.

```python
import os

# Bind to the PORT environment variable provided by Render
port = os.getenv("PORT", "10000")
bind = f"0.0.0.0:{port}"

# Worker configuration
# Free tier: 2 workers, Starter tier: 4 workers
workers = int(os.getenv("GUNICORN_WORKERS", "2"))

# Use eventlet for WebSocket support (Flask-SocketIO requirement)
worker_class = "eventlet"

# Connection settings
worker_connections = 1000
max_requests = 1000  # Restart workers after 1000 requests (prevents memory leaks)
max_requests_jitter = 50
timeout = 120  # 120 seconds for long-running requests (crawler operations)
keepalive = 5

# Logging
accesslog = "-"  # Log to stdout (Render captures this)
errorlog = "-"   # Log to stderr (Render captures this)
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

# Process naming
proc_name = "uraas-dashboard"

# Graceful shutdown
graceful_timeout = 30

# Preload app for faster worker spawning
preload_app = True
```

**Key Configuration Points:**
- Binds to PORT environment variable (Render requirement)
- Uses eventlet worker class for WebSocket support
- Logs to stdout/stderr (Render captures and displays these)
- Implements graceful shutdown for zero-downtime deployments
- Configures appropriate timeouts for crawler operations

### 3. Health Check Endpoint

**File:** `uraas/dashboard/app.py` (add this route)

```python
from sqlalchemy import text
from datetime import datetime

@app.route('/health')
def health_check():
    """
    Health check endpoint for Render monitoring.
    Returns 200 if operational, 503 if critical services are down.
    """
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "checks": {}
    }
    
    # Check database connectivity
    try:
        session = SessionLocal()
        session.execute(text("SELECT 1"))
        session.close()
        health_status["checks"]["database"] = "ok"
    except Exception as e:
        health_status["checks"]["database"] = f"error: {str(e)}"
        health_status["status"] = "unhealthy"
        app.logger.error(f"Database health check failed: {str(e)}")
    
    # Check disk space on persistent volume
    try:
        storage_path = config.STORAGE_PATH
        if os.path.exists(storage_path):
            stat = os.statvfs(storage_path)
            free_gb = (stat.f_bavail * stat.f_frsize) / (1024**3)
            health_status["checks"]["disk_space_gb"] = round(free_gb, 2)
            if free_gb < 1:  # Less than 1GB free
                health_status["status"] = "unhealthy"
                health_status["checks"]["disk_space"] = "critical"
        else:
            health_status["checks"]["disk_space"] = "storage path not found"
    except Exception as e:
        health_status["checks"]["disk_space"] = f"error: {str(e)}"
    
    # Return appropriate status code
    status_code = 200 if health_status["status"] == "healthy" else 503
    return jsonify(health_status), status_code
```

**Key Points:**
- Returns 200 for healthy, 503 for unhealthy (Render uses this to restart service)
- Checks database connectivity (critical dependency)
- Checks disk space on persistent volume
- Logs errors for debugging

### 4. Production Configuration Module

**File:** `uraas/production_config.py`

This module detects when running on Render and applies production-specific configuration.

```python
import os
import logging

class ProductionConfig:
    """Production configuration for Render deployment."""
    
    @staticmethod
    def is_production():
        """Detect if running on Render."""
        return os.getenv("RENDER") == "true"
    
    @staticmethod
    def apply_config(app):
        """Apply production configuration to Flask app."""
        if not ProductionConfig.is_production():
            return
        
        # Disable debug mode in production
        app.config['DEBUG'] = False
        app.config['TESTING'] = False
        
        # Security settings
        app.config['SESSION_COOKIE_SECURE'] = True  # HTTPS only
        app.config['SESSION_COOKIE_HTTPONLY'] = True  # No JavaScript access
        app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # CSRF protection
        
        # Use production secret key
        app.config['SECRET_KEY'] = os.getenv('DASHBOARD_SECRET_KEY', 'fallback-secret')
        
        # Database configuration
        app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
            'pool_size': 5,
            'pool_recycle': 3600,
            'pool_pre_ping': True,  # Verify connections before using
            'max_overflow': 10
        }
        
        # Storage configuration
        app.config['STORAGE_PATH'] = os.getenv('STORAGE_PATH', '/opt/render/project/storage')
        
        # Logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        )
```

**Key Points:**
- Detects Render environment via RENDER environment variable
- Disables debug mode (security requirement)
- Configures secure session cookies for HTTPS
- Sets up database connection pooling
- Configures logging to stdout (Render captures this)

### 5. Updated App Entry Point

**File:** `uraas/dashboard/app.py` (modify main block)

```python
if __name__ == '__main__':
    # Apply production configuration if on Render
    from uraas.production_config import ProductionConfig
    ProductionConfig.apply_config(app)
    
    # Get port from environment (Render provides this)
    port = int(os.getenv('PORT', config.DASHBOARD_PORT))
    
    # Determine if running in production
    is_production = ProductionConfig.is_production()
    
    if is_production:
        print("=" * 70)
        print("URAAS Dashboard Starting (Production Mode)")
        print("=" * 70)
        print(f"Port: {port}")
        print(f"Database: {os.getenv('DATABASE_URL', 'Not configured')[:50]}...")
        print(f"Storage: {config.STORAGE_PATH}")
        print("=" * 70)
    else:
        print("=" * 70)
        print("URAAS Dashboard Starting (Development Mode)")
        print("=" * 70)
        print(f"Dashboard URL: http://localhost:{port}")
        print("Press Ctrl+C to stop")
        print("=" * 70)
    
    # Run with SocketIO
    socketio.run(
        app,
        host='0.0.0.0',
        port=port,
        debug=not is_production,
        use_reloader=not is_production
    )
```

**Key Points:**
- Applies production config when on Render
- Binds to PORT environment variable
- Disables debug mode and reloader in production
- Logs startup information for debugging

### 6. Database Initialization Script

**File:** `init_db.py` (modify to be idempotent)

```python
import os
from uraas.database import engine, Base, SessionLocal
from uraas.database import Community, Collection

def init_database():
    """Initialize database tables and seed data. Idempotent (safe to run multiple times)."""
    
    print("=" * 60)
    print("Initializing URAAS Database")
    print("=" * 60)
    
    # Create all tables
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("✓ Tables created")
    
    # Seed faculties and departments
    session = SessionLocal()
    try:
        # Check if already seeded
        existing_count = session.query(Community).count()
        if existing_count > 0:
            print(f"✓ Database already seeded ({existing_count} faculties found)")
            return
        
        print("Seeding faculties and departments...")
        
        # Faculty of Science
        science = Community(name="Faculty of Science")
        session.add(science)
        session.flush()
        
        science_depts = [
            "Computer Science", "Mathematics", "Physics", "Chemistry",
            "Biochemistry", "Microbiology", "Botany", "Zoology",
            "Cell Biology and Genetics", "Marine Sciences"
        ]
        for dept_name in science_depts:
            session.add(Collection(name=dept_name, community_id=science.id))
        
        # Faculty of Engineering
        engineering = Community(name="Faculty of Engineering")
        session.add(engineering)
        session.flush()
        
        eng_depts = [
            "Civil Engineering", "Electrical Engineering", "Mechanical Engineering",
            "Chemical Engineering", "Systems Engineering"
        ]
        for dept_name in eng_depts:
            session.add(Collection(name=dept_name, community_id=engineering.id))
        
        # Faculty of Arts
        arts = Community(name="Faculty of Arts")
        session.add(arts)
        session.flush()
        
        arts_depts = [
            "English", "History", "Philosophy", "Linguistics",
            "European Languages", "Creative Arts", "Music"
        ]
        for dept_name in arts_depts:
            session.add(Collection(name=dept_name, community_id=arts.id))
        
        # Add other faculties (Social Sciences, Law, Education, Medicine, etc.)
        # ... (include all 12 UNILAG faculties)
        
        session.commit()
        print(f"✓ Seeded {session.query(Community).count()} faculties")
        print(f"✓ Seeded {session.query(Collection).count()} departments")
        
    except Exception as e:
        session.rollback()
        print(f"✗ Error seeding database: {str(e)}")
        raise
    finally:
        session.close()
    
    print("=" * 60)
    print("Database initialization complete!")
    print("=" * 60)

if __name__ == '__main__':
    init_database()
```

**Key Points:**
- Idempotent (safe to run multiple times)
- Checks if database is already seeded
- Creates all tables using SQLAlchemy
- Seeds UNILAG faculties and departments
- Handles errors gracefully

### 7. Requirements File

**File:** `requirements.txt` (ensure all dependencies are listed)

```txt
Flask==3.0.0
Flask-SocketIO==5.3.5
gunicorn==21.2.0
eventlet==0.33.3
SQLAlchemy==2.0.23
psycopg2-binary==2.9.9
python-dotenv==1.0.0
requests==2.31.0
beautifulsoup4==4.12.2
lxml==4.9.3
scrapy==2.11.0
fuzzywuzzy==0.18.0
python-Levenshtein==0.23.0
```

**Key Points:**
- Includes gunicorn and eventlet for production server
- psycopg2-binary for PostgreSQL connectivity
- All existing dependencies for crawler and analytics

**File:** `uraas/dashboard/static/css/mobile.css`

```css
/* Mobile-first responsive design */
@media (max-width: 768px) {
    .container {
        padding: 10px;
    }
    
    .chart-container {
        width: 100%;
        height: 300px;
    }
    
    .data-table {
        font-size: 14px;
        overflow-x: auto;
    }
    
    .nav-menu {
        flex-direction: column;
    }
    
    .paper-card {
        margin: 10px 0;
    }
}

/* Touch-friendly buttons */
.btn-mobile {
    min-height: 44px;
    min-width: 44px;
    padding: 12px 20px;
}
```

### 8. Backup Script

**File:** `deploy/backup.sh`

```bash
#!/bin/bash
# Automated database backup script (run daily via cron)

BACKUP_DIR="/opt/render/project/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/uraas_backup_$TIMESTAMP.sql"

# Create backup directory
mkdir -p $BACKUP_DIR

# Dump database
pg_dump $DATABASE_URL > $BACKUP_FILE

# Compress backup
gzip $BACKUP_FILE

# Delete backups older than 30 days
find $BACKUP_DIR -name "*.sql.gz" -mtime +30 -delete

echo "Backup completed: ${BACKUP_FILE}.gz"
```

## Data Models

No changes to existing database schema. The current SQLAlchemy models (Communities, Collections, Items, Authors, Files) work as-is with Render's PostgreSQL.

However, we add database indexes for production performance:

```python
# Add to uraas/database.py model definitions

from sqlalchemy import Index

class Item(Base):
    __tablename__ = 'items'
    
    # ... existing columns ...
    
    # Add indexes for frequently queried columns
    __table_args__ = (
        Index('idx_items_publication_date', 'publication_date'),
        Index('idx_items_doi', 'doi'),
        Index('idx_items_created_at', 'created_at'),
        Index('idx_items_title', 'title'),  # For search queries
    )

class Author(Base):
    __tablename__ = 'authors'
    
    # ... existing columns ...
    
    __table_args__ = (
        Index('idx_authors_name', 'name'),
        Index('idx_authors_normalized_name', 'normalized_name'),
    )

class File(Base):
    __tablename__ = 'files'
    
    # ... existing columns ...
    
    __table_args__ = (
        Index('idx_files_item_id', 'item_id'),
        Index('idx_files_sha256', 'sha256_hash'),
    )
```

These indexes improve query performance for:
- Searching papers by title
- Filtering by publication date
- Looking up papers by DOI
- Finding papers by author name
- Retrieving PDF files

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

Based on the prework analysis, most deployment requirements are about infrastructure configuration (handled by Render) or documentation. The testable properties focus on runtime behavior that ensures the application works correctly in production.

### Property 1: Environment Configuration Loading

*For any* required environment variable (DATABASE_URL, SECRET_KEY, STORAGE_PATH), when the application starts, it should successfully load the value from the environment and use it in configuration.

**Validates: Requirements 4.1, 17.4**

### Property 2: Database Initialization Idempotence

*For any* number of times init_db.py is executed, the database should end up in the same valid state with all required tables and seed data present, without errors or duplicate data.

**Validates: Requirements 9.3, 12.4, 12.5**

### Property 3: Secret Redaction in Logs

*For any* log message generated by the application, the log output should not contain any values from secret environment variables (SECRET_KEY, DATABASE_URL password component, API keys).

**Validates: Requirements 4.4, 10.4**

### Property 4: Health Check Database Verification

*For any* health check request to /health, when the database is accessible, the endpoint should return HTTP 200 with database status "ok", and when the database is inaccessible, it should return HTTP 503 with database status "error".

**Validates: Requirements 7.2, 7.3, 7.4**

### Property 5: Static Asset Cache Headers

*For any* static asset request (CSS, JavaScript, images), the response should include appropriate Cache-Control headers to enable browser caching.

**Validates: Requirements 13.2**

### Property 6: Log Format Consistency

*For any* log entry generated by the application, it should include a timestamp, log level (INFO, WARNING, ERROR), and the log message.

**Validates: Requirements 10.3**

## Error Handling

The application implements comprehensive error handling for production:

**Database Connection Failures**
- Health check returns 503 when database is unavailable
- API endpoints return 500 with user-friendly error messages
- Detailed errors logged server-side for debugging
- SQLAlchemy pool_pre_ping ensures stale connections are detected

**Missing PDF Files**
- /api/papers/{id}/download returns 404 with clear message
- Logs file path for debugging
- Suggests checking storage volume mount

**Environment Configuration Errors**
- Application fails to start if required variables are missing
- Clear error message indicates which variables are missing
- Prevents partial startup with invalid configuration

**Crawler Subprocess Errors**
- Crawler errors streamed to dashboard via WebSocket
- Crawler can be restarted from dashboard after errors
- Subprocess cleanup on disconnect prevents zombie processes

**WebSocket Connection Errors**
- Graceful handling of client disconnects
- Crawler stops when all clients disconnect
- Reconnection supported without restarting crawler

**HTTP Error Pages**
- Custom 404 page for not found errors
- Custom 500 page for server errors (no stack traces to users)
- Stack traces logged server-side for debugging

## Testing Strategy

### Unit Testing

Unit tests focus on specific examples and edge cases for deployment-related functionality:

**Configuration Tests**
- Test environment variable loading with various values
- Test production config detection (RENDER=true)
- Test default values when optional variables are missing
- Test configuration validation catches missing required variables

**Health Check Tests**
- Test /health returns 200 when database is accessible
- Test /health returns 503 when database is unavailable
- Test health check includes disk space information
- Test health check response format

**Database Initialization Tests**
- Test init_db.py creates all required tables
- Test init_db.py seeds faculties and departments
- Test init_db.py is idempotent (can run multiple times)
- Test init_db.py skips seeding if data already exists

**Logging Tests**
- Test secrets are redacted from log output
- Test log format includes timestamp and level
- Test errors are logged with stack traces
- Test logs go to stdout/stderr

**Error Handling Tests**
- Test 404 handler returns custom page
- Test 500 handler returns user-friendly message
- Test database error handling in API endpoints
- Test missing PDF file handling

### Property-Based Testing

Property tests verify universal behaviors across many generated inputs:

**Property Test 1: Environment Configuration Loading**
```python
# Test: For any required environment variable, the app loads it correctly
@given(st.dictionaries(
    keys=st.sampled_from(['DATABASE_URL', 'SECRET_KEY', 'STORAGE_PATH']),
    values=st.text(min_size=1)
))
def test_env_var_loading(env_vars):
    """Feature: live-deployment, Property 1: Environment Configuration Loading"""
    # Set environment variables
    for key, value in env_vars.items():
        os.environ[key] = value
    
    # Load configuration
    config = load_config()
    
    # Verify all variables are loaded
    for key, value in env_vars.items():
        assert getattr(config, key) == value
```

**Property Test 2: Database Initialization Idempotence**
```python
# Test: For any number of init_db runs, database ends in same state
@given(st.integers(min_value=1, max_value=5))
def test_init_db_idempotence(num_runs):
    """Feature: live-deployment, Property 2: Database Initialization Idempotence"""
    # Run init_db multiple times
    for _ in range(num_runs):
        init_database()
    
    # Verify database state
    session = SessionLocal()
    faculty_count = session.query(Community).count()
    dept_count = session.query(Collection).count()
    session.close()
    
    # Should have exactly 12 faculties and 80+ departments
    assert faculty_count == 12
    assert dept_count >= 80
```

**Property Test 3: Secret Redaction in Logs**
```python
# Test: For any log message, secrets are not exposed
@given(st.text(min_size=10))
def test_secret_redaction(secret_value):
    """Feature: live-deployment, Property 3: Secret Redaction in Logs"""
    # Set secret environment variable
    os.environ['SECRET_KEY'] = secret_value
    
    # Trigger logging (simulate error)
    with capture_logs() as logs:
        try:
            # Code that might log the secret
            app.logger.error(f"Error with config: {config}")
        except:
            pass
    
    # Verify secret is not in logs
    log_output = '\n'.join(logs)
    assert secret_value not in log_output
```

**Property Test 4: Health Check Database Verification**
```python
# Test: Health check correctly reports database status
@given(st.booleans())
def test_health_check_database(database_available):
    """Feature: live-deployment, Property 4: Health Check Database Verification"""
    # Mock database availability
    if database_available:
        mock_database_connection(success=True)
    else:
        mock_database_connection(success=False)
    
    # Call health check
    response = client.get('/health')
    
    # Verify response
    if database_available:
        assert response.status_code == 200
        assert response.json['checks']['database'] == 'ok'
    else:
        assert response.status_code == 503
        assert 'error' in response.json['checks']['database']
```

**Property Test 5: Static Asset Cache Headers**
```python
# Test: All static assets have cache headers
@given(st.sampled_from(['style.css', 'app.js', 'logo.png']))
def test_static_asset_caching(asset_filename):
    """Feature: live-deployment, Property 5: Static Asset Cache Headers"""
    # Request static asset
    response = client.get(f'/static/{asset_filename}')
    
    # Verify cache headers are present
    assert 'Cache-Control' in response.headers
    assert 'max-age' in response.headers['Cache-Control']
```

**Property Test 6: Log Format Consistency**
```python
# Test: All log entries have consistent format
@given(st.sampled_from(['INFO', 'WARNING', 'ERROR']), st.text(min_size=1))
def test_log_format(log_level, message):
    """Feature: live-deployment, Property 6: Log Format Consistency"""
    # Generate log entry
    with capture_logs() as logs:
        logger = logging.getLogger('uraas')
        getattr(logger, log_level.lower())(message)
    
    # Verify format
    log_entry = logs[0]
    assert re.match(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}', log_entry)  # Timestamp
    assert log_level in log_entry  # Log level
    assert message in log_entry  # Message
```

### Integration Testing

Integration tests verify the complete deployment works on Render:

**Deployment Verification**
- Deploy to Render staging environment
- Verify application starts successfully
- Verify health check returns 200
- Verify database connection works
- Verify persistent disk is mounted
- Verify PDFs can be uploaded and downloaded

**End-to-End Tests**
- Load dashboard in browser
- Verify all pages render correctly
- Start crawler from dashboard
- Verify WebSocket streaming works
- Verify papers are stored in database
- Verify PDFs are stored on persistent disk
- Verify analytics endpoints return data

### Test Configuration

- Unit tests: Run on every commit (GitHub Actions)
- Property tests: Minimum 100 iterations per test
- Integration tests: Run before production deployment
- All tests must pass before merging to main branch

## Deployment Checklist

Before deploying to Render:

1. ✓ render.yaml file exists in repository root
2. ✓ gunicorn_config.py configured for eventlet workers
3. ✓ Health check endpoint implemented at /health
4. ✓ Production config module detects Render environment
5. ✓ init_db.py is idempotent
6. ✓ All secrets loaded from environment variables
7. ✓ Logging configured to stdout/stderr
8. ✓ Static assets have cache headers
9. ✓ Error pages implemented (404, 500)
10. ✓ Staff validation data files included in repository
11. ✓ requirements.txt includes all dependencies
12. ✓ DEPLOYMENT.md documentation complete
13. ✓ All unit tests passing
14. ✓ All property tests passing (100+ iterations each)

After deployment:

1. ✓ Verify health check returns 200
2. ✓ Verify database connection works
3. ✓ Verify persistent disk mounted at correct path
4. ✓ Verify dashboard loads in browser
5. ✓ Verify WebSocket connection works
6. ✓ Verify crawler can start/stop
7. ✓ Verify PDFs can be downloaded
8. ✓ Verify mobile responsive layout works
9. ✓ Monitor logs for errors
10. ✓ Test on mobile device


# Implementation Plan: Live Deployment to Render

## Overview

This plan implements the deployment of the URAAS Flask dashboard to Render.com as a production web service. The implementation covers Render configuration, production settings, health monitoring, database initialization, and deployment automation. All tasks build incrementally to create a fully functional production deployment.

## Tasks

- [ ] 1. Create Render configuration and deployment files
  - [ ] 1.1 Create render.yaml configuration file
    - Define web service with Python environment, build/start commands
    - Configure PostgreSQL database service with connection string injection
    - Define persistent disk (10GB) for PDF storage at /opt/render/project/storage
    - Set environment variables (PYTHON_VERSION, DATABASE_URL, SECRET_KEY, STORAGE_PATH)
    - Configure health check path to /health
    - _Requirements: 16.1, 16.2, 16.3, 16.4, 16.5_
  
  - [ ] 1.2 Create Gunicorn configuration file (gunicorn_config.py)
    - Bind to PORT environment variable (Render requirement)
    - Configure 2 workers with eventlet worker class for WebSocket support
    - Set timeout to 120 seconds for long-running crawler operations
    - Configure logging to stdout/stderr for Render log capture
    - Enable graceful shutdown with 30-second timeout
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 20.1, 20.4_
  
  - [ ]* 1.3 Write property test for environment configuration loading
    - **Property 1: Environment Configuration Loading**
    - **Validates: Requirements 4.1, 17.4**
    - Test that required environment variables (DATABASE_URL, SECRET_KEY, STORAGE_PATH) are loaded correctly
    - _Requirements: 4.1, 17.4_

- [ ] 2. Implement production configuration module
  - [ ] 2.1 Create production_config.py module
    - Implement is_production() to detect Render environment (RENDER=true)
    - Implement apply_config() to set production Flask settings
    - Disable debug mode and enable secure session cookies (HTTPS only)
    - Configure SQLAlchemy connection pooling (5 connections, pre-ping enabled)
    - Set up logging to stdout with INFO level and timestamp format
    - _Requirements: 17.1, 17.2, 17.3, 17.4, 17.5, 10.1, 10.3_
  
  - [ ]* 2.2 Write property test for secret redaction in logs
    - **Property 3: Secret Redaction in Logs**
    - **Validates: Requirements 4.4, 10.4**
    - Test that secret values never appear in log output
    - _Requirements: 4.4, 10.4_

- [ ] 3. Implement health check endpoint
  - [ ] 3.1 Add /health route to app.py
    - Return JSON with status, timestamp, and checks object
    - Check database connectivity with SELECT 1 query
    - Check disk space on persistent volume (warn if < 1GB free)
    - Return HTTP 200 if healthy, HTTP 503 if unhealthy
    - Log errors when health checks fail
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_
  
  - [ ]* 3.2 Write property test for health check database verification
    - **Property 4: Health Check Database Verification**
    - **Validates: Requirements 7.2, 7.3, 7.4**
    - Test health check returns 200 when database is accessible, 503 when unavailable
    - _Requirements: 7.2, 7.3, 7.4_

- [ ] 4. Update app.py for production deployment
  - [ ] 4.1 Modify app entry point to apply production config
    - Import and call ProductionConfig.apply_config(app) on startup
    - Read PORT from environment variable with fallback to config.DASHBOARD_PORT
    - Detect production mode and disable debug/reloader accordingly
    - Log startup information (port, database URL prefix, storage path)
    - Bind to 0.0.0.0 for Render routing
    - _Requirements: 1.3, 17.1, 17.2, 20.1, 20.2, 20.3, 20.5_
  
  - [ ] 4.2 Add custom error handlers for 404 and 500
    - Implement @app.errorhandler(404) with user-friendly message and navigation links
    - Implement @app.errorhandler(500) with generic error message (no stack traces to users)
    - Log detailed error information server-side for debugging
    - _Requirements: 15.1, 15.2, 15.4, 15.5_

- [ ] 5. Make database initialization idempotent
  - [ ] 5.1 Update init_db.py to be safely re-runnable
    - Check if tables already exist before creating
    - Check if seed data (faculties/departments) already exists before inserting
    - Use try-except with rollback for error handling
    - Log clear status messages (creating tables, already seeded, etc.)
    - Ensure script exits successfully even if data already exists
    - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5_
  
  - [ ]* 5.2 Write property test for database initialization idempotence
    - **Property 2: Database Initialization Idempotence**
    - **Validates: Requirements 9.3, 12.4, 12.5**
    - Test that running init_db.py multiple times produces same valid state
    - _Requirements: 9.3, 12.4, 12.5_

- [ ] 6. Checkpoint - Verify core deployment files
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 7. Configure static asset serving and caching
  - [ ] 7.1 Add cache headers to static asset responses
    - Configure Flask to send Cache-Control headers for static files
    - Set max-age to 3600 seconds (1 hour) for CSS, JS, images
    - Enable gzip compression for text-based assets
    - _Requirements: 13.1, 13.2, 13.3, 13.5_
  
  - [ ]* 7.2 Write property test for static asset cache headers
    - **Property 5: Static Asset Cache Headers**
    - **Validates: Requirements 13.2**
    - Test that all static assets include appropriate Cache-Control headers
    - _Requirements: 13.2_

- [ ] 8. Add database indexes for production performance
  - [ ] 8.1 Add indexes to database models
    - Add indexes to Item model (publication_date, doi, created_at, title)
    - Add indexes to Author model (name, normalized_name)
    - Add indexes to File model (item_id, sha256_hash)
    - Update database.py with __table_args__ for each model
    - _Requirements: 3.1, 3.4_

- [ ] 9. Update requirements.txt for production
  - [ ] 9.1 Ensure all production dependencies are listed
    - Verify gunicorn==21.2.0 is included
    - Verify eventlet==0.33.3 is included for WebSocket support
    - Verify psycopg2-binary==2.9.9 is included for PostgreSQL
    - Verify all existing dependencies (Flask, SQLAlchemy, etc.) are listed
    - Pin all versions for reproducible builds
    - _Requirements: 5.1, 5.4, 9.2_

- [ ] 10. Implement mobile-responsive CSS
  - [ ] 10.1 Create or update mobile.css for responsive design
    - Add media query for screens < 768px width
    - Make containers use full width with reduced padding on mobile
    - Set chart containers to 100% width and 300px height on mobile
    - Make tables horizontally scrollable on mobile
    - Ensure buttons are touch-friendly (min 44x44 pixels)
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5_

- [ ] 11. Create deployment documentation
  - [ ] 11.1 Create DEPLOYMENT.md with step-by-step instructions
    - Document prerequisites (GitHub account, Render account)
    - Provide step-by-step Render service creation instructions
    - List all required environment variables with descriptions
    - Document how to connect GitHub repository to Render
    - Include troubleshooting section for common deployment issues
    - Document how to view logs and monitor health
    - _Requirements: 19.1, 19.2, 19.3, 19.4, 19.5_

- [ ] 12. Verify staff validation data is included
  - [ ] 12.1 Ensure staff data files are in repository
    - Verify data/unilag_staff.json exists and is committed
    - Verify data/staff_department_map.json exists and is committed
    - Test that staff_validator loads data correctly in production mode
    - _Requirements: 18.1, 18.2, 18.3, 18.4_

- [ ] 13. Add logging configuration
  - [ ] 13.1 Configure production logging in production_config.py
    - Set up logging to stdout/stderr for Render capture
    - Configure log format with timestamp, level, logger name, and message
    - Set log level to INFO for production
    - Ensure error logs include stack traces
    - _Requirements: 10.1, 10.2, 10.3, 10.5_
  
  - [ ]* 13.2 Write property test for log format consistency
    - **Property 6: Log Format Consistency**
    - **Validates: Requirements 10.3**
    - Test that all log entries include timestamp, log level, and message
    - _Requirements: 10.3_

- [ ] 14. Checkpoint - Verify all components integrated
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 15. Create deployment verification script
  - [ ] 15.1 Create verify_deployment.py script
    - Check that /health endpoint returns 200
    - Verify database connection works
    - Verify persistent disk is mounted at correct path
    - Check that environment variables are loaded
    - Test that static assets are served with cache headers
    - _Requirements: 7.1, 3.3, 6.3, 4.1, 13.2_

- [ ] 16. Final integration and testing
  - [ ] 16.1 Test complete deployment flow locally
    - Set RENDER=true environment variable to simulate production
    - Run gunicorn with production config
    - Verify health check works
    - Verify database connection works
    - Verify WebSocket streaming works
    - Test crawler start/stop functionality
    - _Requirements: 1.1, 5.1, 7.1, 3.1, 14.1, 8.1_
  
  - [ ]* 16.2 Write integration tests for deployment
    - Test that application starts successfully with production config
    - Test that all API endpoints return valid responses
    - Test that WebSocket connection works
    - Test that PDF download works
    - _Requirements: 1.1, 3.1, 14.1, 6.1_

- [ ] 17. Final checkpoint - Deployment ready
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties
- All code examples use Python (Flask, SQLAlchemy, Gunicorn)
- The deployment uses Render.com's free tier (web service + PostgreSQL + persistent disk)
- WebSocket support requires eventlet worker class in Gunicorn
- Health checks enable automatic service restart on failures
- All secrets must be configured as Render environment variables
- The persistent disk ensures PDFs survive redeployments

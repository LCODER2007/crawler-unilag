# Requirements Document

## Introduction

This document specifies the requirements for deploying the URAAS (University Research Analytics System) Flask dashboard to Render.com as a live production environment. The system currently runs locally with PostgreSQL/SQLite database, staff validation, crawler components, and Docker configuration. The deployment will enable public access via HTTPS while maintaining security, performance, and data integrity.

## Glossary

- **URAAS_System**: The University Research Analytics System including Flask dashboard, PostgreSQL database, crawler components, and all supporting services
- **Render_Platform**: Render.com cloud hosting platform providing web services, databases, and persistent storage
- **Web_Service**: Render's managed web service running the Flask application with Gunicorn
- **Production_Environment**: The live Render environment accessible to public users via internet
- **Mobile_Client**: Web browsers on mobile devices (iOS Safari, Android Chrome, etc.)
- **Dashboard_Service**: The Flask web application (uraas/dashboard/app.py) serving the analytics dashboard
- **Database_Service**: PostgreSQL database instance managed by Render
- **Crawler_Service**: Background subprocess for harvesting research papers, controlled via dashboard
- **Static_Assets**: CSS, JavaScript, images, and other frontend resources served by Flask
- **Environment_Variables**: Render environment configuration including secrets, database URLs, and API keys
- **Health_Endpoint**: HTTP endpoint (/health) that Render uses to check service availability
- **Persistent_Disk**: Render disk storage mounted to the web service for PDF files
- **Build_Command**: Shell command that Render executes to prepare the application for deployment
- **Start_Command**: Shell command that Render executes to run the application (gunicorn)

## Requirements

### Requirement 1: Render Web Service Deployment

**User Story:** As a developer, I want to deploy the Flask dashboard to Render as a web service, so that it is accessible via a public URL.

#### Acceptance Criteria

1. THE URAAS_System SHALL be deployed as a Render Web_Service using the Python environment
2. THE Web_Service SHALL use Gunicorn as the WSGI server with at least 2 worker processes
3. WHEN the Web_Service starts, THE Dashboard_Service SHALL bind to the port specified by Render's PORT environment variable
4. THE Web_Service SHALL execute a Build_Command that installs dependencies from requirements.txt
5. THE Web_Service SHALL execute a Start_Command that launches Gunicorn with the Flask app

### Requirement 2: Automatic HTTPS Configuration

**User Story:** As a user, I want all connections encrypted with HTTPS, so that my data is protected.

#### Acceptance Criteria

1. THE Render_Platform SHALL automatically provision and manage SSL certificates for the Web_Service
2. THE Web_Service SHALL be accessible via HTTPS without manual certificate configuration
3. THE Render_Platform SHALL automatically redirect HTTP requests to HTTPS
4. THE SSL certificate SHALL be trusted by major browsers (Chrome, Firefox, Safari, Edge)
5. WHEN the SSL certificate approaches expiration, THE Render_Platform SHALL automatically renew it

### Requirement 3: Render PostgreSQL Database

**User Story:** As a system administrator, I want the database hosted on Render's managed PostgreSQL service, so that data persists reliably.

#### Acceptance Criteria

1. THE Database_Service SHALL use Render's managed PostgreSQL database
2. THE Database_Service SHALL be accessible only from the Web_Service (network isolation)
3. THE URAAS_System SHALL connect to the database using the DATABASE_URL Environment_Variables provided by Render
4. THE Database_Service SHALL implement connection pooling with minimum 5 connections
5. WHEN the Web_Service restarts, THE URAAS_System SHALL reconnect to the Database_Service automatically

### Requirement 4: Environment Variables Configuration

**User Story:** As a developer, I want production secrets managed via Render environment variables, so that sensitive credentials are not exposed in code.

#### Acceptance Criteria

1. THE URAAS_System SHALL load all configuration from Environment_Variables set in Render dashboard
2. THE Environment_Variables SHALL include DATABASE_URL, SECRET_KEY, and any API keys
3. THE URAAS_System SHALL NOT hardcode any production credentials in source code
4. THE URAAS_System SHALL NOT log or display secret values in error messages or logs
5. WHEN required Environment_Variables are missing, THE URAAS_System SHALL fail to start with a clear error message

### Requirement 5: Gunicorn Process Management

**User Story:** As a system administrator, I want Gunicorn managing Flask worker processes, so that the application handles load and crashes gracefully.

#### Acceptance Criteria

1. THE Web_Service SHALL run Flask behind Gunicorn WSGI server
2. THE Gunicorn configuration SHALL spawn at least 2 worker processes
3. WHEN a worker process crashes, Gunicorn SHALL restart it automatically
4. THE Gunicorn configuration SHALL use eventlet or gevent worker class for WebSocket support
5. THE Gunicorn configuration SHALL set appropriate timeouts (120 seconds) for long-running requests

### Requirement 6: Persistent Disk for PDF Storage

**User Story:** As a researcher, I want downloaded PDFs to persist across deployments, so that I don't lose access to research papers.

#### Acceptance Criteria

1. THE Web_Service SHALL have a Persistent_Disk mounted for PDF storage
2. THE Persistent_Disk SHALL have at least 10GB capacity (expandable to 50GB)
3. THE Persistent_Disk SHALL be mounted at a consistent path (e.g., /opt/render/project/storage)
4. WHEN the Web_Service redeploys, THE URAAS_System SHALL maintain access to all previously stored PDFs
5. THE URAAS_System SHALL configure the PDF storage path to use the Persistent_Disk mount point

### Requirement 7: Health Check Endpoint

**User Story:** As a system administrator, I want Render to monitor application health, so that unhealthy instances are automatically restarted.

#### Acceptance Criteria

1. THE Dashboard_Service SHALL expose a Health_Endpoint at /health
2. THE Health_Endpoint SHALL return HTTP 200 when the application is operational
3. THE Health_Endpoint SHALL check Database_Service connectivity before returning success
4. THE Health_Endpoint SHALL return HTTP 503 when critical services (database) are unavailable
5. THE Render_Platform SHALL use the Health_Endpoint to determine when to restart the Web_Service

### Requirement 8: Crawler Subprocess Control

**User Story:** As a system administrator, I want the crawler running as a subprocess controlled via the dashboard, so that it harvests papers without blocking the web interface.

#### Acceptance Criteria

1. THE Crawler_Service SHALL run as a subprocess spawned by the Dashboard_Service
2. THE Dashboard_Service SHALL provide start/stop controls for the Crawler_Service via the web interface
3. WHEN the Crawler_Service is running, THE Dashboard_Service SHALL stream crawler output to connected clients via WebSocket
4. THE Crawler_Service SHALL respect rate limits and retry logic configured in the application
5. WHEN the Web_Service restarts, THE Crawler_Service SHALL stop gracefully and be restartable from the dashboard

### Requirement 9: Build and Deployment Automation

**User Story:** As a developer, I want automated builds on git push, so that deployments are fast and consistent.

#### Acceptance Criteria

1. THE Render_Platform SHALL automatically build and deploy when code is pushed to the connected Git repository
2. THE Build_Command SHALL install all Python dependencies from requirements.txt
3. THE Build_Command SHALL run database initialization scripts (init_db.py) if needed
4. THE Build_Command SHALL create necessary directories (storage/pdfs)
5. WHEN the build fails, THE Render_Platform SHALL keep the previous working version running

### Requirement 10: Logging and Error Handling

**User Story:** As a system administrator, I want application logs accessible via Render dashboard, so that I can diagnose issues.

#### Acceptance Criteria

1. THE Dashboard_Service SHALL log all errors and warnings to stdout/stderr
2. THE Render_Platform SHALL capture and display logs in the Render dashboard
3. THE Dashboard_Service SHALL log timestamps, log levels, and error messages
4. THE Dashboard_Service SHALL NOT log sensitive information (passwords, API keys, tokens)
5. WHEN an unhandled exception occurs, THE Dashboard_Service SHALL log the full stack trace

### Requirement 11: Mobile-Responsive Interface

**User Story:** As a mobile user, I want the dashboard optimized for my device, so that I can view analytics comfortably on my phone.

#### Acceptance Criteria

1. WHEN accessed from a Mobile_Client with screen width less than 768px, THE Dashboard_Service SHALL render a mobile-optimized layout
2. THE Dashboard_Service SHALL use responsive CSS that adapts to different screen sizes
3. THE Dashboard_Service SHALL render charts at appropriate sizes for mobile screens
4. THE Dashboard_Service SHALL use touch-friendly button sizes (minimum 44x44 pixels)
5. WHEN viewing tables on Mobile_Client, THE Dashboard_Service SHALL enable horizontal scrolling for wide tables

### Requirement 12: Database Initialization

**User Story:** As a developer, I want the database automatically initialized on first deployment, so that the application starts with required data.

#### Acceptance Criteria

1. THE Build_Command SHALL execute init_db.py to create database tables
2. THE init_db.py script SHALL create all required tables (communities, collections, items, authors, files)
3. THE init_db.py script SHALL seed the database with UNILAG faculties and departments
4. THE init_db.py script SHALL be idempotent (safe to run multiple times)
5. WHEN tables already exist, THE init_db.py script SHALL skip creation without errors

### Requirement 13: Static Asset Serving

**User Story:** As a user, I want fast page loads, so that I can access the dashboard quickly.

#### Acceptance Criteria

1. THE Dashboard_Service SHALL serve Static_Assets (CSS, JavaScript, images) via Flask
2. THE Dashboard_Service SHALL set appropriate cache headers for Static_Assets (1 hour)
3. THE Dashboard_Service SHALL enable gzip compression for text-based Static_Assets
4. THE Dashboard_Service SHALL serve Static_Assets from the static/ directory
5. WHEN Static_Assets are requested, THE Dashboard_Service SHALL return them within 500ms

### Requirement 14: WebSocket Support for Crawler Output

**User Story:** As a user, I want to see real-time crawler output, so that I can monitor harvesting progress.

#### Acceptance Criteria

1. THE Dashboard_Service SHALL use Flask-SocketIO for WebSocket communication
2. THE Gunicorn configuration SHALL use eventlet or gevent worker class to support WebSocket
3. WHEN the Crawler_Service is running, THE Dashboard_Service SHALL emit crawler output via WebSocket
4. THE Dashboard_Service SHALL emit crawl_status events (initializing, running, stopped)
5. WHEN a client connects, THE Dashboard_Service SHALL send the current crawler status

### Requirement 15: Error Pages and User Feedback

**User Story:** As a user, I want clear error messages when something goes wrong, so that I understand what happened.

#### Acceptance Criteria

1. WHEN a server error occurs, THE Dashboard_Service SHALL display a user-friendly error page (not stack traces)
2. WHEN the Database_Service is unavailable, THE Dashboard_Service SHALL display "Service temporarily unavailable"
3. WHEN a PDF download fails, THE Dashboard_Service SHALL display "PDF not available" with error details
4. THE Dashboard_Service SHALL log detailed error information server-side while showing simplified messages to users
5. WHEN a 404 error occurs, THE Dashboard_Service SHALL display a custom 404 page with navigation links

### Requirement 16: Render Configuration File

**User Story:** As a developer, I want a render.yaml configuration file, so that Render knows how to deploy the application.

#### Acceptance Criteria

1. THE URAAS_System SHALL include a render.yaml file in the repository root
2. THE render.yaml SHALL define a web service with Python environment
3. THE render.yaml SHALL define a PostgreSQL database service
4. THE render.yaml SHALL define a persistent disk for PDF storage
5. THE render.yaml SHALL specify Build_Command and Start_Command for the web service

### Requirement 17: Production Configuration Module

**User Story:** As a developer, I want production-specific configuration separate from development config, so that settings are appropriate for each environment.

#### Acceptance Criteria

1. THE URAAS_System SHALL detect when running on Render via environment variables
2. THE URAAS_System SHALL use production configuration when RENDER environment variable is set
3. THE production configuration SHALL disable Flask debug mode
4. THE production configuration SHALL use the DATABASE_URL from Environment_Variables
5. THE production configuration SHALL set appropriate timeouts and connection pool sizes

### Requirement 18: Staff Validator Data Persistence

**User Story:** As a system administrator, I want staff validation data available in production, so that the crawler can validate UNILAG authors.

#### Acceptance Criteria

1. THE URAAS_System SHALL include staff validation data files (data/unilag_staff.json, data/staff_department_map.json) in the deployment
2. THE staff_validator module SHALL load staff data from the data/ directory
3. THE staff_validator SHALL function correctly in the production environment
4. WHEN the Crawler_Service runs, THE staff_validator SHALL validate authors against the staff list
5. THE staff validation data SHALL be updateable by replacing files and redeploying

### Requirement 19: Deployment Documentation

**User Story:** As a developer, I want step-by-step deployment instructions, so that I can deploy to Render successfully.

#### Acceptance Criteria

1. THE URAAS_System SHALL include a DEPLOYMENT.md file with Render-specific instructions
2. THE DEPLOYMENT.md SHALL document all required Environment_Variables
3. THE DEPLOYMENT.md SHALL provide step-by-step instructions for creating Render services
4. THE DEPLOYMENT.md SHALL document how to connect the GitHub repository to Render
5. THE DEPLOYMENT.md SHALL include troubleshooting steps for common deployment issues

### Requirement 20: Port Binding Configuration

**User Story:** As a developer, I want the Flask app to bind to the correct port, so that Render can route traffic to it.

#### Acceptance Criteria

1. THE Dashboard_Service SHALL read the PORT environment variable provided by Render
2. THE Dashboard_Service SHALL bind to 0.0.0.0 (all interfaces) on the specified PORT
3. WHEN the PORT environment variable is not set, THE Dashboard_Service SHALL default to port 8080
4. THE Gunicorn Start_Command SHALL use the PORT environment variable
5. THE Dashboard_Service SHALL log the port it is listening on at startup

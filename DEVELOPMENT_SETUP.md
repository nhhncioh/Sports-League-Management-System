# Development Setup Guide

This guide will help you set up and run the Sports League Management System (SLMS) for development.

## Quick Start

### Option 1: Using the npm-style scripts (recommended)
```bash
npm run dev
```

### Option 2: Using Python directly
```bash
python run_dev.py
```

### Option 3: Using Flask commands
```bash
# Set environment variable
set FLASK_APP=main.py  # Windows
export FLASK_APP=main.py  # Linux/Mac

# Run the development server
flask run --debug
```

### Option 4: Using the Windows batch file
```cmd
run_dev.bat
```

## Prerequisites

1. **Python 3.8+** - [Download Python](https://python.org/downloads)
2. **Git** - [Download Git](https://git-scm.com/downloads)

## Setup Instructions

### 1. Clone the Repository
```bash
git clone <repository-url>
cd Sports-League-Management-System
```

### 2. Create Virtual Environment (Recommended)
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Set Up Environment Variables
The `.env` file has been created for you with development defaults. You can modify it if needed:

```bash
# Flask configuration
FLASK_APP=main.py
FLASK_ENV=development
FLASK_DEBUG=1
SECRET_KEY=dev-secret-key-change-in-production

# Database configuration (SQLite for local development)
DATABASE_URL=sqlite:///sports_league.db
```

### 5. Initialize Database
The database will be automatically created when you first run the app, but you can also initialize it manually:

```bash
flask db upgrade  # If migrations exist
# or
python -c "from slms import create_app; from slms.extensions import db; app = create_app(); app.app_context().push(); db.create_all()"
```

### 6. Run the Development Server
```bash
npm run dev
```

The server will start at `http://localhost:5000`

## Creating Demo Data

To quickly set up demo data for testing:

```bash
# Create a demo organization with admin user
npm run create-org
# or manually:
flask org:create --name "Demo League" --slug demo --admin-email admin@demo.com --admin-password password123

# Seed demo data (teams, players, games, etc.)
npm run seed-demo
# or manually:
flask seed:demo --org demo
```

After seeding, you have multiple options to select the tenant (organization):

- Subdomain (if your OS resolves subdomains of localhost):
  - Public: http://demo.localhost:5000
  - Admin: http://demo.localhost:5000/admin (login: admin@demo.com / password123)
- Query parameter (works everywhere):
  - Public: http://localhost:5000/?org=demo
  - Admin: http://localhost:5000/admin?org=demo
- Default org slug (set in .env):
  - Add `DEFAULT_ORG_SLUG=demo` to your `.env`, then visit http://localhost:5000

## Available NPM Scripts

Even though this is a Python Flask app, we've added `package.json` for convenience:

```bash
npm run dev          # Start development server
npm run start        # Start development server (alias)
npm run setup        # Install Python dependencies
npm run create-org   # Create demo organization
npm run seed-demo    # Seed demo data
npm run test         # Run Python tests
npm run test-cli     # Test CLI commands
npm run security-test # Run security tests
```

## Development Workflow

### 1. Basic Development
```bash
# Start the development server
npm run dev

# In another terminal, create demo data
npm run create-org
npm run seed-demo

# Visit http://demo.localhost:5000 or http://localhost:5000/?org=demo
```

### 2. Database Changes
```bash
# Create a new migration
flask db migrate -m "Description of changes"

# Apply migrations
flask db upgrade
```

### 3. Testing CLI Commands
```bash
# Test all CLI commands
npm run test-cli

# Or test individual commands
flask org:list
flask seed:demo --org demo
flask export:season --season <id> --what all
```

## Project Structure

```
Sports-League-Management-System/
├── slms/                    # Main application package
│   ├── __init__.py         # App factory
│   ├── models/             # Database models
│   ├── blueprints/         # Route blueprints
│   ├── templates/          # Jinja2 templates
│   ├── static/             # Static files (CSS, JS, images)
│   ├── commands/           # CLI commands
│   └── extensions.py       # Flask extensions
├── migrations/             # Database migrations
├── tests/                  # Test files
├── main.py                # Application entry point
├── requirements.txt       # Python dependencies
├── .env                   # Environment variables
├── run_dev.py            # Development server runner
├── run_dev.bat           # Windows development launcher
└── package.json          # NPM scripts for convenience
```

## Database Configuration

### Development (SQLite)
The default development setup uses SQLite for simplicity:
```
DATABASE_URL=sqlite:///sports_league.db
```

### Production (PostgreSQL)
For production, use PostgreSQL:
```
DATABASE_URL=postgresql://user:password@localhost:5432/sports_league
```

### Docker (PostgreSQL)
To use the Docker setup:
```bash
docker-compose up -d
```

## Common Issues and Solutions

### Issue: "Module not found" errors
**Solution**: Make sure you're in the virtual environment and dependencies are installed:
```bash
# Activate virtual environment
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt
```

### Issue: Database errors
**Solution**: Initialize or recreate the database:
```bash
# Delete the database file
rm sports_league.db  # Linux/Mac
del sports_league.db  # Windows

# Restart the application (database will be recreated)
npm run dev
```

### Issue: Port 5000 already in use
**Solution**: Kill the process using port 5000 or use a different port:
```bash
# Kill process on port 5000
netstat -ano | findstr :5000  # Windows
lsof -ti:5000 | xargs kill -9  # Linux/Mac

# Or use a different port
flask run --port 5001
```

### Issue: Permission errors on Windows
**Solution**: Run command prompt as administrator or use PowerShell with execution policy:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

## Environment Variables Reference

| Variable | Description | Default |
|----------|-------------|---------|
| `FLASK_APP` | Flask application entry point | `main.py` |
| `FLASK_ENV` | Flask environment | `development` |
| `FLASK_DEBUG` | Enable debug mode | `1` |
| `SECRET_KEY` | Secret key for sessions | `dev-secret-key...` |
| `DATABASE_URL` | Database connection string | `sqlite:///sports_league.db` |
| `REDIS_URL` | Redis connection for background jobs | `redis://localhost:6379/0` |

## Getting Help

1. **Check the logs**: The development server shows detailed error messages
2. **Check the database**: Use a SQLite browser to inspect the database
3. **Run tests**: `npm run test` to verify everything is working
4. **Check CLI commands**: `flask --help` for available commands

## Next Steps

1. Visit the application at http://localhost:5000
2. Create demo data with `npm run create-org` and `npm run seed-demo`
3. Explore the admin interface at http://localhost:5000/demo/admin
4. Try the CLI commands for data management
5. Check out the security features and testing tools

Happy coding! 🚀

# Docker Development Setup

Yes! This project has full Docker support. Here's how to run it with Docker.

## 🐳 **Quick Start with Docker**

```bash
# Option 1: Using npm scripts (recommended)
npm run dev

# Option 2: Direct Docker Compose
docker-compose up --build
```

## 🏗️ **What Docker Sets Up**

The Docker setup includes:
- **Web app** (Flask) on port 5000
- **PostgreSQL database** on port 5432
- **Redis** for background jobs on port 6379
- **Background worker** for async tasks

## 📋 **Available Commands**

### **Development**
```bash
npm run dev          # Start all services with build
npm run start        # Start all services
npm run stop         # Stop all services
npm run restart      # Restart all services
npm run logs         # View web app logs
```

### **Setup & Maintenance**
```bash
npm run setup        # Build Docker images
npm run shell        # Access web container shell
npm run db-shell     # Access PostgreSQL shell
```

### **Data Management**
```bash
npm run create-org   # Create demo organization
npm run seed-demo    # Seed demo data
npm run test-cli     # Test CLI commands
```

## 🚀 **Complete Docker Workflow**

### **1. Start the application:**
```bash
npm run dev
```

This will:
- Build the Docker images
- Start PostgreSQL database
- Start Redis
- Start the Flask web application
- Start the background worker

### **2. Create demo data:**
```bash
# In another terminal (while containers are running)
npm run create-org
npm run seed-demo
```

### **3. Access the application:**
- **Web app**: http://localhost:5000
- **Demo site**: http://localhost:5000/demo
- **Admin**: http://localhost:5000/demo/admin
  - Login: admin@demo.com / password123

### **4. View logs:**
```bash
npm run logs
```

### **5. Stop when done:**
```bash
npm run stop
```

## 🔧 **Docker vs Local Development**

### **Docker (Recommended for Production-like Development):**
✅ Full PostgreSQL database
✅ Redis for background jobs
✅ Background worker processes
✅ Production-like environment
✅ Consistent across different machines

### **Local (Simpler for Quick Development):**
✅ Faster startup
✅ SQLite database (simpler)
✅ No Docker required
✅ Direct file editing

```bash
# To run locally instead of Docker:
npm run dev-local
```

## 🗄️ **Database Access**

### **PostgreSQL Shell:**
```bash
npm run db-shell
# or
docker-compose exec db psql -U sports_league_owner -d sports_league
```

### **Web Container Shell:**
```bash
npm run shell
# or
docker-compose exec web bash
```

### **CLI Commands in Docker:**
```bash
# List organizations
docker-compose exec web flask org:list

# Export data
docker-compose exec web flask export:season --season <id> --what all

# View all available commands
docker-compose exec web flask --help
```

## 📁 **Docker File Structure**

```
├── docker-compose.yml      # Multi-container setup
├── Dockerfile             # Web app container
├── .env                   # Environment variables
├── requirements.txt       # Python dependencies
├── schema.sql            # Database schema
└── init-db.sh           # Database initialization
```

## 🔍 **Monitoring & Debugging**

### **Check container status:**
```bash
docker-compose ps
```

### **View logs for specific service:**
```bash
docker-compose logs web      # Web app logs
docker-compose logs db       # Database logs
docker-compose logs redis    # Redis logs
docker-compose logs worker   # Background worker logs
```

### **Restart specific service:**
```bash
docker-compose restart web
docker-compose restart db
```

### **Rebuild after code changes:**
```bash
npm run dev  # Automatically rebuilds
# or
docker-compose up --build
```

## 🛠️ **Troubleshooting**

### **Port conflicts:**
```bash
# If ports are in use, modify docker-compose.yml:
ports:
  - "5001:5000"  # Change web port
  - "5433:5432"  # Change database port
```

### **Clean restart:**
```bash
docker-compose down -v  # Remove containers and volumes
npm run dev             # Start fresh
```

### **Database issues:**
```bash
# Reset database
docker-compose down -v
docker volume prune
npm run dev
```

### **Permission issues on Windows:**
- Run Docker Desktop as administrator
- Ensure WSL2 is properly configured

## 🎯 **Production Deployment**

The Docker setup is production-ready:

```bash
# Production deployment
docker-compose -f docker-compose.prod.yml up -d
```

Key production features:
- ✅ PostgreSQL database with persistence
- ✅ Redis for session storage and background jobs
- ✅ Background worker for async tasks
- ✅ Health checks for all services
- ✅ Proper networking and security
- ✅ Volume mounts for data persistence

## 🏃‍♂️ **TL;DR - Just Run It**

```bash
# Start everything
npm run dev

# Wait for "web_1 started" message, then in another terminal:
npm run create-org
npm run seed-demo

# Visit: http://localhost:5000/demo
# Admin: http://localhost:5000/demo/admin (admin@demo.com / password123)

# Stop when done
npm run stop
```

That's it! Docker handles all the complexity for you. 🚀
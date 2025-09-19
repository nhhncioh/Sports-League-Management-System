#!/usr/bin/env python3
"""Development server runner for SLMS."""

import os
import sys
from pathlib import Path

def setup_environment():
    """Set up the development environment."""
    # Add the project root to Python path
    project_root = Path(__file__).parent
    sys.path.insert(0, str(project_root))

    # Load environment variables
    try:
        from dotenv import load_dotenv
        env_file = project_root / '.env'
        if env_file.exists():
            load_dotenv(env_file)
            print(f"✓ Loaded environment from {env_file}")
        else:
            print(f"⚠️ No .env file found at {env_file}")
    except ImportError:
        print("⚠️ python-dotenv not installed, environment variables may not load")

    # Set default Flask environment variables
    os.environ.setdefault('FLASK_APP', 'main.py')
    os.environ.setdefault('FLASK_ENV', 'development')
    os.environ.setdefault('FLASK_DEBUG', '1')

def check_dependencies():
    """Check if required dependencies are installed."""
    try:
        import flask
        print(f"✓ Flask {flask.__version__} installed")
    except ImportError:
        print("❌ Flask not installed. Run: pip install -r requirements.txt")
        return False

    try:
        import sqlalchemy
        print(f"✓ SQLAlchemy {sqlalchemy.__version__} installed")
    except ImportError:
        print("❌ SQLAlchemy not installed. Run: pip install -r requirements.txt")
        return False

    return True

def initialize_database():
    """Initialize the database if it doesn't exist."""
    try:
        from slms import create_app
        from slms.extensions import db

        app = create_app()
        with app.app_context():
            # Check if database exists
            try:
                db.engine.connect()
                print("✓ Database connection successful")
            except Exception as e:
                print(f"⚠️ Database connection failed: {e}")
                print("Creating database tables...")
                try:
                    db.create_all()
                    print("✓ Database tables created")
                except Exception as create_error:
                    print(f"❌ Failed to create database tables: {create_error}")
                    return False

        return True
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        return False

def run_development_server():
    """Run the Flask development server."""
    try:
        from slms import create_app

        app = create_app()

        print("\n" + "="*60)
        print("🚀 Starting SLMS Development Server")
        print("="*60)
        print(f"Environment: {os.environ.get('FLASK_ENV', 'production')}")
        print(f"Debug mode: {os.environ.get('FLASK_DEBUG', '0') == '1'}")
        print(f"Database: {os.environ.get('DATABASE_URL', 'Not configured')}")
        print("\n📱 Access the application at:")
        print("   • http://localhost:5000")
        print("   • http://127.0.0.1:5000")
        print("\n🛠️ To create demo data, run in another terminal:")
        print("   flask org:create --name 'Demo League' --slug demo --admin-email admin@demo.com --admin-password password123")
        print("   flask seed:demo --org demo")
        print("   Then visit: http://localhost:5000/demo")
        print("\n⏹️ Press Ctrl+C to stop the server")
        print("="*60)

        # Run the app
        app.run(
            host='0.0.0.0',
            port=5000,
            debug=True,
            use_reloader=True
        )

    except Exception as e:
        print(f"❌ Failed to start development server: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main function to set up and run the development server."""
    print("Sports League Management System - Development Setup")
    print("="*60)

    # Setup environment
    setup_environment()

    # Check dependencies
    if not check_dependencies():
        print("\n❌ Dependencies check failed. Please install requirements:")
        print("   pip install -r requirements.txt")
        sys.exit(1)

    # Initialize database
    if not initialize_database():
        print("\n❌ Database initialization failed.")
        sys.exit(1)

    # Run development server
    try:
        run_development_server()
    except KeyboardInterrupt:
        print("\n\n🛑 Development server stopped by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
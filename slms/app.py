"""Legacy app.py file - use main.py instead."""
from slms import create_app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True)

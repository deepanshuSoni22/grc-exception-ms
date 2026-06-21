import sys
import os

# Ensure the root directory and subdirectories are in Python's search path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask_app.app import app

if __name__ == "__main__":
    app.run()

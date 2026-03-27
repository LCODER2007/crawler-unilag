"""
Simple script to start the URAAS dashboard.
Handles Python path setup automatically.
"""
import sys
import os

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Now import and run the dashboard
from uraas.dashboard.app import app, socketio
from uraas.config import config

if __name__ == '__main__':
    print("=" * 70)
    print("URAAS Dashboard Starting...")
    print("=" * 70)
    print(f"Dashboard URL: http://localhost:{config.DASHBOARD_PORT}")
    print("Press Ctrl+C to stop")
    print("=" * 70)
    socketio.run(app, host='0.0.0.0', port=config.DASHBOARD_PORT, debug=False)

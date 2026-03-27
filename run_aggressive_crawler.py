#!/usr/bin/env python3
"""
AGGRESSIVE CRAWLER LAUNCHER
This is the crawler that searches up to 100,000 pages until target is reached!

Usage:
  python run_aggressive_crawler.py --target 10
  python run_aggressive_crawler.py --target 50
"""

import subprocess
import sys
import os

def main():
    print("=" * 70)
    print("LAUNCHING AGGRESSIVE CRAWLER")
    print("=" * 70)
    print("This crawler will search up to 100,000 pages until your target is reached!")
    print("It will NOT stop after just 250-350 candidates like the old one.")
    print("=" * 70)
    print()
    
    # Pass all arguments to the aggressive crawler
    cmd = [sys.executable, "crawl_aggressive.py"] + sys.argv[1:]
    
    print(f"Running: {' '.join(cmd)}")
    print()
    
    # Run the aggressive crawler
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Crawler failed with exit code {e.returncode}")
        sys.exit(e.returncode)
    except KeyboardInterrupt:
        print("\nCrawler interrupted by user")
        sys.exit(1)

if __name__ == "__main__":
    main()
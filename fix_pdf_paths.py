#!/usr/bin/env python3
"""
Fix PDF file paths in database to use absolute paths.
"""
import os
from uraas.database import SessionLocal, File

def fix_paths():
    session = SessionLocal()
    try:
        # Get project root
        project_root = os.path.dirname(os.path.abspath(__file__))
        
        files = session.query(File).all()
        fixed_count = 0
        missing_count = 0
        
        print("=" * 70)
        print("FIXING PDF PATHS IN DATABASE")
        print("=" * 70)
        print(f"Project root: {project_root}")
        print(f"Total PDF records: {len(files)}")
        print()
        
        for file_record in files:
            old_path = file_record.file_path
            
            # Skip if already absolute and exists
            if os.path.isabs(old_path) and os.path.exists(old_path):
                continue
            
            # Convert to absolute path
            if not os.path.isabs(old_path):
                new_path = os.path.normpath(os.path.join(project_root, old_path))
            else:
                new_path = old_path
            
            # Check if file exists
            if os.path.exists(new_path):
                file_record.file_path = new_path
                fixed_count += 1
                print(f"✓ Fixed: {os.path.basename(new_path)}")
            else:
                missing_count += 1
                print(f"✗ Missing: {os.path.basename(old_path)}")
        
        session.commit()
        
        print()
        print("=" * 70)
        print("SUMMARY")
        print("=" * 70)
        print(f"Total records: {len(files)}")
        print(f"Fixed: {fixed_count}")
        print(f"Missing files: {missing_count}")
        print(f"Already correct: {len(files) - fixed_count - missing_count}")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        session.rollback()
    finally:
        session.close()

if __name__ == '__main__':
    fix_paths()

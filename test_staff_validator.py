"""
Quick test script to verify staff validator is working correctly.
Run this to ensure the staff validation logic is functioning.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from uraas.utils.staff_validator import staff_validator

def test_staff_validator():
    print("=" * 70)
    print("URAAS Staff Validator Test")
    print("=" * 70)
    print()
    
    # Load staff cache
    print(f"Staff cache loaded: {len(staff_validator.staff_names)} names")
    print()
    
    # Test cases
    test_cases = [
        # Should PASS (actual UNILAG staff - examples from your data)
        ("Prof. A. O. Osibogun", True),
        ("Dr. O. O. Afolayan", True),
        ("Prof Nwadinigwe", True),
        ("Dr. Yinka-Banjo C.O", True),
        
        # Should PASS (fuzzy match - slight variations)
        ("Professor A O Osibogun", True),
        ("Dr O O Afolayan", True),
        ("Prof. Nwadinigwe", True),
        
        # Should FAIL (not UNILAG staff)
        ("John Smith", False),
        ("Dr. Jane Doe", False),
        ("Prof. Random Person", False),
        ("University of Lagos", False),  # Not a person
        ("Lagos State", False),
    ]
    
    print("Running test cases...")
    print("-" * 70)
    
    passed = 0
    failed = 0
    
    for name, expected in test_cases:
        result = staff_validator.is_staff_member(name)
        status = "✓ PASS" if result == expected else "✗ FAIL"
        
        if result == expected:
            passed += 1
        else:
            failed += 1
        
        print(f"{status} | {name:40} | Expected: {expected:5} | Got: {result:5}")
    
    print("-" * 70)
    print()
    print(f"Results: {passed} passed, {failed} failed out of {len(test_cases)} tests")
    print()
    
    # Test author list validation
    print("Testing author list validation...")
    print("-" * 70)
    
    author_lists = [
        # Should PASS (has at least one UNILAG staff)
        (["Prof. A. O. Osibogun", "John Smith", "Jane Doe"], True),
        (["Random Person", "Dr. O. O. Afolayan"], True),
        
        # Should FAIL (no UNILAG staff)
        (["John Smith", "Jane Doe", "Random Person"], False),
        ([], False),
    ]
    
    for authors, expected in author_lists:
        result = staff_validator.validate_authors(authors, require_all=False)
        status = "✓ PASS" if result == expected else "✗ FAIL"
        
        author_str = ", ".join(authors[:2]) + ("..." if len(authors) > 2 else "")
        print(f"{status} | [{author_str:40}] | Expected: {expected:5} | Got: {result:5}")
    
    print("-" * 70)
    print()
    
    # Show sample of loaded staff
    print("Sample of loaded staff names (first 10):")
    print("-" * 70)
    for i, name in enumerate(list(staff_validator.staff_names)[:10], 1):
        print(f"{i:2}. {name}")
    
    print()
    print("=" * 70)
    print("Test complete!")
    print("=" * 70)

if __name__ == '__main__':
    test_staff_validator()

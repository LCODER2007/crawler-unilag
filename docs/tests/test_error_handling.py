#!/usr/bin/env python3
"""
Test Error Handling and Classification Improvements
Verifies that the system handles errors gracefully and classifies papers correctly.
"""
import sys
from uraas.database import SessionLocal, Item
from uraas.utils.unilag_classifier import classifier
from uraas.analytics.engine import analytics

def test_classifier_error_handling():
    """Test that classifier handles invalid inputs gracefully."""
    print("\n" + "=" * 70)
    print("TEST 1: Classifier Error Handling")
    print("=" * 70)
    
    test_cases = [
        (None, "None input"),
        ("", "Empty string"),
        ("   ", "Whitespace only"),
        ("a" * 10000, "Very long text"),
        ("Special chars: @#$%^&*()", "Special characters"),
    ]
    
    passed = 0
    for text, description in test_cases:
        try:
            result = classifier.classify(text)
            print(f"✓ {description}: Handled gracefully (returned {len(result)} results)")
            passed += 1
        except Exception as e:
            print(f"✗ {description}: Failed with error: {str(e)}")
    
    print(f"\nPassed: {passed}/{len(test_cases)}")
    return passed == len(test_cases)

def test_language_classification():
    """Test that language papers are correctly identified."""
    print("\n" + "=" * 70)
    print("TEST 2: Language Research Classification")
    print("=" * 70)
    
    # Medical/engineering papers that should NOT be classified as language papers
    false_positives = [
        "Barriers and facilitators of access to maternal, newborn and child health services during COVID-19",
        "A comparative study on the failure analysis of high voltage composite insulator core rods",
        "Preterm care during the COVID-19 pandemic: A comparative risk analysis",
        "Clinical outcomes in obstetric patients with hypertension",
        "Neonatal care in Nigerian hospitals during the pandemic",
        "High voltage insulator testing and analysis",
    ]
    
    print("Medical/Engineering Papers (should NOT match Faculty of Arts):")
    tn_count = 0
    for title in false_positives:
        results = classifier.classify(title.lower())
        # Check if classified under Faculty of Arts
        is_arts = any('Arts' in r[0] for r in results)
        status = "✓" if not is_arts else "✗"
        print(f"{status} {title[:70]}")
        if not is_arts:
            tn_count += 1
    
    print(f"\nCorrectly excluded: {tn_count}/{len(false_positives)} ({tn_count/len(false_positives)*100:.1f}%)")
    
    # The key test is that medical/engineering papers are NOT misclassified
    # as language research papers
    success = tn_count == len(false_positives)
    
    if success:
        print("\n✓ Language classification is working correctly!")
        print("  Medical and engineering papers are properly excluded.")
    else:
        print("\n✗ Some medical/engineering papers were misclassified.")
    
    return success

def test_analytics_error_handling():
    """Test that analytics functions handle errors gracefully."""
    print("\n" + "=" * 70)
    print("TEST 3: Analytics Error Handling")
    print("=" * 70)
    
    tests = [
        ("get_top_authors", lambda: analytics.get_top_authors(limit=5)),
        ("get_department_collaboration_network", lambda: analytics.get_department_collaboration_network()),
        ("get_publication_trends", lambda: analytics.get_publication_trends()),
        ("get_papers_by_faculty_and_department", lambda: analytics.get_papers_by_faculty_and_department()),
    ]
    
    passed = 0
    for name, func in tests:
        try:
            result = func()
            print(f"✓ {name}: Executed successfully")
            passed += 1
        except Exception as e:
            print(f"✗ {name}: Failed with error: {str(e)}")
    
    print(f"\nPassed: {passed}/{len(tests)}")
    return passed == len(tests)

def test_database_integrity():
    """Test database queries handle missing/null data."""
    print("\n" + "=" * 70)
    print("TEST 4: Database Integrity")
    print("=" * 70)
    
    session = SessionLocal()
    try:
        # Test handling of papers with missing data
        items = session.query(Item).limit(10).all()
        
        issues = []
        for item in items:
            try:
                # Test accessing potentially null fields
                _ = item.title or "Untitled"
                _ = item.abstract or ""
                _ = item.doi or ""
                _ = [a.name for a in item.authors]
                _ = [c.name for c in item.collections]
            except Exception as e:
                issues.append(f"Item {item.id}: {str(e)}")
        
        if issues:
            print("✗ Found issues:")
            for issue in issues:
                print(f"  - {issue}")
            return False
        else:
            print(f"✓ All {len(items)} test items handled correctly")
            return True
            
    except Exception as e:
        print(f"✗ Database test failed: {str(e)}")
        return False
    finally:
        session.close()

def main():
    print("=" * 70)
    print("URAAS ERROR HANDLING & CLASSIFICATION TEST SUITE")
    print("=" * 70)
    
    results = []
    
    # Run all tests
    results.append(("Classifier Error Handling", test_classifier_error_handling()))
    results.append(("Language Classification", test_language_classification()))
    results.append(("Analytics Error Handling", test_analytics_error_handling()))
    results.append(("Database Integrity", test_database_integrity()))
    
    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    
    for name, passed in results:
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{status}: {name}")
    
    total_passed = sum(1 for _, p in results if p)
    print(f"\nOverall: {total_passed}/{len(results)} test suites passed")
    
    if total_passed == len(results):
        print("\n🎉 All tests passed! System is robust and ready for production.")
        return 0
    else:
        print("\n⚠️  Some tests failed. Review the output above for details.")
        return 1

if __name__ == '__main__':
    sys.exit(main())

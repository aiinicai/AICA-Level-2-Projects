from ai_extractor import extract_email_with_ai
from validation import validate_ai_result
from test_cases import TEST_CASES

def main():
    passed = failed = errors = 0
    print("=" * 72)
    print("AICA LEVEL 2 CAPSTONE - AUTOMATED AI TEST RUN")
    print("=" * 72)
    for test in TEST_CASES:
        try:
            result = extract_email_with_ai(test["email"])
            validation = validate_ai_result(result)
            actual_total = sum(c.amount_usd for c in result.charges)
            actual_review = not validation.approved
            ok = round(actual_total, 2) == round(test["expected"]["total"], 2) and actual_review == test["expected"]["review"]
            passed += int(ok); failed += int(not ok)
            print(f'{test["id"]}: {"PASS" if ok else "FAIL"} | USD {actual_total:,.2f} | Review {actual_review}')
        except Exception as exc:
            errors += 1
            print(f'{test["id"]}: ERROR | {exc}')
    print("\nFINAL TEST SUMMARY")
    print(f"Total Tests : {len(TEST_CASES)}")
    print(f"Passed      : {passed}")
    print(f"Failed      : {failed}")
    print(f"Errors      : {errors}")

if __name__ == "__main__":
    main()

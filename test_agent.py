"""
Test script — demonstrates both required test inputs.

Usage:
    1. Start the server:  uvicorn app.main:app --reload
    2. Run this script:   python test_agent.py

Test 1 (Standard):  A clear, well-defined business request.
Test 2 (Complex):   An ambiguous, multi-step request requiring
                     the agent to make its own decisions.
"""

import httpx
import json
import sys
import time

BASE_URL = "http://127.0.0.1:8000"

# ── Test Cases ───────────────────────────────────────────────────────

TEST_CASES = [
    {
        "name": "Test 1 — Standard Business Request",
        "description": (
            "A clear, well-defined request for a project proposal. "
            "The agent should produce a structured proposal document."
        ),
        "payload": {
            "request": (
                "Create a project proposal for a mobile app that helps "
                "users track their daily water intake. The app should "
                "include reminders, progress tracking, and health insights."
            )
        },
    },
    {
        "name": "Test 2 — Complex / Ambiguous Request",
        "description": (
            "A vague, multi-faceted request with missing information and "
            "conflicting requirements. The agent must make assumptions, "
            "decide the document type, and create a coherent output."
        ),
        "payload": {
            "request": (
                "We had a meeting yesterday about Q3 strategy. Some people "
                "wanted to expand into Europe, others preferred focusing on "
                "the US market. Budget is tight but we also need to hire. "
                "The CEO mentioned something about AI integration but "
                "wasn't specific. Put together something useful from this."
            )
        },
    },
]


def run_test(test: dict, index: int) -> bool:
    """Run a single test case against the running server."""
    print(f"\n{'='*70}")
    print(f"  {test['name']}")
    print(f"  {test['description']}")
    print(f"{'='*70}")
    print(f"\nRequest: {test['payload']['request'][:100]}...")
    print("\nSending to POST /agent ... (this may take 30-60 seconds)\n")

    start = time.time()

    try:
        with httpx.Client(timeout=300.0) as client:
            response = client.post(f"{BASE_URL}/agent", json=test["payload"])

        elapsed = time.time() - start

        if response.status_code != 200:
            print(f"  ✗ FAILED — HTTP {response.status_code}")
            print(f"  Response: {response.text[:500]}")
            return False

        data = response.json()

        print(f"  ✓ Status: {response.status_code}")
        print(f"  ✓ Time: {elapsed:.1f}s")
        print(f"  ✓ Request ID: {data.get('request_id')}")
        print(f"  ✓ Document Type: {data.get('document_type')}")
        print(f"  ✓ Filename: {data.get('filename')}")
        print(f"  ✓ Download URL: {data.get('download_url')}")

        # Assumptions
        assumptions = data.get("assumptions", [])
        if assumptions:
            print(f"\n  Assumptions made ({len(assumptions)}):")
            for a in assumptions:
                print(f"    • {a}")

        # Task Plan
        tasks = data.get("task_plan", [])
        print(f"\n  Task Plan ({len(tasks)} steps):")
        for t in tasks:
            status_icon = {"completed": "✓", "failed": "✗", "pending": "○"}.get(
                t.get("status", ""), "?"
            )
            print(f"    {status_icon} Step {t['step_number']}: [{t['action']}] {t['description'][:60]}")

        # Reflection
        reflection = data.get("reflection", {})
        print(f"\n  Reflection:")
        print(f"    Score: {reflection.get('score', 'N/A')}/100")
        print(f"    Passed: {reflection.get('passed', 'N/A')}")
        if reflection.get("issues"):
            print(f"    Issues: {len(reflection['issues'])}")
            for issue in reflection["issues"][:3]:
                print(f"      - {issue[:80]}")
        if reflection.get("improvements_made"):
            print(f"    Improvements: {len(reflection['improvements_made'])}")
            for imp in reflection["improvements_made"]:
                print(f"      + {imp}")

        print(f"\n  Message: {data.get('message')}")

        # Try to download the file
        dl_url = data.get("download_url")
        if dl_url:
            with httpx.Client(timeout=30.0) as client:
                dl_response = client.get(f"{BASE_URL}{dl_url}")
            if dl_response.status_code == 200:
                print(f"  ✓ Document download verified ({len(dl_response.content)} bytes)")
            else:
                print(f"  ⚠ Document download failed: HTTP {dl_response.status_code}")

        return True

    except httpx.ConnectError:
        print("  ✗ ERROR: Could not connect to server.")
        print("  Make sure the server is running: uvicorn app.main:app --reload")
        return False
    except Exception as e:
        print(f"  ✗ ERROR: {e}")
        return False


def main():
    """Run all test cases."""
    print("\n" + "╔" + "═"*68 + "╗")
    print("║" + " AUTONOMOUS AI AGENT — TEST SUITE ".center(68) + "║")
    print("╚" + "═"*68 + "╝")

    # Health check
    print("\nChecking server health...")
    try:
        with httpx.Client(timeout=5.0) as client:
            health = client.get(f"{BASE_URL}/health")
        if health.status_code == 200:
            print(f"  ✓ Server is healthy: {health.json()}")
        else:
            print(f"  ✗ Server returned {health.status_code}")
            sys.exit(1)
    except httpx.ConnectError:
        print("  ✗ Server is not running!")
        print("  Start it with: uvicorn app.main:app --reload")
        sys.exit(1)

    # Run tests
    results = []
    for i, test in enumerate(TEST_CASES, start=1):
        passed = run_test(test, i)
        results.append((test["name"], passed))

    # Summary
    print(f"\n\n{'='*70}")
    print("  TEST SUMMARY")
    print(f"{'='*70}")
    for name, passed in results:
        icon = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {icon}  {name}")

    total_passed = sum(1 for _, p in results if p)
    print(f"\n  {total_passed}/{len(results)} tests passed.")
    print(f"{'='*70}\n")

    sys.exit(0 if total_passed == len(results) else 1)


if __name__ == "__main__":
    main()

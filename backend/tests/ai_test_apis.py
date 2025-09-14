#!/usr/bin/env python3
"""
Simple manual API validation script for testing Snapshot integration.
Run this to verify all backend APIs work correctly with real Snapshot data.
"""

import requests
import time
from typing import Optional

# Configuration
BASE_URL = "http://localhost:8000"
REAL_SPACE_ID = "arbitrumfoundation.eth"
TIMEOUT = 30


class APITester:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.results = []

    def log_result(
        self, test_name: str, success: bool, details: str, response_time: float = 0
    ):
        """Log test result."""
        status = "✅ PASS" if success else "❌ FAIL"
        self.results.append(
            {
                "test": test_name,
                "success": success,
                "details": details,
                "response_time": response_time,
            }
        )
        print(f"{status} {test_name}: {details} ({response_time:.2f}s)")

    def test_health_endpoint(self) -> bool:
        """Test the health check endpoint."""
        try:
            start = time.time()
            response = requests.get(f"{self.base_url}/health", timeout=TIMEOUT)
            response_time = time.time() - start

            if response.status_code == 200:
                data = response.json()
                if "status" in data and data["status"] == "healthy":
                    self.log_result(
                        "Health Check", True, f"Status: {data['status']}", response_time
                    )
                    return True
                else:
                    self.log_result(
                        "Health Check",
                        False,
                        f"Invalid response: {data}",
                        response_time,
                    )
                    return False
            else:
                self.log_result(
                    "Health Check", False, f"HTTP {response.status_code}", response_time
                )
                return False

        except Exception as e:
            self.log_result("Health Check", False, f"Error: {str(e)}")
            return False

    def test_proposals_endpoint(self) -> Optional[str]:
        """Test the proposals listing endpoint and return a proposal ID for further testing."""
        try:
            start = time.time()
            response = requests.get(
                f"{self.base_url}/proposals",
                params={"space_id": REAL_SPACE_ID, "limit": 5},
                timeout=TIMEOUT,
            )
            response_time = time.time() - start

            if response.status_code == 200:
                data = response.json()
                if "proposals" in data and isinstance(data["proposals"], list):
                    proposal_count = len(data["proposals"])
                    if proposal_count > 0:
                        proposal_id = data["proposals"][0]["id"]
                        self.log_result(
                            "Proposals List",
                            True,
                            f"Found {proposal_count} proposals",
                            response_time,
                        )
                        return proposal_id
                    else:
                        self.log_result(
                            "Proposals List",
                            True,
                            "No proposals found (valid response)",
                            response_time,
                        )
                        return None
                else:
                    self.log_result(
                        "Proposals List",
                        False,
                        f"Invalid response structure: {data}",
                        response_time,
                    )
                    return None
            else:
                self.log_result(
                    "Proposals List",
                    False,
                    f"HTTP {response.status_code}: {response.text}",
                    response_time,
                )
                return None

        except Exception as e:
            self.log_result("Proposals List", False, f"Error: {str(e)}")
            return None

    def test_proposal_by_id(self, proposal_id: str) -> bool:
        """Test getting a specific proposal by ID."""
        try:
            start = time.time()
            response = requests.get(
                f"{self.base_url}/proposals/{proposal_id}", timeout=TIMEOUT
            )
            response_time = time.time() - start

            if response.status_code == 200:
                data = response.json()
                required_fields = ["id", "title", "state"]
                if all(field in data for field in required_fields):
                    self.log_result(
                        "Proposal by ID",
                        True,
                        f"ID: {data['id'][:20]}..., Title: {data['title'][:50]}...",
                        response_time,
                    )
                    return True
                else:
                    missing = [f for f in required_fields if f not in data]
                    self.log_result(
                        "Proposal by ID",
                        False,
                        f"Missing fields: {missing}",
                        response_time,
                    )
                    return False
            else:
                self.log_result(
                    "Proposal by ID",
                    False,
                    f"HTTP {response.status_code}: {response.text}",
                    response_time,
                )
                return False

        except Exception as e:
            self.log_result("Proposal by ID", False, f"Error: {str(e)}")
            return False

    def test_proposal_summarize(self, proposal_id: str) -> bool:
        """Test AI proposal summarization."""
        try:
            start = time.time()
            response = requests.post(
                f"{self.base_url}/proposals/summarize",
                json={
                    "proposal_ids": [proposal_id],
                    "include_risk_assessment": True,
                    "include_recommendations": True,
                },
                timeout=TIMEOUT,
            )
            response_time = time.time() - start

            if response.status_code == 200:
                data = response.json()
                if "summaries" in data and len(data["summaries"]) > 0:
                    summary = data["summaries"][0]
                    if "summary" in summary and "proposal_id" in summary:
                        self.log_result(
                            "AI Summarization",
                            True,
                            f"Generated summary for {summary['proposal_id']}",
                            response_time,
                        )
                        return True
                    else:
                        self.log_result(
                            "AI Summarization",
                            False,
                            f"Invalid summary structure: {summary}",
                            response_time,
                        )
                        return False
                else:
                    self.log_result(
                        "AI Summarization",
                        False,
                        f"No summaries returned: {data}",
                        response_time,
                    )
                    return False
            else:
                self.log_result(
                    "AI Summarization",
                    False,
                    f"HTTP {response.status_code}: {response.text}",
                    response_time,
                )
                return False

        except Exception as e:
            self.log_result("AI Summarization", False, f"Error: {str(e)}")
            return False

    def test_top_voters(self, proposal_id: str) -> bool:
        """Test top voters endpoint."""
        try:
            start = time.time()
            response = requests.get(
                f"{self.base_url}/proposals/{proposal_id}/top-voters", timeout=TIMEOUT
            )
            response_time = time.time() - start

            if response.status_code == 200:
                data = response.json()
                if "proposal_id" in data and "voters" in data:
                    voter_count = len(data["voters"])
                    self.log_result(
                        "Top Voters",
                        True,
                        f"Found {voter_count} voters for proposal",
                        response_time,
                    )
                    return True
                else:
                    self.log_result(
                        "Top Voters",
                        False,
                        f"Invalid response structure: {data}",
                        response_time,
                    )
                    return False
            else:
                self.log_result(
                    "Top Voters",
                    False,
                    f"HTTP {response.status_code}: {response.text}",
                    response_time,
                )
                return False

        except Exception as e:
            self.log_result("Top Voters", False, f"Error: {str(e)}")
            return False

    def run_all_tests(self):
        """Run all API tests in sequence."""
        print(f"🚀 Starting API validation against {self.base_url}")
        print(f"📊 Testing with Snapshot space: {REAL_SPACE_ID}")
        print("=" * 80)

        # Test 1: Health check
        health_ok = self.test_health_endpoint()
        if not health_ok:
            print("❌ Health check failed - backend may not be running")
            return False

        # Test 2: Get proposals and extract one for further testing
        proposal_id = self.test_proposals_endpoint()
        if not proposal_id:
            print("❌ No proposals found for testing individual endpoints")
            return False

        # Test 3: Get specific proposal
        proposal_ok = self.test_proposal_by_id(proposal_id)

        # Test 4: AI summarization
        summarize_ok = self.test_proposal_summarize(proposal_id)

        # Test 5: Top voters
        voters_ok = self.test_top_voters(proposal_id)

        # Summary
        print("=" * 80)
        passed = sum(1 for r in self.results if r["success"])
        total = len(self.results)
        print(f"📈 SUMMARY: {passed}/{total} tests passed")

        if passed == total:
            print("🎉 All API endpoints working correctly with real Snapshot data!")
            return True
        else:
            print("⚠️  Some tests failed - check output above for details")
            return False


def main():
    """Main execution function."""
    print("Backend API Validation Script")
    print("This script tests all API endpoints with real Snapshot data")
    print()

    tester = APITester(BASE_URL)
    success = tester.run_all_tests()

    if success:
        exit(0)
    else:
        exit(1)


if __name__ == "__main__":
    main()

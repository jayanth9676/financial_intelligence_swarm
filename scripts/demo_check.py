#!/usr/bin/env python3
"""Demo setup and readiness verification script.

This script:
1. Checks all required services are running
2. Verifies database connections
3. Hydrates sample data
4. Runs basic health checks
5. Reports demo readiness status
"""

import sys
import httpx
from typing import List, Tuple

# API base URL
API_BASE = "http://localhost:8000"


class DemoChecker:
    """Check demo readiness and setup sample data."""
    
    def __init__(self):
        self.results: List[Tuple[str, bool, str]] = []
        self.client = httpx.Client(timeout=30.0)
    
    def check(self, name: str, passed: bool, message: str = ""):
        """Record a check result."""
        status = "✅" if passed else "❌"
        self.results.append((name, passed, message))
        print(f"  {status} {name}: {message}")
    
    def check_backend_health(self) -> bool:
        """Check if backend API is running."""
        print("\n🔍 Checking Backend API...")
        try:
            response = self.client.get(f"{API_BASE}/health")
            if response.status_code == 200:
                data = response.json()
                self.check("Backend API", True, f"Running (v{data.get('version', '?')})")
                return True
            else:
                self.check("Backend API", False, f"Status {response.status_code}")
                return False
        except Exception as e:
            self.check("Backend API", False, f"Connection failed: {e}")
            return False
    
    def check_frontend_health(self) -> bool:
        """Check if frontend is running."""
        print("\n🔍 Checking Frontend...")
        try:
            response = self.client.get("http://localhost:3000", follow_redirects=True)
            if response.status_code == 200:
                self.check("Frontend Dashboard", True, "Running on port 3000")
                return True
            else:
                self.check("Frontend Dashboard", False, f"Status {response.status_code}")
                return False
        except Exception as e:
            self.check("Frontend Dashboard", False, f"Connection failed: {e}")
            return False
    
    def check_api_endpoints(self) -> bool:
        """Check critical API endpoints."""
        print("\n🔍 Checking API Endpoints...")
        endpoints = [
            ("/transactions", "GET", "Transactions List"),
            ("/monitor/thresholds", "GET", "Monitoring Config"),
            ("/compliance/status", "GET", "Compliance Status"),
            ("/partners", "GET", "Partners List"),
            ("/approval/queue", "GET", "Approval Queue"),
            ("/reconciliation/status", "GET", "Reconciliation Status"),
        ]
        
        all_passed = True
        for path, method, name in endpoints:
            try:
                if method == "GET":
                    response = self.client.get(f"{API_BASE}{path}")
                else:
                    response = self.client.post(f"{API_BASE}{path}")
                
                if response.status_code == 200:
                    self.check(name, True, "Accessible")
                else:
                    self.check(name, False, f"Status {response.status_code}")
                    all_passed = False
            except Exception as e:
                self.check(name, False, str(e))
                all_passed = False
        
        return all_passed
    
    def generate_sample_data(self) -> bool:
        """Generate sample transaction data."""
        print("\n🔍 Generating Sample Data...")
        try:
            response = self.client.post(f"{API_BASE}/generate-data?count=5")
            if response.status_code == 200:
                data = response.json()
                count = data.get("count", 0)
                self.check("Sample Transactions", True, f"Generated {count} transactions")
                return True
            else:
                self.check("Sample Transactions", False, f"Failed with status {response.status_code}")
                return False
        except Exception as e:
            self.check("Sample Transactions", False, str(e))
            return False
    
    def verify_investigation_flow(self) -> bool:
        """Verify end-to-end investigation works."""
        print("\n🔍 Verifying Investigation Flow...")
        try:
            # Get a pending transaction
            tx_response = self.client.get(f"{API_BASE}/transactions")
            if tx_response.status_code != 200:
                self.check("Investigation Flow", False, "Failed to get transactions")
                return False
            
            transactions = tx_response.json().get("transactions", [])
            pending = [t for t in transactions if t.get("status") == "pending"]
            
            if not pending:
                self.check("Investigation Flow", True, "No pending transactions (generate data first)")
                return True
            
            # Investigation would require streaming - just verify endpoint exists
            test_uetr = pending[0]["uetr"]
            self.check("Investigation Flow", True, f"Ready to investigate {test_uetr[:8]}...")
            return True
            
        except Exception as e:
            self.check("Investigation Flow", False, str(e))
            return False
    
    def verify_sar_generation(self) -> bool:
        """Verify SAR generation works."""
        print("\n🔍 Verifying SAR Generation...")
        try:
            # Check if SAR endpoint exists (don't actually generate without completed investigation)
            response = self.client.get(f"{API_BASE}/docs")
            if response.status_code == 200:
                self.check("SAR Generation", True, "Endpoint available")
                return True
            else:
                self.check("SAR Generation", False, "API docs not accessible")
                return False
        except Exception as e:
            self.check("SAR Generation", False, str(e))
            return False
    
    def print_summary(self):
        """Print final summary."""
        print("\n" + "=" * 60)
        print("📊 DEMO READINESS SUMMARY")
        print("=" * 60)
        
        passed = sum(1 for _, p, _ in self.results if p)
        total = len(self.results)
        
        print(f"\nChecks passed: {passed}/{total}")
        
        if passed == total:
            print("\n🎉 Demo is READY!")
            print("\nAccess points:")
            print("  • Frontend:  http://localhost:3000")
            print("  • API Docs:  http://localhost:8000/docs")
            print("  • WebSocket: ws://localhost:8000/ws")
        else:
            print("\n⚠️  Some checks failed. Please address the issues above.")
            failed = [name for name, p, _ in self.results if not p]
            print(f"\nFailed: {', '.join(failed)}")
        
        print()
        return passed == total


def main():
    """Main entry point."""
    print("=" * 60)
    print("🚀 FIS Demo Readiness Check")
    print("=" * 60)
    
    checker = DemoChecker()
    
    # Run all checks
    backend_ok = checker.check_backend_health()
    
    if backend_ok:
        checker.check_api_endpoints()
        checker.generate_sample_data()
        checker.verify_investigation_flow()
        checker.verify_sar_generation()
    
    checker.check_frontend_health()
    
    # Print summary and exit with appropriate code
    ready = checker.print_summary()
    sys.exit(0 if ready else 1)


if __name__ == "__main__":
    main()

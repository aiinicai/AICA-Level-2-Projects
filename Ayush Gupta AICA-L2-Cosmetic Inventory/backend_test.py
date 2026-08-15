#!/usr/bin/env python3
"""
Comprehensive backend API testing for Cosmetic Inventory Management System
"""

import requests
import sys
import json
from datetime import datetime, timedelta
import uuid

class InventoryAPITester:
    def __init__(self, base_url="https://job-timeline-4.preview.emergentagent.com"):
        self.base_url = base_url
        self.token = None
        self.user = None
        self.tests_run = 0
        self.tests_passed = 0
        self.created_ids = {
            'suppliers': [],
            'materials': [],
            'products': [],
            'purchase_orders': [],
            'chemist_reports': []
        }

    def log(self, message):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None):
        """Run a single API test"""
        url = f"{self.base_url}/api/{endpoint}"
        test_headers = {'Content-Type': 'application/json'}
        
        if self.token:
            test_headers['Authorization'] = f'Bearer {self.token}'
        if headers:
            test_headers.update(headers)

        self.tests_run += 1
        self.log(f"Testing {name}...")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=test_headers, timeout=10)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=test_headers, timeout=10)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=test_headers, timeout=10)
            elif method == 'DELETE':
                response = requests.delete(url, headers=test_headers, timeout=10)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                self.log(f"✅ PASSED - {name} - Status: {response.status_code}")
                try:
                    return True, response.json() if response.text else {}
                except:
                    return True, {}
            else:
                self.log(f"❌ FAILED - {name} - Expected {expected_status}, got {response.status_code}")
                try:
                    error_detail = response.json().get('detail', response.text)
                    self.log(f"   Error: {error_detail}")
                except:
                    self.log(f"   Response: {response.text[:200]}")
                return False, {}

        except Exception as e:
            self.log(f"❌ FAILED - {name} - Error: {str(e)}")
            return False, {}

    def test_user_registration_and_login(self):
        """Test user registration (first user becomes admin) and login"""
        self.log("\n=== Testing User Authentication ===")
        
        # Register first user (should become admin)
        admin_data = {
            "email": f"admin@test.com",
            "name": "Test Admin",
            "password": "admin123"
        }
        
        success, response = self.run_test(
            "Admin Registration", "POST", "auth/register", 200, admin_data
        )
        
        if success and 'token' in response:
            self.token = response['token']
            self.user = response['user']
            self.log(f"✅ Admin registered successfully - Role: {self.user.get('role')}")
            
            # Verify the user is admin
            if self.user.get('role') != 'admin':
                self.log(f"❌ First user should be admin, got: {self.user.get('role')}")
                return False
            
            # Test login
            login_success, login_response = self.run_test(
                "Admin Login", "POST", "auth/login", 200, 
                {"email": admin_data["email"], "password": admin_data["password"]}
            )
            
            if login_success:
                # Test /auth/me endpoint
                me_success, me_response = self.run_test(
                    "Get Current User", "GET", "auth/me", 200
                )
                return me_success
            
            return login_success
        
        return False

    def test_suppliers_crud(self):
        """Test suppliers CRUD operations"""
        self.log("\n=== Testing Suppliers CRUD ===")
        
        # Create supplier
        supplier_data = {
            "name": "Chemical Supplies Co.",
            "contact_person": "John Doe",
            "phone": "+1234567890",
            "email": "john@chemicals.com",
            "address": "123 Chemical St, City",
            "material_type": "chemicals"
        }
        
        success, response = self.run_test(
            "Create Chemical Supplier", "POST", "suppliers", 200, supplier_data
        )
        
        if success and 'id' in response:
            supplier_id = response['id']
            self.created_ids['suppliers'].append(supplier_id)
            
            # Get all suppliers
            self.run_test("Get All Suppliers", "GET", "suppliers", 200)
            
            # Get specific supplier
            self.run_test("Get Supplier by ID", "GET", f"suppliers/{supplier_id}", 200)
            
            # Update supplier
            update_data = {"phone": "+9876543210"}
            self.run_test("Update Supplier", "PUT", f"suppliers/{supplier_id}", 200, update_data)
            
            # Create packing supplier
            packing_supplier = {
                "name": "Packaging Materials Ltd",
                "contact_person": "Jane Smith",
                "phone": "+1122334455",
                "email": "jane@packaging.com",
                "address": "456 Package Ave, City",
                "material_type": "packing"
            }
            
            pack_success, pack_response = self.run_test(
                "Create Packing Supplier", "POST", "suppliers", 200, packing_supplier
            )
            
            if pack_success and 'id' in pack_response:
                self.created_ids['suppliers'].append(pack_response['id'])
            
            return True
        
        return False

    def test_materials_crud(self):
        """Test raw materials CRUD operations"""
        self.log("\n=== Testing Raw Materials CRUD ===")
        
        # Create chemical material
        chemical_data = {
            "name": "Sodium Lauryl Sulfate",
            "sku": "SLS-001",
            "category": "chemical",
            "unit": "kg",
            "min_stock_level": 10.0,
            "max_stock_level": 100.0,
            "unit_price": 150.50,
            "supplier_id": self.created_ids['suppliers'][0] if self.created_ids['suppliers'] else None
        }
        
        success, response = self.run_test(
            "Create Chemical Material", "POST", "materials", 200, chemical_data
        )
        
        if success and 'id' in response:
            material_id = response['id']
            self.created_ids['materials'].append(material_id)
            
            # Create packing material
            packing_data = {
                "name": "Plastic Bottles 250ml",
                "sku": "BTL-250",
                "category": "packing",
                "unit": "pieces",
                "min_stock_level": 500,
                "max_stock_level": 5000,
                "unit_price": 2.50,
                "supplier_id": self.created_ids['suppliers'][1] if len(self.created_ids['suppliers']) > 1 else None
            }
            
            pack_success, pack_response = self.run_test(
                "Create Packing Material", "POST", "materials", 200, packing_data
            )
            
            if pack_success and 'id' in pack_response:
                self.created_ids['materials'].append(pack_response['id'])
            
            # Get all materials
            self.run_test("Get All Materials", "GET", "materials", 200)
            
            # Get materials by category
            self.run_test("Get Chemical Materials", "GET", "materials?category=chemical", 200)
            self.run_test("Get Packing Materials", "GET", "materials?category=packing", 200)
            
            # Get specific material
            self.run_test("Get Material by ID", "GET", f"materials/{material_id}", 200)
            
            # Update material
            update_data = {"unit_price": 160.00}
            self.run_test("Update Material", "PUT", f"materials/{material_id}", 200, update_data)
            
            return True
        
        return False

    def test_products_crud(self):
        """Test products CRUD operations"""
        self.log("\n=== Testing Products CRUD ===")
        
        product_data = {
            "name": "Anti-Dandruff Shampoo",
            "sku": "SHAM-001",
            "category": "shampoo",
            "description": "Premium anti-dandruff shampoo with natural ingredients",
            "batch_size": 1000.0,
            "unit": "liters",
            "formula": [
                {
                    "material_id": self.created_ids['materials'][0] if self.created_ids['materials'] else "dummy",
                    "material_name": "Sodium Lauryl Sulfate",
                    "quantity": 50.0
                }
            ]
        }
        
        success, response = self.run_test(
            "Create Product", "POST", "products", 200, product_data
        )
        
        if success and 'id' in response:
            product_id = response['id']
            self.created_ids['products'].append(product_id)
            
            # Get all products
            self.run_test("Get All Products", "GET", "products", 200)
            
            # Get products by category
            self.run_test("Get Shampoo Products", "GET", "products?category=shampoo", 200)
            
            # Get specific product
            self.run_test("Get Product by ID", "GET", f"products/{product_id}", 200)
            
            # Update product
            update_data = {"description": "Updated premium anti-dandruff shampoo"}
            self.run_test("Update Product", "PUT", f"products/{product_id}", 200, update_data)
            
            return True
        
        return False

    def test_purchase_orders_flow(self):
        """Test complete purchase order flow"""
        self.log("\n=== Testing Purchase Orders Flow ===")
        
        if not self.created_ids['suppliers'] or not self.created_ids['materials']:
            self.log("❌ Cannot test PO flow - missing suppliers or materials")
            return False
        
        po_data = {
            "supplier_id": self.created_ids['suppliers'][0],
            "items": [
                {
                    "material_id": self.created_ids['materials'][0],
                    "material_name": "Sodium Lauryl Sulfate",
                    "quantity": 50.0,
                    "unit_price": 150.50
                }
            ],
            "order_date": datetime.now().strftime("%Y-%m-%d"),
            "expected_delivery": (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d"),
            "notes": "Urgent order for production"
        }
        
        success, response = self.run_test(
            "Create Purchase Order", "POST", "purchase-orders", 200, po_data
        )
        
        if success and 'id' in response:
            po_id = response['id']
            self.created_ids['purchase_orders'].append(po_id)
            
            # Get all POs
            self.run_test("Get All Purchase Orders", "GET", "purchase-orders", 200)
            
            # Get PO by status
            self.run_test("Get Pending POs", "GET", "purchase-orders?status=pending", 200)
            
            # Get specific PO
            self.run_test("Get PO by ID", "GET", f"purchase-orders/{po_id}", 200)
            
            # Approve PO
            self.run_test("Approve PO", "PUT", f"purchase-orders/{po_id}", 200, {"status": "approved"})
            
            # Receive PO (this should update stock)
            self.run_test("Receive PO", "POST", f"purchase-orders/{po_id}/receive", 200)
            
            # Verify stock was updated
            if self.created_ids['materials']:
                self.run_test("Check Updated Material Stock", "GET", f"materials/{self.created_ids['materials'][0]}", 200)
            
            return True
        
        return False

    def test_chemist_reports_flow(self):
        """Test chemist reports workflow"""
        self.log("\n=== Testing Chemist Reports Flow ===")
        
        if not self.created_ids['products'] or not self.created_ids['materials']:
            self.log("❌ Cannot test chemist reports - missing products or materials")
            return False
        
        report_data = {
            "product_id": self.created_ids['products'][0],
            "batch_size": 500.0,
            "materials_required": [
                {
                    "material_id": self.created_ids['materials'][0],
                    "material_name": "Sodium Lauryl Sulfate",
                    "quantity": 25.0
                }
            ],
            "notes": "Production batch for anti-dandruff shampoo"
        }
        
        success, response = self.run_test(
            "Create Chemist Report", "POST", "chemist-reports", 200, report_data
        )
        
        if success and 'id' in response:
            report_id = response['id']
            self.created_ids['chemist_reports'].append(report_id)
            
            # Get all reports
            self.run_test("Get All Chemist Reports", "GET", "chemist-reports", 200)
            
            # Get pending reports
            self.run_test("Get Pending Reports", "GET", "chemist-reports?status=pending", 200)
            
            # Get specific report
            self.run_test("Get Report by ID", "GET", f"chemist-reports/{report_id}", 200)
            
            # Approve report
            self.run_test("Approve Report", "PUT", f"chemist-reports/{report_id}", 200, {"status": "approved"})
            
            # Issue materials (this should deduct from stock)
            self.run_test("Issue Materials", "POST", f"chemist-reports/{report_id}/issue-materials", 200)
            
            return True
        
        return False

    def test_dashboard_and_reports(self):
        """Test dashboard stats and reporting endpoints"""
        self.log("\n=== Testing Dashboard & Reports ===")
        
        # Dashboard stats
        self.run_test("Dashboard Stats", "GET", "dashboard/stats", 200)
        
        # Stock movements
        self.run_test("Stock Movements", "GET", "stock-movements", 200)
        
        # Reports
        start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        end_date = datetime.now().strftime("%Y-%m-%d")
        
        self.run_test("Consumption Report", "GET", f"reports/consumption?start_date={start_date}&end_date={end_date}", 200)
        self.run_test("Stage-wise Report", "GET", "reports/stage-wise", 200)
        self.run_test("Inventory Summary", "GET", "reports/inventory-summary", 200)
        
        return True

    def test_error_handling(self):
        """Test various error scenarios"""
        self.log("\n=== Testing Error Handling ===")
        
        # Invalid endpoints
        self.run_test("Invalid Endpoint", "GET", "invalid-endpoint", 404)
        
        # Missing authentication
        temp_token = self.token
        self.token = None
        self.run_test("No Auth Token", "GET", "suppliers", 401)
        self.token = temp_token
        
        # Invalid data
        self.run_test("Invalid Supplier Data", "POST", "suppliers", 422, {"name": ""})
        
        # Non-existent resource
        self.run_test("Non-existent Supplier", "GET", "suppliers/non-existent-id", 404)
        
        return True

    def run_all_tests(self):
        """Run the complete test suite"""
        self.log("🚀 Starting Cosmetic Inventory Management API Testing")
        self.log(f"Base URL: {self.base_url}")
        
        try:
            # Core authentication test
            if not self.test_user_registration_and_login():
                self.log("❌ Authentication failed - stopping tests")
                return False
            
            # Core CRUD operations
            self.test_suppliers_crud()
            self.test_materials_crud() 
            self.test_products_crud()
            
            # Business workflows
            self.test_purchase_orders_flow()
            self.test_chemist_reports_flow()
            
            # Dashboard and reporting
            self.test_dashboard_and_reports()
            
            # Error handling
            self.test_error_handling()
            
            # Final summary
            self.log(f"\n📊 TEST SUMMARY:")
            self.log(f"Tests Run: {self.tests_run}")
            self.log(f"Tests Passed: {self.tests_passed}")
            self.log(f"Tests Failed: {self.tests_run - self.tests_passed}")
            self.log(f"Success Rate: {(self.tests_passed/self.tests_run*100):.1f}%")
            
            if self.tests_passed == self.tests_run:
                self.log("🎉 ALL TESTS PASSED!")
                return True
            else:
                self.log("⚠️  Some tests failed - check the logs above")
                return False
                
        except Exception as e:
            self.log(f"❌ Test suite failed with error: {str(e)}")
            return False

def main():
    tester = InventoryAPITester()
    success = tester.run_all_tests()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
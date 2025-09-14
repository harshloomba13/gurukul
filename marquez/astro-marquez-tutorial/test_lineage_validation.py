#!/usr/bin/env python3
"""
Lineage Validation Test Suite
Validates that data lineage tracking is working correctly
"""

import requests
import json
import pymongo
import psycopg2
import time
from urllib.parse import quote

class LineageValidator:
    def __init__(self):
        self.marquez_url = "http://localhost:5007"
        self.mongodb_conn = {
            'host': 'localhost',
            'port': 27017,
            'username': 'admin',
            'password': 'admin123',
            'authSource': 'admin'
        }
        self.postgres_conn = {
            'host': 'localhost',
            'port': 5435,
            'database': 'lineagetutorial',
            'user': 'postgres',
            'password': 'postgres'
        }
    
    def test_marquez_connectivity(self):
        """Test 1: Verify Marquez API is accessible"""
        print("🔍 Testing Marquez API connectivity...")
        try:
            response = requests.get(f"{self.marquez_url}/api/v1/namespaces", timeout=10)
            if response.status_code == 200:
                namespaces = response.json()["namespaces"]
                print(f"✅ Marquez API accessible - Found {len(namespaces)} namespaces")
                for ns in namespaces:
                    print(f"   📁 Namespace: {ns['name']}")
                return True
            else:
                print(f"❌ Marquez API error: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Marquez connection failed: {e}")
            return False
    
    def test_postgres_lineage_datasets(self):
        """Test 2: Verify PostgreSQL datasets are tracked in lineage"""
        print("\n🔍 Testing PostgreSQL dataset lineage...")
        
        expected_datasets = [
            "lineagetutorial.public.adoption_center_1",
            "lineagetutorial.public.adoption_center_2", 
            "lineagetutorial.public.animal_adoptions_combined"
        ]
        
        try:
            namespace = "postgres://host.docker.internal:5435"
            encoded_namespace = quote(namespace, safe='')
            url = f"{self.marquez_url}/api/v1/namespaces/{encoded_namespace}/datasets"
            
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                datasets_data = response.json()
                datasets = [ds["name"] for ds in datasets_data.get("datasets", [])]
                
                print(f"✅ Found {len(datasets)} datasets in PostgreSQL namespace")
                
                missing_datasets = []
                for expected in expected_datasets:
                    if expected in datasets:
                        print(f"   ✅ {expected}")
                    else:
                        print(f"   ❌ {expected} - MISSING")
                        missing_datasets.append(expected)
                
                if not missing_datasets:
                    print("✅ All expected PostgreSQL datasets found in lineage!")
                    return True
                else:
                    print(f"❌ Missing datasets: {missing_datasets}")
                    return False
            else:
                print(f"❌ Failed to get datasets: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ PostgreSQL lineage test failed: {e}")
            return False
    
    def test_mongodb_data_source(self):
        """Test 3: Verify MongoDB data source is accessible"""
        print("\n🔍 Testing MongoDB data source...")
        
        try:
            client = pymongo.MongoClient(**self.mongodb_conn)
            db = client['ecommerce']
            collection = db['customer_profiles']
            
            count = collection.count_documents({})
            if count > 0:
                print(f"✅ MongoDB accessible - Found {count} customer profiles")
                
                # Sample a document to verify structure
                sample = collection.find_one({}, {
                    'customer_id': 1, 'name': 1, 'demographics.income_bracket': 1, '_id': 0
                })
                print(f"   📄 Sample: {sample}")
                client.close()
                return True
            else:
                print("❌ No customer profiles found in MongoDB")
                client.close()
                return False
                
        except Exception as e:
            print(f"❌ MongoDB test failed: {e}")
            return False
    
    def test_postgres_data_consistency(self):
        """Test 4: Verify PostgreSQL data transformations are consistent"""
        print("\n🔍 Testing PostgreSQL data consistency...")
        
        try:
            conn = psycopg2.connect(**self.postgres_conn)
            cursor = conn.cursor()
            
            # Check if tables exist and have data
            tables_to_check = [
                'adoption_center_1',
                'adoption_center_2', 
                'animal_adoptions_combined'
            ]
            
            table_counts = {}
            for table in tables_to_check:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cursor.fetchone()[0]
                    table_counts[table] = count
                    print(f"   📊 {table}: {count} rows")
                except Exception as te:
                    print(f"   ❌ {table}: Error - {te}")
                    table_counts[table] = 0
            
            # Validate transformation logic (UNION should combine both source tables)
            source1_count = table_counts.get('adoption_center_1', 0)
            source2_count = table_counts.get('adoption_center_2', 0)
            target_count = table_counts.get('animal_adoptions_combined', 0)
            
            if source1_count > 0 and source2_count > 0 and target_count > 0:
                expected_count = source1_count + source2_count
                if target_count == expected_count:
                    print(f"✅ Data transformation correct: {source1_count} + {source2_count} = {target_count}")
                    consistency_ok = True
                else:
                    print(f"⚠️  Data inconsistency: Expected {expected_count}, got {target_count}")
                    consistency_ok = False
            else:
                print("⚠️  Some tables are empty - lineage DAG may need to run")
                consistency_ok = False
            
            cursor.close()
            conn.close()
            return consistency_ok
            
        except Exception as e:
            print(f"❌ PostgreSQL consistency test failed: {e}")
            return False
    
    def test_column_lineage_metadata(self):
        """Test 5: Verify column-level lineage metadata"""
        print("\n🔍 Testing column-level lineage metadata...")
        
        try:
            namespace = "postgres://host.docker.internal:5435"
            dataset = "lineagetutorial.public.animal_adoptions_combined"
            encoded_namespace = quote(namespace, safe='')
            
            url = f"{self.marquez_url}/api/v1/namespaces/{encoded_namespace}/datasets/{dataset}"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                dataset_info = response.json()
                fields = dataset_info.get("fields", [])
                
                expected_fields = ["date", "type", "name", "age"]
                actual_fields = [field["name"] for field in fields]
                
                print(f"✅ Found {len(fields)} fields in schema lineage")
                
                missing_fields = []
                for field in expected_fields:
                    if field in actual_fields:
                        field_info = next(f for f in fields if f["name"] == field)
                        print(f"   ✅ {field} ({field_info.get('type', 'unknown')})")
                    else:
                        print(f"   ❌ {field} - MISSING")
                        missing_fields.append(field)
                
                # Check for column lineage facets
                facets = dataset_info.get("facets", {})
                if "columnLineage" in facets:
                    col_lineage = facets["columnLineage"]
                    print(f"   🔗 Column lineage tracking enabled: {len(col_lineage.get('fields', {}))} fields")
                
                return len(missing_fields) == 0
                
            else:
                print(f"❌ Failed to get dataset metadata: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Column lineage test failed: {e}")
            return False
    
    def test_openlineage_events(self):
        """Test 6: Check if OpenLineage events are being captured"""
        print("\n🔍 Testing OpenLineage event capture...")
        
        try:
            # Check for recent lineage events
            url = f"{self.marquez_url}/api/v1/events"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                events_data = response.json()
                events = events_data.get("events", [])
                
                if events:
                    print(f"✅ Found {len(events)} lineage events")
                    
                    # Analyze event types
                    event_types = {}
                    recent_events = events[:5]  # Check last 5 events
                    
                    for event in recent_events:
                        event_type = event.get("eventType", "unknown")
                        event_types[event_type] = event_types.get(event_type, 0) + 1
                        
                        job_name = event.get("job", {}).get("name", "unknown")
                        print(f"   📝 {event_type} event from job: {job_name}")
                    
                    print(f"   📊 Event types: {event_types}")
                    return True
                else:
                    print("⚠️  No lineage events found - DAGs may need to run")
                    return False
            else:
                print(f"❌ Failed to get events: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ OpenLineage events test failed: {e}")
            return False
    
    def run_all_tests(self):
        """Run all validation tests"""
        print("🚀 Starting Lineage Validation Test Suite")
        print("=" * 60)
        
        tests = [
            self.test_marquez_connectivity,
            self.test_mongodb_data_source,
            self.test_postgres_data_consistency,
            self.test_postgres_lineage_datasets,
            self.test_column_lineage_metadata,
            self.test_openlineage_events
        ]
        
        results = []
        for test in tests:
            try:
                result = test()
                results.append(result)
            except Exception as e:
                print(f"❌ Test failed with exception: {e}")
                results.append(False)
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 TEST RESULTS SUMMARY")
        print("=" * 60)
        
        passed = sum(results)
        total = len(results)
        
        test_names = [
            "Marquez API Connectivity",
            "MongoDB Data Source",
            "PostgreSQL Data Consistency", 
            "PostgreSQL Lineage Datasets",
            "Column-Level Lineage Metadata",
            "OpenLineage Event Capture"
        ]
        
        for i, (test_name, result) in enumerate(zip(test_names, results)):
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{i+1}. {test_name}: {status}")
        
        print(f"\nOverall: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
        
        if passed == total:
            print("🎉 All lineage validation tests PASSED! System is working correctly.")
        elif passed >= total * 0.7:
            print("⚠️  Most tests passed - system is mostly functional.")
        else:
            print("❌ Many tests failed - system needs attention.")
        
        return passed == total

if __name__ == "__main__":
    validator = LineageValidator()
    validator.run_all_tests()
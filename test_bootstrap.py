#!/usr/bin/env python3
"""Test bootstrap_runtime functionality directly"""

import os
import sys

# Set test environment
os.environ['MAHOUN_ENV'] = 'test'
os.environ['MAHOUN_TESTING'] = '1'
os.environ['ENABLE_POSTGRES'] = 'false'
os.environ['ENABLE_NEO4J'] = 'false'
os.environ['ENABLE_REDIS'] = 'false'
os.environ['MAHOUN_GRAPH_BACKEND'] = 'disabled_fallback'

print("Testing bootstrap_runtime directly...")
print("Environment variables set for test mode")

try:
    # Import bootstrap function
    from mahoun.bootstrap.runtime import bootstrap_runtime
    print("✅ bootstrap_runtime imported successfully")
    
    # Call bootstrap
    print("Calling bootstrap_runtime()...")
    try:
        result = bootstrap_runtime()
    except Exception as bootstrap_error:
        print(f"Bootstrap error: {bootstrap_error}")
        import traceback
        traceback.print_exc()
        raise
    
    print("✅ bootstrap_runtime completed successfully")
    print(f"✅ Services registered: {list(result.keys())}")
    
    # Check critical services
    critical = ['graph_retriever', 'query', 'gnn']
    found = [s for s in critical if s in result]
    missing = [s for s in critical if s not in result]
    
    print(f"Critical services check:")
    for service in critical:
        if service in result:
            print(f"  ✅ {service}: FOUND")
        else:
            print(f"  ❌ {service}: MISSING")
    
    if not missing:
        print("\n🎉 ALL CRITICAL SERVICES REGISTERED - Task 1.1 SUCCESS!")
    else:
        print(f"\n❌ Task 1.1 INCOMPLETE - missing services: {missing}")
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
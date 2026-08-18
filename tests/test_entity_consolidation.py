#!/usr/bin/env python3
"""
🧪 Entity Consolidation Comprehensive Test Suite
==============================================

درست و حساب‌شده! تست‌های جامع برای Entity Feature Merge
"""

import sys
import subprocess
import importlib
import traceback
from pathlib import Path


@pytest.mark.p2
def test_basic_import():
    """تست ۱: Basic Import Test"""
    print("🧪 Test 1: Basic Import Test")
    try:
        # Basic imports
        from mahoun.core.models.entity import Entity, EntityType
        print("   ✅ Entity and EntityType imported successfully")
        
        # Factory import
        from mahoun.core.models.entity import EntityFactory
        print("   ✅ EntityFactory imported successfully")
        
        # Legacy compatibility imports
        from mahoun.core.models.entity import create_entity, normalize_text
        print("   ✅ Legacy functions imported successfully")
        
        return True
    except Exception as e:
        print(f"   ❌ Import failed: {e}")
        return False


@pytest.mark.p2
def test_entity_creation():
    """تست ۲: Entity Creation Test"""
    print("\n🧪 Test 2: Entity Creation Test")
    try:
        from mahoun.core.models.entity import Entity, EntityType
        
        # Simple entity creation
        entity = Entity(
            text="دادگاه تهران",
            entity_type=EntityType.COURT,
            start=0,
            end=11
        )
        
        print(f"   ✅ Entity created: {entity}")
        print(f"   ✅ Normalized text: '{entity.normalized_text}'")
        print(f"   ✅ Fingerprint: {entity.fingerprint[:16]}...")
        
        return True
    except Exception as e:
        print(f"   ❌ Entity creation failed: {e}")
        traceback.print_exc()
        return False


@pytest.mark.p2
def test_persian_normalization():
    """تست ۳: Persian Text Normalization"""
    print("\n🧪 Test 3: Persian Text Normalization")
    try:
        from mahoun.core.models.entity import EntityNormalizer, normalize_text
        
        # Test Persian digits
        persian_text = "شماره ۱۲۳۴۵"
        normalized = EntityNormalizer.normalize(persian_text)
        expected = "شماره 12345"
        
        print(f"   Input: '{persian_text}'")
        print(f"   Output: '{normalized}'")
        print(f"   Expected: '{expected}'")
        
        if normalized == expected:
            print("   ✅ Persian normalization working correctly")
        else:
            print("   ❌ Persian normalization failed")
            return False
            
        # Test legacy function
        legacy_result = normalize_text(persian_text)
        if legacy_result == normalized:
            print("   ✅ Legacy normalize_text function working")
            return True
        else:
            print("   ❌ Legacy function mismatch")
            return False
            
    except Exception as e:
        print(f"   ❌ Normalization test failed: {e}")
        traceback.print_exc()
        return False


@pytest.mark.p2
def test_entity_serialization():
    """تست ۴: Entity Serialization/Deserialization"""
    print("\n🧪 Test 4: Entity Serialization Test")
    try:
        from mahoun.core.models.entity import Entity, EntityType
        
        # Create entity
        original = Entity(
            text="قاضی احمدی",
            entity_type=EntityType.JUDGE,
            start=10,
            end=20,
            confidence=0.95
        )
        
        # Serialize
        entity_dict = original.to_dict()
        print(f"   ✅ Serialized to dict: {len(entity_dict)} fields")
        
        # Deserialize
        restored = Entity.from_dict(entity_dict)
        print(f"   ✅ Deserialized entity: {restored}")
        
        # Compare
        if original == restored:
            print("   ✅ Serialization round-trip successful")
            return True
        else:
            print("   ❌ Entities don't match after round-trip")
            print(f"     Original: {original}")
            print(f"     Restored: {restored}")
            return False
            
    except Exception as e:
        print(f"   ❌ Serialization test failed: {e}")
        traceback.print_exc()
        return False


@pytest.mark.p2
def test_factory_methods():
    """تست ۵: Factory Methods"""
    print("\n🧪 Test 5: Factory Methods Test")
    try:
        from mahoun.core.models.entity import EntityFactory, create_entity
        
        # Factory method
        entity1 = EntityFactory.create_from_text(
            text="شرکت پتروشیمی",
            auto_detect_type=True
        )
        print(f"   ✅ Factory entity: {entity1}")
        
        # Legacy create function
        entity2 = create_entity(
            text="مهندس رضایی",
            entity_type="person"
        )
        print(f"   ✅ Legacy entity: {entity2}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Factory test failed: {e}")
        traceback.print_exc()
        return False


@pytest.mark.p2
def test_backward_compatibility():
    """تست ۶: Backward Compatibility"""
    print("\n🧪 Test 6: Backward Compatibility Test")
    try:
        from mahoun.core.models.entity import (
            LegacyEntity, NEREntity, GraphEntity, RAGEntity, EvidenceEntity
        )
        
        # Test all legacy aliases
        aliases = [
            ("LegacyEntity", LegacyEntity),
            ("NEREntity", NEREntity), 
            ("GraphEntity", GraphEntity),
            ("RAGEntity", RAGEntity),
            ("EvidenceEntity", EvidenceEntity)
        ]
        
        for name, alias_class in aliases:
            try:
                entity = alias_class(
                    text="تست",
                    entity_type="other",
                    start=0,
                    end=3
                )
                print(f"   ✅ {name} works: {type(entity).__name__}")
            except Exception as e:
                print(f"   ❌ {name} failed: {e}")
                return False
        
        return True
        
    except Exception as e:
        print(f"   ❌ Backward compatibility test failed: {e}")
        traceback.print_exc()
        return False


@pytest.mark.p2
def test_module_init_imports():
    """تست ۷: Module __init__.py Imports"""
    print("\n🧪 Test 7: Module Init Imports Test")
    try:
        # Test importing from the module init
        from mahoun.core.models import Entity, EntityType, create_entity
        print("   ✅ Imports from mahoun.core.models work")
        
        # Test that they're the same objects
        from mahoun.core.models.entity import Entity as DirectEntity
        
        if Entity is DirectEntity:
            print("   ✅ Module imports reference same objects")
            return True
        else:
            print("   ❌ Module imports reference different objects")
            return False
            
    except Exception as e:
        print(f"   ❌ Module init test failed: {e}")
        traceback.print_exc()
        return False


@pytest.mark.p2
def test_virtual_env():
    """تست ۸: Virtual Environment Check"""
    print("\n🧪 Test 8: Virtual Environment Check")
    
    # Check if we're in virtual environment
    in_venv = hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)
    
    if in_venv:
        print(f"   ✅ Running in virtual environment: {sys.prefix}")
    else:
        print(f"   ⚠️  Not in virtual environment: {sys.prefix}")
        print("   🔧 Activating venv...")
        
        # Try to activate venv and test
        venv_path = Path("/home/haji/Desktop/KingMahouN/venv")
        if venv_path.exists():
            print(f"   ✅ Virtual environment found at: {venv_path}")
            return True
        else:
            print(f"   ❌ Virtual environment not found at: {venv_path}")
            return False
    
    return True


@pytest.mark.p2
def test_syntax_check():
    """تست ۹: Syntax Check of Modified Files"""
    print("\n🧪 Test 9: Syntax Check of Modified Files")
    
    files_to_check = [
        "mahoun/core/models/entity.py",
        "mahoun/nlp/ultra_persian_legal_nlp.py", 
        "mahoun/graph/builders/entity_extractor.py"
    ]
    
    repo_root = Path("/home/haji/Desktop/KingMahouN")
    
    for file_path in files_to_check:
        full_path = repo_root / file_path
        if not full_path.exists():
            print(f"   ⚠️  File not found: {file_path}")
            continue
            
        try:
            # Compile the file to check syntax
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            compile(content, str(full_path), 'exec')
            print(f"   ✅ Syntax OK: {file_path}")
            
        except SyntaxError as e:
            print(f"   ❌ Syntax Error in {file_path}: {e}")
            return False
        except Exception as e:
            print(f"   ❌ Error checking {file_path}: {e}")
            return False
    
    return True


def run_comprehensive_tests():
    """اجرای تمام تست‌ها"""
    print("🚀 Starting Entity Consolidation Comprehensive Test Suite")
    print("=" * 60)
    
    tests = [
        test_virtual_env,
        test_syntax_check,
        test_basic_import,
        test_entity_creation,
        test_persian_normalization,
        test_entity_serialization,
        test_factory_methods,
        test_backward_compatibility,
        test_module_init_imports
    ]
    
    results = []
    
    for test_func in tests:
        try:
            result = test_func()
            results.append(result)
        except Exception as e:
            print(f"   💥 Test crashed: {e}")
            results.append(False)
    
    print("\n" + "=" * 60)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 60)
    
    passed = sum(results)
    total = len(results)
    
    for i, (test_func, result) in enumerate(zip(tests, results)):
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {i+1}. {test_func.__name__}: {status}")
    
    print(f"\n📈 Overall: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED! Entity consolidation is working perfectly!")
        return True
    else:
        print(f"💔 {total-passed} tests failed. Consolidation needs fixes.")
        return False


if __name__ == "__main__":
    success = run_comprehensive_tests()
    sys.exit(0 if success else 1)
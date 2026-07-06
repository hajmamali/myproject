#!/usr/bin/env python3
"""
تحلیل P1 Duplicate Definitions از arch_check.py
=====================================

این اسکریپت:
1. P1 duplicates رو از JSON خروجی arch_check استخراج می‌کنه
2. بر اساس تعداد فایل‌های دارای duplicate رتبه‌بندی می‌کنه
3. top candidates برای consolidation رو شناسایی می‌کنه
"""

import json
from pathlib import Path
from collections import defaultdict

def analyze_p1_duplicates(json_path="arch_check_p1_analysis.json"):
    """تحلیل P1 duplicate definitions"""
    
    if not Path(json_path).exists():
        print(f"❌ فایل {json_path} یافت نشد. اول arch_check رو با --json-output اجرا کن.")
        return
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    findings = data.get('findings', [])
    
    # فیلتر P1 Duplicate Definitions
    duplicates = [
        f for f in findings
        if f['severity'] == 'P1' and f['category'] == 'Duplicate Definition'
    ]
    
    print(f"\n{'='*90}")
    print(f"📊 تحلیل P1 Duplicate Definitions")
    print(f"{'='*90}")
    print(f"Total P1 Duplicates: {len(duplicates)}")
    print()
    
    # گروه‌بندی بر اساس تعداد فایل‌ها
    by_file_count = defaultdict(list)
    
    for dup in duplicates:
        file_count = len(dup['files'])
        class_name = dup['title'].split("'")[1] if "'" in dup['title'] else "Unknown"
        by_file_count[file_count].append({
            'name': class_name,
            'files': dup['files'],
            'detail': dup['detail']
        })
    
    # رتبه‌بندی: بیشترین تعداد فایل اول
    print(f"{'='*90}")
    print(f"🔥 TOP DUPLICATE CANDIDATES (رتبه‌بندی بر اساس impact)")
    print(f"{'='*90}\n")
    
    for file_count in sorted(by_file_count.keys(), reverse=True):
        items = by_file_count[file_count]
        print(f"\n{'─'*90}")
        print(f"📁 Duplicates در {file_count} فایل ({len(items)} مورد):")
        print(f"{'─'*90}")
        
        # مرتب‌سازی بر اساس نام
        for item in sorted(items, key=lambda x: x['name']):
            print(f"\n  ▸ {item['name']}")
            print(f"    Impact: {file_count} فایل دارای implementation مجزا")
            print(f"    Files:")
            for f in item['files']:
                # استخراج نام فایل و line number
                parts = f.rsplit(':', 1)
                file_path = parts[0]
                line_no = parts[1] if len(parts) > 1 else '?'
                print(f"      • {file_path}:{line_no}")
    
    # خلاصه آماری
    print(f"\n{'='*90}")
    print(f"📈 STATISTICAL SUMMARY")
    print(f"{'='*90}\n")
    
    total_impact = sum(file_count * len(items) for file_count, items in by_file_count.items())
    
    for file_count in sorted(by_file_count.keys(), reverse=True):
        count = len(by_file_count[file_count])
        impact = file_count * count
        print(f"  {file_count} files: {count:3d} duplicates (impact score: {impact:3d})")
    
    print(f"\n  Total Impact Score: {total_impact}")
    print(f"  Average files per duplicate: {sum(fc * len(items) for fc, items in by_file_count.items()) / len(duplicates):.1f}")
    
    # Top 10 high-impact candidates
    print(f"\n{'='*90}")
    print(f"🎯 TOP 10 HIGH-IMPACT CONSOLIDATION CANDIDATES")
    print(f"{'='*90}\n")
    
    all_items = []
    for file_count, items in by_file_count.items():
        for item in items:
            all_items.append({
                'name': item['name'],
                'file_count': file_count,
                'files': item['files'],
                'impact': file_count  # می‌تونیم formula پیچیده‌تر بذاریم
            })
    
    # مرتب‌سازی بر اساس impact
    top_10 = sorted(all_items, key=lambda x: x['impact'], reverse=True)[:10]
    
    for idx, item in enumerate(top_10, 1):
        print(f"{idx:2d}. {item['name']}")
        print(f"    📊 Impact: {item['file_count']} فایل")
        print(f"    📂 Locations:")
        for f in item['files'][:5]:  # max 5 فایل اول نمایش
            print(f"       • {f}")
        if len(item['files']) > 5:
            print(f"       ... و {len(item['files']) - 5} فایل دیگر")
        print()
    
    # Category breakdown
    print(f"\n{'='*90}")
    print(f"🏷️  CATEGORY BREAKDOWN")
    print(f"{'='*90}\n")
    
    categories = {
        'Config/Settings': ['Config', 'Settings', 'ObservabilityConfig', 'LedgerBackend', 'GuardMode'],
        'Error/Exception': ['Error', 'Exception'],
        'Health/Status': ['Health', 'Status', 'ComponentHealth'],
        'Models/Entities': ['Entity', 'ValidationResult', 'MerkleTree'],
        'LLM/AI': ['LLM', 'Model', 'Provider', 'Capability', 'EmbeddingMode'],
        'NLP/Text': ['Normalizer', 'Extractor', 'Persian'],
        'Security/Governance': ['Security', 'Governance', 'Violation', 'Breach'],
        'Circuit/Resilience': ['CircuitBreaker'],
    }
    
    category_counts = defaultdict(list)
    
    for item in all_items:
        name = item['name']
        categorized = False
        
        for cat, keywords in categories.items():
            if any(kw in name for kw in keywords):
                category_counts[cat].append(name)
                categorized = True
                break
        
        if not categorized:
            category_counts['Other'].append(name)
    
    for cat in sorted(category_counts.keys(), key=lambda c: len(category_counts[c]), reverse=True):
        items = category_counts[cat]
        print(f"  {cat:25s}: {len(items):3d} duplicates")
    
    print(f"\n{'='*90}")
    print(f"✅ تحلیل تکمیل شد")
    print(f"{'='*90}\n")
    
    return duplicates, by_file_count, top_10


if __name__ == "__main__":
    analyze_p1_duplicates()

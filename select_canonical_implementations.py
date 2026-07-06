#!/usr/bin/env python3
"""
انتخاب Canonical Implementation برای هر Duplicate
===================================================

این اسکریپت برای هر duplicate definition:
1. همه implementation‌ها رو بررسی می‌کنه
2. بر اساس معیارهای مختلف امتیاز می‌ده
3. بهترین candidate رو به عنوان canonical انتخاب می‌کنه
4. یک migration plan تولید می‌کنه

معیارهای امتیازدهی:
- Location: mahoun/core > mahoun/other > mahoun/ultra_systems
- Completeness: خطوط کد، docstring، type hints
- Usage: تعداد import‌ها در کدبیس
- Quality: test coverage، validation
"""

import ast
import json
from pathlib import Path
from collections import defaultdict
from dataclasses import dataclass
from typing import List, Dict, Optional

@dataclass
class Implementation:
    """اطلاعات یک implementation"""
    name: str
    file_path: str
    line_no: int
    score: float = 0.0
    
    # امتیازهای جزئی
    location_score: float = 0.0
    completeness_score: float = 0.0
    usage_score: float = 0.0
    quality_score: float = 0.0
    
    # اطلاعات اضافی
    lines_of_code: int = 0
    has_docstring: bool = False
    has_type_hints: bool = False
    import_count: int = 0
    
    def __repr__(self):
        return f"Implementation({self.name}, {self.file_path}:{self.line_no}, score={self.score:.2f})"


def score_location(file_path: str) -> float:
    """امتیازدهی بر اساس location"""
    path = file_path.lower()
    
    # Core modules = highest priority
    if '/core/models' in path and not 'protocols' in path:
        return 10.0
    elif '/core/exceptions' in path and 'exceptions_v2' not in path:
        return 9.0
    elif '/core/' in path and 'governance' not in path:
        return 8.0
    
    # Domain-specific canonical locations
    elif '/schemas/' in path and not 'contracts' in path:
        return 7.0
    elif '/reasoning/' in path and 'ultra' not in path:
        return 7.0
    elif '/rag/' in path and 'ultra' not in path:
        return 7.0
    elif '/graph/' in path and 'ultra' not in path:
        return 7.0
    
    # Specialized but acceptable
    elif '/infrastructure/' in path:
        return 6.0
    elif '/pipelines/' in path:
        return 5.0
    elif '/agents/' in path and 'archive' not in path:
        return 5.0
    
    # Deprecated or experimental
    elif '/ultra_systems/' in path:
        return 2.0
    elif '/archive/' in path:
        return 1.0
    elif 'exceptions_v2' in path:
        return 3.0  # exceptions_v2 is newer but not canonical
    
    # Default
    else:
        return 4.0


def analyze_class_completeness(file_path: str, class_name: str, line_no: int) -> Dict:
    """تحلیل کامل بودن یک class"""
    try:
        source = Path(file_path).read_text(encoding='utf-8', errors='ignore')
        tree = ast.parse(source)
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == class_name:
                # خطوط کد (تقریبی)
                if hasattr(node, 'end_lineno'):
                    loc = node.end_lineno - node.lineno
                else:
                    loc = 10  # default guess
                
                # Docstring
                has_docstring = (
                    node.body and 
                    isinstance(node.body[0], ast.Expr) and 
                    isinstance(node.body[0].value, ast.Constant) and 
                    isinstance(node.body[0].value.value, str)
                )
                
                # Type hints در methods
                type_hint_count = 0
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        if item.returns:
                            type_hint_count += 1
                        for arg in item.args.args:
                            if arg.annotation:
                                type_hint_count += 1
                
                has_type_hints = type_hint_count > 0
                
                return {
                    'loc': loc,
                    'has_docstring': has_docstring,
                    'has_type_hints': has_type_hints,
                    'type_hint_count': type_hint_count
                }
    except Exception as e:
        pass
    
    return {'loc': 0, 'has_docstring': False, 'has_type_hints': False, 'type_hint_count': 0}


def count_imports(root: Path, class_name: str) -> int:
    """تعداد فایل‌هایی که این class رو import می‌کنن"""
    import_count = 0
    
    for py_file in root.rglob("*.py"):
        if 'test' in str(py_file).lower():
            continue  # skip tests
        
        try:
            source = py_file.read_text(encoding='utf-8', errors='ignore')
            if f"import {class_name}" in source or f"from " in source and class_name in source:
                import_count += 1
        except:
            pass
    
    return import_count


def score_implementation(impl: Implementation, root: Path) -> Implementation:
    """محاسبه امتیاز کلی implementation"""
    
    # 1. Location score (وزن: 40%)
    impl.location_score = score_location(impl.file_path)
    
    # 2. Completeness score (وزن: 30%)
    info = analyze_class_completeness(impl.file_path, impl.name, impl.line_no)
    impl.lines_of_code = info['loc']
    impl.has_docstring = info['has_docstring']
    impl.has_type_hints = info['has_type_hints']
    
    completeness = 0.0
    if impl.lines_of_code > 5:
        completeness += 3.0
    if impl.lines_of_code > 20:
        completeness += 2.0
    if impl.has_docstring:
        completeness += 3.0
    if impl.has_type_hints:
        completeness += 2.0
    
    impl.completeness_score = min(completeness, 10.0)
    
    # 3. Usage score (وزن: 20%) - expensive, skip for now
    # impl.import_count = count_imports(root, impl.name)
    # impl.usage_score = min(impl.import_count * 2, 10.0)
    impl.usage_score = 5.0  # default neutral
    
    # 4. Quality score (وزن: 10%) - heuristic
    quality = 5.0  # default
    if 'test' in impl.file_path.lower():
        quality = 1.0  # test-only implementations
    elif 'archive' in impl.file_path.lower():
        quality = 2.0
    elif impl.file_path.endswith('_v2.py'):
        quality = 4.0  # newer but experimental
    
    impl.quality_score = quality
    
    # وزن‌دهی نهایی
    impl.score = (
        impl.location_score * 0.4 +
        impl.completeness_score * 0.3 +
        impl.usage_score * 0.2 +
        impl.quality_score * 0.1
    )
    
    return impl


def select_canonical(duplicates: List[Implementation], root: Path) -> Implementation:
    """انتخاب canonical implementation از لیست"""
    
    # امتیازدهی به همه
    scored = [score_implementation(impl, root) for impl in duplicates]
    
    # مرتب‌سازی بر اساس امتیاز
    scored.sort(key=lambda x: x.score, reverse=True)
    
    return scored[0], scored


def generate_migration_plan(canonical: Implementation, others: List[Implementation]) -> str:
    """تولید migration plan"""
    lines = []
    lines.append(f"## Migration Plan: {canonical.name}")
    lines.append("")
    lines.append(f"**Canonical Location:** `{canonical.file_path}:{canonical.line_no}`")
    lines.append(f"**Score:** {canonical.score:.2f}/10.0")
    lines.append("")
    lines.append("### Why This is Canonical:")
    lines.append(f"- Location Score: {canonical.location_score:.1f}/10 ({'core' if '/core/' in canonical.file_path else 'domain'})")
    lines.append(f"- Completeness: {canonical.completeness_score:.1f}/10 (LOC={canonical.lines_of_code}, docstring={'✓' if canonical.has_docstring else '✗'}, types={'✓' if canonical.has_type_hints else '✗'})")
    lines.append(f"- Usage: {canonical.usage_score:.1f}/10")
    lines.append(f"- Quality: {canonical.quality_score:.1f}/10")
    lines.append("")
    lines.append("### Duplicates to Remove:")
    lines.append("")
    
    for impl in others:
        if impl.file_path == canonical.file_path:
            continue
        lines.append(f"- `{impl.file_path}:{impl.line_no}` (score={impl.score:.2f})")
    
    lines.append("")
    lines.append("### Migration Steps:")
    lines.append("")
    lines.append("1. Verify canonical implementation has all features from duplicates")
    lines.append("2. Update all imports to point to canonical location:")
    lines.append(f"   ```python")
    lines.append(f"   from {canonical.file_path.replace('/', '.').replace('.py', '')} import {canonical.name}")
    lines.append(f"   ```")
    lines.append("3. Add deprecation warnings to duplicate locations")
    lines.append("4. Remove duplicates after migration period")
    lines.append("")
    
    return "\n".join(lines)


def main():
    """Main analysis"""
    
    # بارگذاری داده‌های arch_check
    json_path = Path("arch_check_p1_analysis.json")
    if not json_path.exists():
        print("❌ فایل arch_check_p1_analysis.json یافت نشد")
        return
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    findings = data.get('findings', [])
    duplicates = [
        f for f in findings
        if f['severity'] == 'P1' and f['category'] == 'Duplicate Definition'
    ]
    
    print(f"\n{'='*90}")
    print(f"🔍 تحلیل و انتخاب Canonical Implementations")
    print(f"{'='*90}\n")
    
    root = Path("mahoun")
    
    # گروه‌بندی بر اساس نام class
    by_class = defaultdict(list)
    
    for dup in duplicates:
        class_name = dup['title'].split("'")[1] if "'" in dup['title'] else "Unknown"
        
        for file_loc in dup['files']:
            parts = file_loc.rsplit(':', 1)
            file_path = parts[0]
            line_no = int(parts[1]) if len(parts) > 1 else 0
            
            impl = Implementation(
                name=class_name,
                file_path=file_path,
                line_no=line_no
            )
            by_class[class_name].append(impl)
    
    # تحلیل top 20 high-impact
    print("📊 تحلیل Top 20 High-Impact Duplicates:\n")
    
    # مرتب‌سازی بر اساس تعداد فایل
    sorted_classes = sorted(by_class.items(), key=lambda x: len(x[1]), reverse=True)[:20]
    
    results = []
    
    for class_name, impls in sorted_classes:
        print(f"  ▸ {class_name} ({len(impls)} implementations)...")
        
        canonical, scored = select_canonical(impls, root)
        
        results.append({
            'class': class_name,
            'canonical': canonical,
            'all_scored': scored
        })
        
        print(f"    ✓ Canonical: {canonical.file_path}:{canonical.line_no} (score={canonical.score:.2f})")
    
    # تولید گزارش
    print(f"\n{'='*90}")
    print("📝 تولید Migration Plans...")
    print(f"{'='*90}\n")
    
    migration_doc = []
    migration_doc.append("# P1 Duplicate Consolidation — Migration Plans")
    migration_doc.append("")
    migration_doc.append("**Generated:** " + str(Path.cwd()))
    migration_doc.append("")
    migration_doc.append("این سند شامل migration plan برای top 20 duplicate definitions است.")
    migration_doc.append("")
    migration_doc.append("---")
    migration_doc.append("")
    
    for result in results:
        canonical = result['canonical']
        others = [impl for impl in result['all_scored'] if impl.file_path != canonical.file_path]
        
        plan = generate_migration_plan(canonical, others)
        migration_doc.append(plan)
        migration_doc.append("---")
        migration_doc.append("")
    
    # ذخیره
    output_path = Path("P1_MIGRATION_PLANS.md")
    output_path.write_text("\n".join(migration_doc), encoding='utf-8')
    
    print(f"✅ Migration plans ذخیره شد: {output_path}")
    
    # خلاصه‌ی سریع
    print(f"\n{'='*90}")
    print("🎯 QUICK SUMMARY — Top 10 Canonical Locations")
    print(f"{'='*90}\n")
    
    for i, result in enumerate(results[:10], 1):
        canonical = result['canonical']
        print(f"{i:2d}. {canonical.name:30s} → {canonical.file_path}")
    
    print()


if __name__ == "__main__":
    main()

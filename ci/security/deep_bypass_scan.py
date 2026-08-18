#!/usr/bin/env python3
"""
Deep Bypass Vector Scanner
===========================

این اسکریپت به دنبال bypass vectorهای پنهان می‌گرده که ممکنه از دید معمولی فرار کنن:

1. Global variable leakage (neo4j_driver accessible)
2. Monkey-patching governance functions
3. Direct __dict__ manipulation
4. Reflection/getattr abuse
5. Import-time side effects
6. Context manager bypasses
"""

import ast
import sys
from pathlib import Path
from typing import List, Dict, Tuple
from dataclasses import dataclass


@dataclass
class DeepThreat:
    """یک تهدید امنیتی عمیق"""
    file_path: str
    line_number: int
    threat_type: str
    severity: str  # CRITICAL, HIGH, MEDIUM
    description: str
    evidence: str


class DeepBypassScanner(ast.NodeVisitor):
    """
    اسکنر عمیق برای پیدا کردن bypass vectorهای پیچیده
    """
    
    def __init__(self, file_path: str, source: str):
        self.file_path = file_path
        self.source = source
        self.lines = source.splitlines()
        self.threats: List[DeepThreat] = []
    
    def visit_Attribute(self, node: ast.Attribute) -> None:
        """چک کردن دسترسی مستقیم به __dict__ یا private attributes"""
        if node.attr in ('__dict__', '__class__', '__globals__'):
            self.threats.append(DeepThreat(
                file_path=self.file_path,
                line_number=node.lineno,
                threat_type="REFLECTION_ABUSE",
                severity="HIGH",
                description=f"دسترسی به {node.attr} - می‌تونه برای bypass استفاده بشه",
                evidence=self._get_line(node.lineno)
            ))
        
        self.generic_visit(node)
    
    def visit_Call(self, node: ast.Call) -> None:
        """چک کردن توابع خطرناک"""
        dangerous_funcs = {
            'eval': 'CRITICAL',
            'exec': 'CRITICAL', 
            'compile': 'HIGH',
            'getattr': 'MEDIUM',
            'setattr': 'HIGH',
            'delattr': 'HIGH',
            '__import__': 'HIGH',
        }
        
        if isinstance(node.func, ast.Name):
            if node.func.id in dangerous_funcs:
                self.threats.append(DeepThreat(
                    file_path=self.file_path,
                    line_number=node.lineno,
                    threat_type="DANGEROUS_FUNCTION",
                    severity=dangerous_funcs[node.func.id],
                    description=f"استفاده از {node.func.id}() - خطر bypass بالا",
                    evidence=self._get_line(node.lineno)
                ))
        
        # چک کردن monkey patching
        if isinstance(node.func, ast.Attribute):
            if node.func.attr == 'patch' or 'mock' in node.func.attr.lower():
                self.threats.append(DeepThreat(
                    file_path=self.file_path,
                    line_number=node.lineno,
                    threat_type="MONKEY_PATCH",
                    severity="HIGH",
                    description="Monkey patching - می‌تونه governance رو دور بزنه",
                    evidence=self._get_line(node.lineno)
                ))
        
        self.generic_visit(node)
    
    def visit_Import(self, node: ast.Import) -> None:
        """چک کردن import های خطرناک"""
        dangerous_imports = ['unittest.mock', 'mock', 'importlib']
        for alias in node.names:
            if alias.name in dangerous_imports:
                self.threats.append(DeepThreat(
                    file_path=self.file_path,
                    line_number=node.lineno,
                    threat_type="DANGEROUS_IMPORT",
                    severity="MEDIUM",
                    description=f"Import {alias.name} - potential bypass tool",
                    evidence=self._get_line(node.lineno)
                ))
        self.generic_visit(node)
    
    def visit_Global(self, node: ast.Global) -> None:
        """چک کردن تغییر global variables"""
        for name in node.names:
            if 'driver' in name.lower() or 'connection' in name.lower():
                self.threats.append(DeepThreat(
                    file_path=self.file_path,
                    line_number=node.lineno,
                    threat_type="GLOBAL_MUTATION",
                    severity="HIGH",
                    description=f"تغییر متغیر global {name} - خطر bypass",
                    evidence=self._get_line(node.lineno)
                ))
        self.generic_visit(node)
    
    def _get_line(self, line_no: int) -> str:
        if 0 < line_no <= len(self.lines):
            return self.lines[line_no - 1].strip()
        return ""


def scan_for_global_leaks(repo_root: Path) -> List[DeepThreat]:
    """
    اسکن برای global variable leakage
    
    این خطرناک‌ترین bypass هست: اگه کسی بتونه مستقیم به api.database.neo4j_driver
    دسترسی پیدا کنه، کل governance رو دور می‌زنه
    """
    threats = []
    
    # پیدا کردن همه جاهایی که neo4j_driver رو import می‌کنن
    for py_file in repo_root.rglob("*.py"):
        if 'test' in str(py_file) or '__pycache__' in str(py_file):
            continue
        
        try:
            content = py_file.read_text(encoding='utf-8')
            
            # چک ۱: import مستقیم neo4j_driver
            if 'from api.database import' in content and 'neo4j_driver' in content:
                for i, line in enumerate(content.splitlines(), 1):
                    if 'from api.database import' in line and 'neo4j_driver' in line:
                        threats.append(DeepThreat(
                            file_path=str(py_file),
                            line_number=i,
                            threat_type="GLOBAL_DRIVER_IMPORT",
                            severity="CRITICAL",
                            description="❌ CRITICAL: import مستقیم neo4j_driver - کل governance رو bypass می‌کنه!",
                            evidence=line.strip()
                        ))
            
            # چک ۲: دسترسی مستقیم به api.database.neo4j_driver
            if 'api.database.neo4j_driver' in content:
                for i, line in enumerate(content.splitlines(), 1):
                    if 'api.database.neo4j_driver' in line:
                        threats.append(DeepThreat(
                            file_path=str(py_file),
                            line_number=i,
                            threat_type="GLOBAL_DRIVER_ACCESS",
                            severity="CRITICAL",
                            description="❌ CRITICAL: دسترسی مستقیم به neo4j_driver - bypass کامل!",
                            evidence=line.strip()
                        ))
        
        except Exception:
            pass
    
    return threats


def scan_file_deep(file_path: Path) -> List[DeepThreat]:
    """اسکن عمیق یک فایل"""
    try:
        source = file_path.read_text(encoding='utf-8')
        tree = ast.parse(source, filename=str(file_path))
        
        scanner = DeepBypassScanner(str(file_path), source)
        scanner.visit(tree)
        
        return scanner.threats
    
    except Exception as e:
        return []


def main():
    workspace = Path(__file__).parent.parent.parent
    
    print("🔍 شروع اسکن عمیق برای bypass vectorها...")
    print("=" * 80)
    print()
    
    # اسکن ۱: Global variable leaks (خطرناک‌ترین!)
    print("📍 چک ۱: Global Variable Leakage")
    global_threats = scan_for_global_leaks(workspace)
    
    if global_threats:
        print(f"⚠️  پیدا شد {len(global_threats)} تهدید CRITICAL!")
        for threat in global_threats:
            print(f"\n  🔴 {threat.file_path}:{threat.line_number}")
            print(f"     {threat.description}")
            print(f"     کد: {threat.evidence}")
    else:
        print("✅ هیچ global leak پیدا نشد")
    
    print()
    print("-" * 80)
    print()
    
    # اسکن ۲: Deep code analysis
    print("📍 چک ۲: Deep Code Analysis (reflection, eval, etc.)")
    
    deep_threats = []
    for py_file in workspace.rglob("*.py"):
        if 'test' not in str(py_file) and '__pycache__' not in str(py_file):
            if 'api/' in str(py_file) or 'mahoun/' in str(py_file):
                threats = scan_file_deep(py_file)
                if threats:
                    deep_threats.extend(threats)
    
    if deep_threats:
        print(f"⚠️  پیدا شد {len(deep_threats)} تهدید بالقوه")
        
        # گروه‌بندی بر اساس severity
        critical = [t for t in deep_threats if t.severity == "CRITICAL"]
        high = [t for t in deep_threats if t.severity == "HIGH"]
        
        if critical:
            print(f"\n🔴 CRITICAL: {len(critical)}")
            for t in critical[:5]:  # فقط ۵ تا اول
                print(f"   {t.file_path}:{t.line_number} - {t.description}")
        
        if high:
            print(f"\n🟠 HIGH: {len(high)}")
            for t in high[:5]:
                print(f"   {t.file_path}:{t.line_number} - {t.description}")
    else:
        print("✅ هیچ تهدید عمیقی پیدا نشد")
    
    print()
    print("=" * 80)
    
    # نتیجه‌گیری
    total_critical = len([t for t in (global_threats + deep_threats) if t.severity == "CRITICAL"])
    
    if total_critical > 0:
        print(f"\n❌ پیدا شد {total_critical} تهدید CRITICAL")
        print("⚠️  این‌ها می‌تونن governance رو bypass کنن!")
        return 1
    else:
        print("\n✅ هیچ تهدید CRITICAL پیدا نشد")
        print("✅ سیستم از نظر bypass vectorهای شناخته‌شده امنه")
        return 0


if __name__ == '__main__':
    sys.exit(main())

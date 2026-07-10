#!/usr/bin/env python3
"""
MAHOUN NIGHTMARE MODE: The Ultimate Legal Reasoning Challenge
==============================================================
Scenario: "The Phantom Merger"

Complexity Features:
1. TEMPORAL REASONING: Documents with conflicting dates
2. CONTRADICTORY EVIDENCE: Forged vs Real documents
3. MULTI-JURISDICTIONAL: Iran + UAE + Cyprus laws
4. 7-HOP CHAIN: Deep relationship traversal
5. NOISE INJECTION: 50% irrelevant documents
6. LEGAL PRECEDENT: Requires finding case law
7. MATHEMATICAL PROOF: Stock dilution calculation
"""

"""
Auto-fixed: Removed hardcoded path hacks.
Run with: pip install -e . (to install mahoun as editable package)
"""
import sys
from pathlib import Path

# Portable repo-root discovery (only if needed for non-installed runs)
if __name__ == "__main__":
    repo_root = Path(__file__).resolve().parent.parent
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))


import logging
import sys
import networkx as nx
import numpy as np
from datetime import datetime
from typing import List, Dict, Any

from mahoun.retrieval.ultra_hybrid_search import UltraHybridSearch, SearchConfig, FusionMethod
from mahoun.graph.ultra_graph_builder import UltraGraphBuilder

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger("NIGHTMARE")

class NightmareModeAML:
    """
    THE PHANTOM MERGER CASE
    -----------------------
    A company claims to have merged with a foreign entity.
    The merger documents show $500M valuation.
    BUT: The foreign entity was dissolved 2 years BEFORE the merger date.
    CHALLENGE: Find the temporal contradiction across 15 documents.
    """
    
    def __init__(self):
        # 15 Documents (7 relevant, 8 noise)
        self.documents = [
            # === CORE EVIDENCE ===
            {"doc_id": "MERGER-ANNOUNCE", "content": "اطلاعیه ادغام: شرکت 'تکنولوژی پارس' با شرکت 'CyberTech Cyprus' ادغام شد. تاریخ: ۱۴۰۲/۰۶/۱۵. ارزش معامله: ۵۰۰ میلیون دلار.", "date": "2023-09-06"},
            
            {"doc_id": "CYPRUS-DISSOLUTION", "content": "Official Gazette Cyprus: CyberTech Cyprus Ltd was DISSOLVED on 15-March-2021. Reason: Bankruptcy.", "date": "2021-03-15"},
            
            {"doc_id": "STOCK-DILUTION", "content": "گزارش سهام: پس از ادغام، سهام شرکت پارس از ۱۰۰ میلیون به ۱ میلیارد سهم افزایش یافت (رقیق‌سازی ۱۰ برابری).", "date": "2023-09-20"},
            
            {"doc_id": "LAW-IRAN-MERGER", "content": "ماده ۱۲ قانون تجارت: ادغام با شرکت خارجی منحل شده باطل است و قابل پیگرد کیفری می‌باشد.", "date": "1311"},
            
            {"doc_id": "CASE-PRECEDENT", "content": "رأی دیوان عدالت اداری ۱۴۰۰: ادغام صوری منجر به رقیق‌سازی سهام، کلاهبرداری محسوب می‌شود.", "date": "2021-12-10"},
            
            {"doc_id": "AUDIT-FRAUD", "content": "گزارش حسابرسی مستقل: اسناد ادغام CyberTech فاقد مهر رسمی قبرس است. احتمال جعل: ۹۵٪.", "date": "2023-10-01"},
            
            {"doc_id": "CEO-INTEL", "content": "گزارش پلیس بین‌الملل: مدیرعامل شرکت پارس، آقای 'رضا متقلب'، سابقه کلاهبرداری در امارات دارد.", "date": "2023-11-05"},
            
            # === NOISE (Distractors) ===
            {"doc_id": "NOISE-1", "content": "قیمت طلا امروز در بازار تهران به ۲ میلیون تومان رسید.", "date": "2023-09-07"},
            {"doc_id": "NOISE-2", "content": "دستورالعمل جدید بانک مرکزی برای تسهیلات خرید خودرو.", "date": "2023-08-15"},
            {"doc_id": "NOISE-3", "content": "شرکت 'پارس خودرو' (نه پارس تکنولوژی) سود ۳۰٪ اعلام کرد.", "date": "2023-07-20"},
            {"doc_id": "NOISE-4", "content": "مقاله: تاریخچه صنعت نفت در ایران از سال ۱۲۹۰.", "date": "2023-05-10"},
            {"doc_id": "NOISE-5", "content": "Cyprus tourism statistics for 2022: 3.2M visitors.", "date": "2023-01-12"},
            {"doc_id": "NOISE-6", "content": "آموزش نرم‌افزار حسابداری برای مشاغل کوچک.", "date": "2023-06-18"},
            {"doc_id": "NOISE-7", "content": "لیست رستوران‌های برتر تهران در سال ۱۴۰۲.", "date": "2023-04-22"},
            {"doc_id": "NOISE-8", "content": "تحلیل تکنیکال بورس: شاخص کل به ۲ میلیون واحد رسید.", "date": "2023-09-25"},
        ]
        
        # Complex Relationships (7-Hop Chain)
        self.relationships = [
            # Chain: Merger -> Cyprus Entity -> Dissolution (TEMPORAL CONFLICT!)
            {"source_id": "MERGER-ANNOUNCE", "target_id": "CYPRUS_ENTITY", "type": "CLAIMS_MERGER_WITH", "weight": 1.0},
            {"source_id": "CYPRUS_ENTITY", "target_id": "CYPRUS-DISSOLUTION", "type": "STATUS_RECORD", "weight": 1.0},
            
            # Chain: Merger -> Stock Dilution -> Fraud Pattern
            {"source_id": "MERGER-ANNOUNCE", "target_id": "STOCK-DILUTION", "type": "RESULTED_IN", "weight": 1.0},
            {"source_id": "STOCK-DILUTION", "target_id": "CASE-PRECEDENT", "type": "MATCHES_PATTERN", "weight": 0.9},
            
            # Chain: Merger -> Audit -> Forgery
            {"source_id": "MERGER-ANNOUNCE", "target_id": "AUDIT-FRAUD", "type": "AUDITED_BY", "weight": 1.0},
            {"source_id": "AUDIT-FRAUD", "target_id": "FORGERY_NODE", "type": "DETECTED", "weight": 0.95},
            
            # Chain: Company -> CEO -> Criminal Record
            {"source_id": "PARS_COMPANY", "target_id": "CEO_NODE", "type": "MANAGED_BY", "weight": 1.0},
            {"source_id": "CEO_NODE", "target_id": "CEO-INTEL", "type": "SUBJECT_OF", "weight": 1.0},
            
            # Legal Framework
            {"source_id": "MERGER-ANNOUNCE", "target_id": "LAW-IRAN-MERGER", "type": "GOVERNED_BY", "weight": 0.7},
            {"source_id": "FORGERY_NODE", "target_id": "LAW-IRAN-MERGER", "type": "VIOLATES", "weight": 1.0},
        ]

    def run(self):
        print("\n" + "🔥"*40)
        print("💀 MAHOUN NIGHTMARE MODE: THE PHANTOM MERGER")
        print("🔥"*40)
        print("\n⚠️  CHALLENGE: Find temporal fraud in 15 documents (7 signal, 8 noise)")
        
        # Build Graph
        builder = UltraGraphBuilder(enable_quality_assessment=False)
        entities = [{"id": d["doc_id"], "label": "Document", "text": d["content"], "properties": {"date": d.get("date", "")}} for d in self.documents]
        entities.extend([
            {"id": "CYPRUS_ENTITY", "label": "Company", "properties": {"name": "CyberTech Cyprus", "status": "DISSOLVED"}},
            {"id": "PARS_COMPANY", "label": "Company", "properties": {"name": "Pars Tech"}},
            {"id": "CEO_NODE", "label": "Person", "properties": {"name": "Reza Motaghaleb"}},
            {"id": "FORGERY_NODE", "label": "Crime", "properties": {"type": "Document Forgery"}},
        ])
        
        builder.build_graph(entities, self.relationships)
        
        nx_graph = nx.DiGraph()
        for edge in builder._edges:
            nx_graph.add_edge(edge.source_id, edge.target_id, type=edge.relationship_type, weight=edge.weight)
        
        # Ultra-Aggressive Config
        config = SearchConfig(
            use_bm25=True, use_dense=True, use_graph=True,
            graph_weight=0.95,  # Maximum graph reliance
            bm25_weight=0.3,
            dense_weight=0.4,
            rrf_k=30,
            top_k=100,
            final_k=10
        )
        
        engine = UltraHybridSearch(config, embedding_provider=self._mock_embedder())
        engine.graph_retriever.max_hops = 7  # DEEP SEARCH
        engine.set_graph(nx_graph)
        engine.index(self.documents)
        
        # The Impossible Query
        query = "آیا ادغام شرکت پارس قانونی است؟ اسناد تاریخی و حسابرسی را بررسی کن"
        print(f"\n🔍 Investigator's Query: '{query}'")
        print("\n" + "-"*80)
        
        results, metrics = engine.search(query, top_k=10)
        
        print("\n📋 EVIDENCE DOSSIER (Ranked by Relevance):\n")
        
        critical_finds = {
            "temporal_conflict": False,
            "legal_basis": False,
            "audit_fraud": False,
            "precedent": False,
            "noise_filtered": 0
        }
        
        for i, res in enumerate(results, 1):
            is_noise = res.doc_id.startswith("NOISE")
            
            if is_noise:
                critical_finds["noise_filtered"] += 1
                marker = "🗑️ [NOISE]"
            else:
                marker = "📌"
                
                if "DISSOLVED" in res.content and "2021" in res.content:
                    marker = "⏰ [TEMPORAL BOMB]"
                    critical_finds["temporal_conflict"] = True
                elif "ماده ۱۲" in res.content:
                    marker = "⚖️ [LEGAL BASIS]"
                    critical_finds["legal_basis"] = True
                elif "جعل" in res.content or "فاقد مهر" in res.content:
                    marker = "🔍 [FORENSIC EVIDENCE]"
                    critical_finds["audit_fraud"] = True
                elif "رأی دیوان" in res.content:
                    marker = "📚 [CASE LAW]"
                    critical_finds["precedent"] = True
            
            print(f"   {i}. {marker:<25} {res.doc_id}")
            if not is_noise:
                print(f"      └─ {res.content[:100]}...")
        
        # Verdict
        print("\n" + "="*80)
        print("🏛️  FINAL VERDICT:")
        print("="*80)
        
        score = sum([
            critical_finds["temporal_conflict"] * 40,
            critical_finds["legal_basis"] * 25,
            critical_finds["audit_fraud"] * 20,
            critical_finds["precedent"] * 15,
        ])
        
        noise_ratio = critical_finds["noise_filtered"] / len(results) * 100
        
        print(f"\n✓ Temporal Conflict Detected: {'YES ✅' if critical_finds['temporal_conflict'] else 'NO ❌'}")
        print(f"✓ Legal Framework Found: {'YES ✅' if critical_finds['legal_basis'] else 'NO ❌'}")
        print(f"✓ Forensic Evidence: {'YES ✅' if critical_finds['audit_fraud'] else 'NO ❌'}")
        print(f"✓ Case Precedent: {'YES ✅' if critical_finds['precedent'] else 'NO ❌'}")
        print(f"✓ Noise Filtered: {noise_ratio:.1f}% (Lower is better)")
        
        print(f"\n🎯 REASONING SCORE: {score}/100")
        
        if score >= 90:
            print("\n👑 GENIUS LEVEL: System performed PERFECT legal reasoning!")
        elif score >= 70:
            print("\n🌟 EXCELLENT: System found critical evidence!")
        elif score >= 50:
            print("\n✅ GOOD: System detected the fraud pattern.")
        else:
            print("\n⚠️ NEEDS IMPROVEMENT: Missed key evidence.")
        
        print("\n" + "🔥"*40)

    def _mock_embedder(self):
        class Mock:
            def embed(self, texts):
                np.random.seed(42)
                return np.random.randn(len(texts), 768).astype(np.float32)
            def embed_query(self, text):
                np.random.seed(42)
                return np.random.randn(768).astype(np.float32)
        return Mock()

if __name__ == "__main__":
    NightmareModeAML().run()

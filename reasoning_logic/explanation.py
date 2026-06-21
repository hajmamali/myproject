"""
Explanation Generation System
==============================

Generate human-readable explanations for reasoning results.

Features:
- Natural language explanation generation
- Proof tree visualization
- Step-by-step reasoning traces
- Multi-language support with proper i18n
- Customizable explanation styles

Author: MAHOUN Team
"""

from typing import List, Dict, Optional, Any
from enum import Enum
from dataclasses import dataclass
import os
import logging

from reasoning_logic.core import Fact, Rule, Atom
from reasoning_logic.backward_chaining import ProofNode, ProofStatus

logger = logging.getLogger(__name__)


class ExplanationStyle(Enum):
    """Style of explanation"""
    CONCISE = "concise"  # Brief summary
    DETAILED = "detailed"  # Full step-by-step
    TECHNICAL = "technical"  # With logical notation
    NARRATIVE = "narrative"  # Story-like explanation


class ExplanationLanguage(Enum):
    """Language for explanation"""
    ENGLISH = "en"
    FARSI = "fa"


@dataclass
class ExplanationConfig:
    """Configuration for explanation generation"""
    style: ExplanationStyle = ExplanationStyle.DETAILED
    language: ExplanationLanguage = ExplanationLanguage.ENGLISH
    max_depth: int = 10
    include_confidence: bool = True
    include_rules: bool = True
    unicode_symbols: bool = True


class I18nProvider:
    """
    Internationalization provider for explanations
    
    Uses a simple dictionary-based approach with fallback to English.
    For production, consider using gettext or similar framework.
    """
    
    TRANSLATIONS = {
        ExplanationLanguage.ENGLISH: {
            'proved': 'Successfully proved',
            'failed': 'Failed to prove',
            'using_rule': 'Using rule',
            'known_fact': 'This is a known fact',
            'because': 'because',
            'and': 'and',
            'therefore': 'Therefore',
            'step': 'Step',
            'if': 'If',
            'then': 'then',
            'is_true': 'is true',
            'are_all_true': 'are all true',
            'must_be_true': 'must be true',
            'we_know_that': 'We know that',
            'we_attempted': 'We attempted to prove',
            'to_prove': 'To prove',
            'we_used_rule': 'we used a rule that states',
        },
        ExplanationLanguage.FARSI: {
            'proved': 'با موفقیت اثبات شد',
            'failed': 'اثبات نشد',
            'using_rule': 'با استفاده از قانون',
            'known_fact': 'این یک واقعیت شناخته شده است',
            'because': 'زیرا',
            'and': 'و',
            'therefore': 'بنابراین',
            'step': 'مرحله',
            'if': 'اگر',
            'then': 'آنگاه',
            'is_true': 'درست است',
            'are_all_true': 'همگی درست هستند',
            'must_be_true': 'باید درست باشد',
            'we_know_that': 'ما می‌دانیم که',
            'we_attempted': 'ما تلاش کردیم تا اثبات کنیم',
            'to_prove': 'برای اثبات',
            'we_used_rule': 'ما از قانونی استفاده کردیم که بیان می‌کند',
        }
    }
    
    def __init__(self, language: ExplanationLanguage):
        """
        Initialize i18n provider
        
        Args:
            language: Target language
        """
        self.language = language
        self._translations = self.TRANSLATIONS.get(
            language, 
            self.TRANSLATIONS[ExplanationLanguage.ENGLISH]
        )
    
    def get(self, key: str, default: Optional[str] = None) -> str:
        """
        Get translated string
        
        Args:
            key: Translation key
            default: Default value if key not found
            
        Returns:
            Translated string or default or key
        """
        return self._translations.get(key, default or key)
    
    def format(self, key: str, **kwargs) -> str:
        """
        Get translated string with formatting
        
        Args:
            key: Translation key
            **kwargs: Format arguments
            
        Returns:
            Formatted translated string
        """
        template = self.get(key)
        try:
            return template.format(**kwargs)
        except (KeyError, ValueError) as e:
            logger.warning(f"Failed to format translation '{key}': {e}")
            return template


class ExplanationGenerator:
    """
    Generate human-readable explanations for reasoning
    
    Supports:
    - Proof tree explanations
    - Forward chaining traces
    - Contradiction explanations
    - Multi-language output with proper i18n
    """
    
    def __init__(self, config: Optional[ExplanationConfig] = None):
        """
        Initialize explanation generator
        
        Args:
            config: Configuration for explanation style
        """
        self.config = config or ExplanationConfig()
        self.i18n = I18nProvider(self.config.language)
    
    def explain_proof(self, proof_tree: ProofNode) -> str:
        """
        Generate explanation from proof tree
        
        Args:
            proof_tree: Root of proof tree
        
        Returns:
            Human-readable explanation
        """
        if self.config.style == ExplanationStyle.CONCISE:
            return self._explain_concise(proof_tree)
        elif self.config.style == ExplanationStyle.DETAILED:
            return self._explain_detailed(proof_tree)
        elif self.config.style == ExplanationStyle.TECHNICAL:
            return self._explain_technical(proof_tree)
        else:  # NARRATIVE
            return self._explain_narrative(proof_tree)
    
    def _explain_concise(self, node: ProofNode) -> str:
        """Generate concise explanation"""
        if node.status == ProofStatus.SUCCESS:
            return f"✓ {self.i18n.get('proved')}: {node.goal}"
        else:
            return f"✗ {self.i18n.get('failed')}: {node.goal} ({node.status.value})"
    
    def _explain_detailed(self, node: ProofNode, indent: int = 0) -> str:
        """Generate detailed step-by-step explanation"""
        lines = []
        prefix = "  " * indent
        
        if node.status == ProofStatus.SUCCESS:
            if node.fact_matched:
                lines.append(f"{prefix}✓ {node.goal}")
                lines.append(f"{prefix}  → {self.i18n.get('known_fact')}")
            elif node.rule_used:
                lines.append(f"{prefix}✓ {node.goal}")
                if self.config.include_rules:
                    lines.append(f"{prefix}  → {self.i18n.get('using_rule')}: {node.rule_used}")
                
                if node.children:
                    lines.append(f"{prefix}  → {self.i18n.get('because')}:")
                    for child in node.children:
                        lines.append(self._explain_detailed(child, indent + 2))
            else:
                lines.append(f"{prefix}✓ {node.goal}")
        else:
            lines.append(f"{prefix}✗ {node.goal}")
            lines.append(f"{prefix}  → {self.i18n.get('failed')} ({node.status.value})")
        
        return "\n".join(lines)
    
    def _explain_technical(self, node: ProofNode, indent: int = 0) -> str:
        """Generate technical explanation with logical notation"""
        lines = []
        prefix = "  " * indent
        
        if node.status == ProofStatus.SUCCESS:
            if node.fact_matched:
                lines.append(f"{prefix}{node.goal} ← fact")
            elif node.rule_used:
                premises = " ∧ ".join(str(child.goal) for child in node.children)
                lines.append(f"{prefix}{node.goal} ← {premises}")
                
                for child in node.children:
                    lines.append(self._explain_technical(child, indent + 1))
        else:
            lines.append(f"{prefix}{node.goal} ← ⊥ ({node.status.value})")
        
        return "\n".join(lines)
    
    def _explain_narrative(self, node: ProofNode) -> str:
        """Generate narrative-style explanation"""
        if node.status != ProofStatus.SUCCESS:
            return f"{self.i18n.get('we_attempted')} {node.goal}, {self.i18n.get('failed').lower()}."
        
        if node.fact_matched:
            return f"{self.i18n.get('we_know_that')} {node.goal} {self.i18n.get('is_true')} {self.i18n.get('because')} {self.i18n.get('known_fact').lower()}."
        
        if node.rule_used:
            parts = []
            parts.append(f"{self.i18n.get('to_prove')} {node.goal}, {self.i18n.get('we_used_rule')}:")
            
            if node.children:
                conditions = [str(child.goal) for child in node.children]
                if len(conditions) == 1:
                    parts.append(f"{self.i18n.get('if')} {conditions[0]} {self.i18n.get('is_true')},")
                else:
                    cond_str = f", {self.i18n.get('and')} ".join(conditions)
                    parts.append(f"{self.i18n.get('if')} {cond_str} {self.i18n.get('are_all_true')},")
                
                parts.append(f"{self.i18n.get('then')} {node.goal} {self.i18n.get('must_be_true')}.")
                parts.append("")
                
                for i, child in enumerate(node.children, 1):
                    parts.append(f"{self.i18n.get('step')} {i}: {self._explain_narrative(child)}")
            
            parts.append(f"\n{self.i18n.get('therefore')}, {node.goal} {self.i18n.get('is_true')}.")
            return "\n".join(parts)
        
        return f"{node.goal} {self.i18n.get('is_true')}."
    
    def explain_forward_chaining(self, derived_facts: List[Fact], 
                                 rules_fired: List[tuple]) -> str:
        """
        Explain forward chaining derivation
        
        Args:
            derived_facts: Facts that were derived
            rules_fired: List of (rule, antecedents, conclusion) tuples
        
        Returns:
            Explanation string
        """
        lines = []
        
        lines.append("Forward Chaining Derivation:")
        lines.append("=" * 60)
        lines.append(f"Derived {len(derived_facts)} new facts:")
        lines.append("")
        
        for i, (rule, antecedents, conclusion) in enumerate(rules_fired, 1):
            lines.append(f"{self.i18n.get('step')} {i}:")
            lines.append(f"  {self.i18n.get('using_rule')}: {rule}")
            lines.append(f"  Given:")
            for ant in antecedents:
                lines.append(f"    - {ant}")
            lines.append(f"  {self.i18n.get('therefore')}: {conclusion}")
            lines.append("")
        
        return "\n".join(lines)
    
    def explain_contradiction(self, fact1: Fact, fact2: Fact, 
                            explanation1: str, explanation2: str) -> str:
        """
        Explain a contradiction between two facts
        
        Args:
            fact1: First contradictory fact
            fact2: Second contradictory fact
            explanation1: Explanation for fact1
            explanation2: Explanation for fact2
        
        Returns:
            Contradiction explanation
        """
        lines = []
        lines.append("⚠️  CONTRADICTION DETECTED")
        lines.append("=" * 60)
        lines.append(f"Fact 1: {fact1}")
        lines.append(f"Fact 2: {fact2}")
        lines.append("")
        lines.append("These facts contradict each other.")
        lines.append("")
        lines.append("Explanation for Fact 1:")
        lines.append(explanation1)
        lines.append("")
        lines.append("Explanation for Fact 2:")
        lines.append(explanation2)
        lines.append("")
        lines.append("Resolution required: Choose which fact to believe or revise assumptions.")
        
        return "\n".join(lines)
    
    def visualize_proof_tree(self, node: ProofNode) -> str:
        """
        Generate ASCII art visualization of proof tree
        
        Args:
            node: Root of proof tree
        
        Returns:
            ASCII art tree
        """
        return self._visualize_node(node, "", True)
    
    def _visualize_node(self, node: ProofNode, prefix: str, is_last: bool) -> str:
        """Recursive helper for tree visualization"""
        lines = []
        
        # Node symbol
        if node.status == ProofStatus.SUCCESS:
            symbol = "✓"
        else:
            symbol = "✗"
        
        # Current node
        connector = "└── " if is_last else "├── "
        lines.append(f"{prefix}{connector}{symbol} {node.goal}")
        
        # Children
        if node.children:
            extension = "    " if is_last else "│   "
            for i, child in enumerate(node.children):
                child_is_last = (i == len(node.children) - 1)
                lines.append(self._visualize_node(child, prefix + extension, child_is_last))
        
        return "\n".join(lines)

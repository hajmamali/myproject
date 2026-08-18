"""
MAHOUN Semantic Drift Classifier
================================

Classification Engine for API and Schema Drift Detection

Responsibility:
- Classify detected changes into semantic categories
- Distinguish cosmetic changes from behavioral changes
- Provide deterministic classification for CI/CD

Categories (for API):
- Cosmetic: Whitespace, formatting changes
- Documentation: Docstring, comment updates
- Typing: Type annotation changes only
- Refactor: Internal restructuring without API change
- Rename: Symbol renamed (same behavior)
- Module Relocation: Symbol moved to different module
- Public API Change: Signature modification
- Contract Change: Interface/abstract method change
- Behavioral Change: Logic modification
- Governance Change: Policy/rule modification
- Security Change: Security-related modification
- Kernel Boundary Change: Tier-0 modification

Categories (for Schema):
- Formatting: Whitespace, indentation
- Comments: Comment changes only
- Docstrings: Documentation string changes
- Typing: Type hint changes
- Structural: Schema structure modification
- Validation: Validation rule changes
- Contract: Contract term changes
- Behavioral: Logic/behavior changes

Requirements:
- Deterministic output
- Fail-closed behavior preserved
- No CI architecture changes
- No new guards introduced
"""

import ast
import difflib
import hashlib
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


# =============================================================================
# SEMANTIC DRIFT CATEGORIES
# =============================================================================

class APIDriftCategory(Enum):
    """Semantic categories for API changes."""
    COSMETIC = "Cosmetic"
    DOCUMENTATION = "Documentation"
    TYPING = "Typing"
    REFACTOR = "Refactor"
    RENAME = "Rename"
    MODULE_RELOCATION = "Module Relocation"
    PUBLIC_API_CHANGE = "Public API Change"
    CONTRACT_CHANGE = "Contract Change"
    BEHAVIORAL_CHANGE = "Behavioral Change"
    GOVERNANCE_CHANGE = "Governance Change"
    SECURITY_CHANGE = "Security Change"
    KERNEL_BOUNDARY_CHANGE = "Kernel Boundary Change"


class SchemaDriftCategory(Enum):
    """Semantic categories for schema changes."""
    FORMATTING = "Formatting"
    COMMENTS = "Comments"
    DOCSTRINGS = "Docstrings"
    TYPING = "Typing"
    STRUCTURAL = "Structural"
    VALIDATION = "Validation"
    CONTRACT = "Contract"
    BEHAVIORAL = "Behavioral"


# =============================================================================
# DRIFT SEVERITY LEVELS
# =============================================================================

class DriftSeverity(Enum):
    """Severity levels for classified drifts."""
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


# =============================================================================
# SEVERITY MAPPING
# =============================================================================

# API Drift Category -> Severity mapping
API_SEVERITY_MAP: Dict[APIDriftCategory, DriftSeverity] = {
    APIDriftCategory.COSMETIC: DriftSeverity.INFO,
    APIDriftCategory.DOCUMENTATION: DriftSeverity.LOW,
    APIDriftCategory.TYPING: DriftSeverity.LOW,
    APIDriftCategory.REFACTOR: DriftSeverity.LOW,
    APIDriftCategory.RENAME: DriftSeverity.MEDIUM,
    APIDriftCategory.MODULE_RELOCATION: DriftSeverity.MEDIUM,
    APIDriftCategory.PUBLIC_API_CHANGE: DriftSeverity.HIGH,
    APIDriftCategory.CONTRACT_CHANGE: DriftSeverity.HIGH,
    APIDriftCategory.BEHAVIORAL_CHANGE: DriftSeverity.CRITICAL,
    APIDriftCategory.GOVERNANCE_CHANGE: DriftSeverity.CRITICAL,
    APIDriftCategory.SECURITY_CHANGE: DriftSeverity.CRITICAL,
    APIDriftCategory.KERNEL_BOUNDARY_CHANGE: DriftSeverity.CRITICAL,
}

# Schema Drift Category -> Severity mapping
SCHEMA_SEVERITY_MAP: Dict[SchemaDriftCategory, DriftSeverity] = {
    SchemaDriftCategory.FORMATTING: DriftSeverity.INFO,
    SchemaDriftCategory.COMMENTS: DriftSeverity.INFO,
    SchemaDriftCategory.DOCSTRINGS: DriftSeverity.LOW,
    SchemaDriftCategory.TYPING: DriftSeverity.LOW,
    SchemaDriftCategory.STRUCTURAL: DriftSeverity.MEDIUM,
    SchemaDriftCategory.VALIDATION: DriftSeverity.HIGH,
    SchemaDriftCategory.CONTRACT: DriftSeverity.HIGH,
    SchemaDriftCategory.BEHAVIORAL: DriftSeverity.CRITICAL,
}


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class SemanticDriftClassification:
    """Complete classification of a detected drift."""
    category: APIDriftCategory | SchemaDriftCategory
    severity: DriftSeverity
    old_path: Optional[str] = None
    new_path: Optional[str] = None
    old_symbol: Optional[str] = None
    new_symbol: Optional[str] = None
    old_signature: Optional[str] = None
    new_signature: Optional[str] = None
    confidence: float = 1.0
    evidence: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "category": self.category.value,
            "severity": self.severity.value,
            "old_path": self.old_path,
            "new_path": self.new_path,
            "old_symbol": self.old_symbol,
            "new_symbol": self.new_symbol,
            "old_signature": self.old_signature,
            "new_signature": self.new_signature,
            "confidence": self.confidence,
            "evidence": self.evidence,
            "details": self.details,
        }


@dataclass 
class SemanticDriftReport:
    """Complete semantic drift report."""
    classifications: List[SemanticDriftClassification] = field(default_factory=list)
    summary: Dict[str, int] = field(default_factory=dict)
    critical_drifts: List[SemanticDriftClassification] = field(default_factory=list)
    non_critical_drifts: List[SemanticDriftClassification] = field(default_factory=list)
    
    def add_classification(self, classification: SemanticDriftClassification) -> None:
        """Add a classification to the report."""
        self.classifications.append(classification)
        
        # Update summary
        category_key = classification.category.value
        severity_key = classification.severity.value
        
        if category_key not in self.summary:
            self.summary[category_key] = 0
        self.summary[category_key] += 1
        
        # Categorize
        if classification.severity in [DriftSeverity.CRITICAL, DriftSeverity.HIGH]:
            self.critical_drifts.append(classification)
        else:
            self.non_critical_drifts.append(classification)


# =============================================================================
# API DRIFT CLASSIFIER
# =============================================================================

class APISemanticClassifier:
    """
    Classifier for API drift detection.
    
    Distinguishes between:
    - Removed
    - Renamed
    - Moved (to different module)
    - Aliased (deprecated with replacement)
    
    And classifies into semantic categories.
    """
    
    def __init__(self, name_similarity_threshold: float = 0.7, 
                 signature_similarity_threshold: float = 0.8):
        self.name_similarity_threshold = name_similarity_threshold
        self.signature_similarity_threshold = signature_similarity_threshold
        
    def classify_api_change(
        self,
        old_members: Dict[str, Any],
        new_members: Dict[str, Any],
        module_path: str,
        old_module_api: Optional[Dict[str, Any]] = None,
        new_module_api: Optional[Dict[str, Any]] = None
    ) -> List[SemanticDriftClassification]:
        """
        Classify API changes between two states.
        
        Args:
            old_members: Dict of old API members {name: {type, signature, ...}}
            new_members: Dict of new API members {name: {type, signature, ...}}
            module_path: The module path being compared
            old_module_api: Full old module API data
            new_module_api: Full new module API data
            
        Returns:
            List of classified drifts
        """
        classifications: List[SemanticDriftClassification] = []
        
        old_names = set(old_members.keys())
        new_names = set(new_members.keys())
        
        removed = old_names - new_names
        added = new_names - old_names
        common = old_names & new_names
        
        # Classify removed symbols
        for name in removed:
            classification = self._classify_removed(name, old_members[name], 
                                                   added, new_members, module_path)
            if classification:
                classifications.append(classification)
        
        # Classify added symbols
        for name in added:
            # Skip if already matched as a rename
            if not any(c.new_symbol == name for c in classifications):
                classification = self._classify_added(name, new_members[name], 
                                                       module_path)
                if classification:
                    classifications.append(classification)
        
        # Classify changed symbols
        for name in common:
            old_data = old_members[name]
            new_data = new_members[name]
            classification = self._classify_changed(name, old_data, new_data, module_path)
            if classification:
                classifications.append(classification)
        
        return classifications
    
    def _classify_removed(
        self,
        name: str,
        old_data: Dict[str, Any],
        added_names: Set[str],
        new_members: Dict[str, Any],
        module_path: str
    ) -> Optional[SemanticDriftClassification]:
        """Classify a removed symbol."""
        # Check if this is a rename
        for new_name in added_names:
            new_data = new_members[new_name]
            similarity = self._calculate_name_similarity(name, new_name)
            
            # Check signature similarity if available
            old_sig = old_data.get("signature", "")
            new_sig = new_data.get("signature", "")
            sig_similarity = self._calculate_signature_similarity(old_sig, new_sig)
            
            # If name and signature are similar, it's a rename
            if (similarity >= self.name_similarity_threshold and 
                sig_similarity >= self.signature_similarity_threshold):
                
                # It's a rename
                return SemanticDriftClassification(
                    category=APIDriftCategory.RENAME,
                    severity=API_SEVERITY_MAP[APIDriftCategory.RENAME],
                    old_path=module_path,
                    new_path=module_path,
                    old_symbol=name,
                    new_symbol=new_name,
                    old_signature=old_sig,
                    new_signature=new_sig,
                    confidence=min(similarity, sig_similarity),
                    evidence=[
                        f"Name similarity: {similarity:.2%}",
                        f"Signature similarity: {sig_similarity:.2%}",
                        f"Old: {name}{'(' + old_sig + ')' if old_sig else ''}",
                        f"New: {new_name}{'(' + new_sig + ')' if new_sig else ''}"
                    ],
                    details={"type": old_data.get("type")}
                )
        
        # Check if there's an alias (deprecated symbol pointing to new one)
        # This would require inspecting the code for deprecation warnings
        # For now, treat as removal
        
        # Classify based on symbol characteristics
        symbol_type = old_data.get("type", "")
        
        # Check if it's a governance-related symbol
        if self._is_governance_symbol(name, old_data):
            category = APIDriftCategory.GOVERNANCE_CHANGE
        elif self._is_security_symbol(name, old_data):
            category = APIDriftCategory.SECURITY_CHANGE
        else:
            # Default: assume it's a removal (but could be moved)
            category = APIDriftCategory.PUBLIC_API_CHANGE
        
        return SemanticDriftClassification(
            category=category,
            severity=API_SEVERITY_MAP[category],
            old_path=module_path,
            old_symbol=name,
            old_signature=old_data.get("signature"),
            confidence=1.0,
            evidence=[f"Symbol {name} removed from {module_path}"],
            details={"type": symbol_type}
        )
    
    def _classify_added(
        self,
        name: str,
        new_data: Dict[str, Any],
        module_path: str
    ) -> Optional[SemanticDriftClassification]:
        """Classify an added symbol."""
        symbol_type = new_data.get("type", "")
        signature = new_data.get("signature", "")
        
        # Check if it's documentation-only (unlikely for added symbol)
        # Check if it's typing
        if symbol_type == "variable" and self._is_typing_related(name):
            return SemanticDriftClassification(
                category=APIDriftCategory.TYPING,
                severity=API_SEVERITY_MAP[APIDriftCategory.TYPING],
                new_path=module_path,
                new_symbol=name,
                new_signature=signature,
                confidence=1.0,
                evidence=[f"Type-related symbol added: {name}"],
                details={"type": symbol_type}
            )
        
        # Check if it's governance-related
        if self._is_governance_symbol(name, new_data):
            category = APIDriftCategory.GOVERNANCE_CHANGE
        elif self._is_security_symbol(name, new_data):
            category = APIDriftCategory.SECURITY_CHANGE
        else:
            category = APIDriftCategory.PUBLIC_API_CHANGE
        
        return SemanticDriftClassification(
            category=category,
            severity=API_SEVERITY_MAP[category],
            new_path=module_path,
            new_symbol=name,
            new_signature=signature,
            confidence=1.0,
            evidence=[f"Symbol {name} added to {module_path}"],
            details={"type": symbol_type}
        )
    
    def _classify_changed(
        self,
        name: str,
        old_data: Dict[str, Any],
        new_data: Dict[str, Any],
        module_path: str
    ) -> Optional[SemanticDriftClassification]:
        """Classify a changed symbol."""
        old_sig = old_data.get("signature", "")
        new_sig = new_data.get("signature", "")
        old_type = old_data.get("type", "")
        new_type = new_data.get("type", "")
        
        # If only documentation changed
        if old_sig == new_sig and old_type == new_type:
            return SemanticDriftClassification(
                category=APIDriftCategory.DOCUMENTATION,
                severity=API_SEVERITY_MAP[APIDriftCategory.DOCUMENTATION],
                old_path=module_path,
                old_symbol=name,
                new_symbol=name,
                old_signature=old_sig,
                new_signature=new_sig,
                confidence=1.0,
                evidence=[f"Only metadata/docstring changed for {name}"],
                details={"type": old_type}
            )
        
        # If only type annotations changed
        if self._is_typing_only_change(old_sig, new_sig):
            return SemanticDriftClassification(
                category=APIDriftCategory.TYPING,
                severity=API_SEVERITY_MAP[APIDriftCategory.TYPING],
                old_path=module_path,
                old_symbol=name,
                new_symbol=name,
                old_signature=old_sig,
                new_signature=new_sig,
                confidence=0.95,
                evidence=[
                    f"Type annotation change detected",
                    f"Old: {old_sig}",
                    f"New: {new_sig}"
                ],
                details={"type": old_type}
            )
        
        # If signature changed
        if old_sig != new_sig:
            # Check if it's a contract change (abstract method, interface)
            if self._is_contract_symbol(name, old_data):
                category = APIDriftCategory.CONTRACT_CHANGE
            elif self._is_governance_symbol(name, old_data):
                category = APIDriftCategory.GOVERNANCE_CHANGE
            else:
                category = APIDriftCategory.PUBLIC_API_CHANGE
            
            return SemanticDriftClassification(
                category=category,
                severity=API_SEVERITY_MAP[category],
                old_path=module_path,
                old_symbol=name,
                new_symbol=name,
                old_signature=old_sig,
                new_signature=new_sig,
                confidence=1.0,
                evidence=[
                    f"Signature changed for {name}",
                    f"Old: {old_sig}",
                    f"New: {new_sig}"
                ],
                details={"type": old_type}
            )
        
        # If type changed (class -> method, etc.)
        if old_type != new_type:
            return SemanticDriftClassification(
                category=APIDriftCategory.REFACTOR,
                severity=API_SEVERITY_MAP[APIDriftCategory.REFACTOR],
                old_path=module_path,
                old_symbol=name,
                new_symbol=name,
                old_signature=old_sig,
                new_signature=new_sig,
                confidence=1.0,
                evidence=[
                    f"Symbol type changed from {old_type} to {new_type}",
                    f"Symbol: {name}"
                ],
                details={"old_type": old_type, "new_type": new_type}
            )
        
        # If we get here, something changed but we couldn't classify
        # This shouldn't happen if signature and type are the same
        return None
    
    def classify_missing_vs_renamed_vs_moved(
        self,
        expected_symbols: Set[str],
        current_symbols: Set[str],
        old_api_data: Dict[str, Dict[str, Any]],
        new_api_data: Dict[str, Dict[str, Any]],
        all_modules: List[str]
    ) -> Dict[str, List[SemanticDriftClassification]]:
        """
        Advanced classification: distinguish between removed, renamed, moved, aliased.
        
        This performs cross-module analysis to detect:
        - Removed: Symbol no longer exists anywhere
        - Renamed: Symbol exists with different name in same module
        - Moved: Symbol exists with same name in different module
        - Aliased: Symbol deprecated with replacement
        
        Returns dict with keys: 'removed', 'renamed', 'moved', 'aliased'
        """
        removed = []
        renamed = []
        moved = []
        aliased = []
        
        # Build symbol -> module mapping for current state
        current_symbol_map: Dict[str, List[Tuple[str, Dict[str, Any]]]] = {}
        for module in all_modules:
            if module in new_api_data:
                for symbol, data in new_api_data[module].get("members", {}).items():
                    if symbol not in current_symbol_map:
                        current_symbol_map[symbol] = []
                    current_symbol_map[symbol].append((module, data))
        
        # Build symbol -> module mapping for expected state
        expected_symbol_map: Dict[str, List[Tuple[str, Dict[str, Any]]]] = {}
        for module in all_modules:
            if module in old_api_data:
                for symbol, data in old_api_data[module].get("members", {}).items():
                    if symbol not in expected_symbol_map:
                        expected_symbol_map[symbol] = []
                    expected_symbol_map[symbol].append((module, data))
        
        # Check each expected symbol
        for symbol in expected_symbols:
            if symbol in current_symbol_map:
                # Symbol exists - check if in same module
                expected_modules = [m for m, _ in expected_symbol_map.get(symbol, [])]
                current_modules = [m for m, _ in current_symbol_map[symbol]]
                
                # If in different module, it's moved
                if set(expected_modules) != set(current_modules):
                    for exp_module in expected_modules:
                        for curr_module in current_modules:
                            if exp_module != curr_module:
                                # Find the data
                                exp_data = None
                                for m, d in expected_symbol_map[symbol]:
                                    if m == exp_module:
                                        exp_data = d
                                        break
                                curr_data = None
                                for m, d in current_symbol_map[symbol]:
                                    if m == curr_module:
                                        curr_data = d
                                        break
                                
                                moved.append(SemanticDriftClassification(
                                    category=APIDriftCategory.MODULE_RELOCATION,
                                    severity=API_SEVERITY_MAP[APIDriftCategory.MODULE_RELOCATION],
                                    old_path=exp_module,
                                    new_path=curr_module,
                                    old_symbol=symbol,
                                    new_symbol=symbol,
                                    old_signature=exp_data.get("signature") if exp_data else None,
                                    new_signature=curr_data.get("signature") if curr_data else None,
                                    confidence=1.0,
                                    evidence=[
                                        f"Symbol {symbol} moved from {exp_module} to {curr_module}"
                                    ],
                                    details={"type": exp_data.get("type") if exp_data else ""}
                                ))
            else:
                # Symbol doesn't exist - check if renamed
                found_rename = False
                for new_symbol in current_symbols:
                    similarity = self._calculate_name_similarity(symbol, new_symbol)
                    
                    # Get data for comparison
                    exp_data = None
                    for m, symbols in old_api_data.items():
                        if symbol in symbols.get("members", {}):
                            exp_data = symbols["members"][symbol]
                            break
                    
                    new_data = None
                    for m, symbols in new_api_data.items():
                        if new_symbol in symbols.get("members", {}):
                            new_data = symbols["members"][new_symbol]
                            break
                    
                    if exp_data and new_data:
                        old_sig = exp_data.get("signature", "")
                        new_sig = new_data.get("signature", "")
                        sig_similarity = self._calculate_signature_similarity(old_sig, new_sig)
                        
                        if (similarity >= self.name_similarity_threshold and 
                            sig_similarity >= self.signature_similarity_threshold):
                            
                            # Found a rename
                            renamed.append(SemanticDriftClassification(
                                category=APIDriftCategory.RENAME,
                                severity=API_SEVERITY_MAP[APIDriftCategory.RENAME],
                                old_path=exp_data.get("module", ""),
                                new_path=new_data.get("module", ""),
                                old_symbol=symbol,
                                new_symbol=new_symbol,
                                old_signature=old_sig,
                                new_signature=new_sig,
                                confidence=min(similarity, sig_similarity),
                                evidence=[
                                    f"Name similarity: {similarity:.2%}",
                                    f"Signature similarity: {sig_similarity:.2%}",
                                    f"Old: {symbol}",
                                    f"New: {new_symbol}"
                                ],
                                details={"type": exp_data.get("type")}
                            ))
                            found_rename = True
                            break
                
                if not found_rename:
                    # Check if aliased (would need deprecation detection)
                    # For now, treat as removed
                    # Find which module it was in
                    for module in all_modules:
                        if module in old_api_data:
                            if symbol in old_api_data[module].get("members", {}):
                                removed.append(SemanticDriftClassification(
                                    category=APIDriftCategory.PUBLIC_API_CHANGE,
                                    severity=API_SEVERITY_MAP[APIDriftCategory.PUBLIC_API_CHANGE],
                                    old_path=module,
                                    old_symbol=symbol,
                                    old_signature=old_api_data[module]["members"][symbol].get("signature"),
                                    confidence=1.0,
                                    evidence=[f"Symbol {symbol} removed (no matching rename found)"],
                                    details={"type": old_api_data[module]["members"][symbol].get("type")}
                                ))
                                break
        
        return {
            "removed": removed,
            "renamed": renamed,
            "moved": moved,
            "aliased": aliased
        }
    
    def _calculate_name_similarity(self, name1: str, name2: str) -> float:
        """Calculate similarity between two names."""
        return difflib.SequenceMatcher(None, name1, name2).ratio()
    
    def _calculate_signature_similarity(self, sig1: str, sig2: str) -> float:
        """Calculate similarity between two signatures."""
        # Normalize signatures
        norm1 = self._normalize_signature(sig1)
        norm2 = self._normalize_signature(sig2)
        return difflib.SequenceMatcher(None, norm1, norm2).ratio()
    
    def _normalize_signature(self, signature: str) -> str:
        """Normalize signature for comparison."""
        # Remove spaces, standardize
        return re.sub(r'\s+', ' ', signature).strip()
    
    def _is_typing_only_change(self, old_sig: str, new_sig: str) -> bool:
        """Check if change is only in type annotations."""
        # Simple heuristic: if the parameter names are the same
        # but types are different
        old_params = self._extract_parameters(old_sig)
        new_params = self._extract_parameters(new_sig)
        
        if len(old_params) != len(new_params):
            return False
        
        # Check if parameter names match
        for (old_name, _), (new_name, _) in zip(old_params, new_params):
            if old_name != new_name:
                return False
        
        # Check if types are different
        type_diff = False
        for (_, old_type), (_, new_type) in zip(old_params, new_params):
            if old_type != new_type:
                type_diff = True
                break
        
        return type_diff
    
    def _extract_parameters(self, signature: str) -> List[Tuple[str, str]]:
        """Extract parameter names and types from signature."""
        params = []
        if not signature:
            return params
        
        # Simple parsing (for display purposes)
        # Match patterns like: (param1: Type1, param2: Type2) -> ReturnType
        match = re.match(r'\((.*?)\)', signature)
        if match:
            params_str = match.group(1)
            for param in params_str.split(','):
                param = param.strip()
                if ':' in param:
                    name, type_ = param.split(':', 1)
                    params.append((name.strip(), type_.strip()))
                elif param:
                    params.append((param, ''))
        
        return params
    
    def _is_governance_symbol(self, name: str, data: Dict[str, Any]) -> bool:
        """Check if symbol is governance-related."""
        governance_keywords = [
            'governance', 'violation', 'policy', 'enforce', 'authorize',
            'kernel', 'boundary', 'lock', 'mutation', 'guard'
        ]
        name_lower = name.lower()
        for kw in governance_keywords:
            if kw in name_lower:
                return True
        return False
    
    def _is_security_symbol(self, name: str, data: Dict[str, Any]) -> bool:
        """Check if symbol is security-related."""
        security_keywords = ['security', 'auth', 'permission', 'token', 'safe']
        name_lower = name.lower()
        for kw in security_keywords:
            if kw in name_lower:
                return True
        return False
    
    def _is_contract_symbol(self, name: str, data: Dict[str, Any]) -> bool:
        """Check if symbol is a contract (abstract/interface)."""
        symbol_type = data.get("type", "")
        # Check if it's in a contracts module
        module = data.get("module", "")
        return 'contract' in module.lower() or symbol_type == 'abstract'


# =============================================================================
# SCHEMA DRIFT CLASSIFIER
# =============================================================================

class SchemaSemanticClassifier:
    """
    Classifier for schema drift detection.
    
    Distinguishes between:
    - Formatting (whitespace, indentation)
    - Comments (comment changes only)
    - Docstrings (docstring changes only)
    - Typing (type hint changes)
    - Structural (schema structure changes)
    - Validation (validation rule changes)
    - Contract (contract term changes)
    - Behavioral (logic/behavior changes)
    """
    
    def __init__(self):
        self.comment_pattern = re.compile(r'^\s*#.*$', re.MULTILINE)
        self.docstring_pattern = re.compile(r'^\s*["\']{3}.*["\']{3}$', re.MULTILINE | re.DOTALL)
        self.typing_pattern = re.compile(r':\s*[A-Z]\w*', re.MULTILINE)
    
    def classify_schema_change(
        self,
        file_path: str,
        old_content: str,
        new_content: str
    ) -> SemanticDriftClassification:
        """
        Classify a schema file change into semantic categories.
        
        Args:
            file_path: Path to the schema file
            old_content: Old file content
            new_content: New file content
            
        Returns:
            Classification of the change
        """
        # Calculate hash difference
        old_hash = hashlib.sha256(old_content.encode()).hexdigest()
        new_hash = hashlib.sha256(new_content.encode()).hexdigest()
        
        if old_hash == new_hash:
            # No change
            return SemanticDriftClassification(
                category=SchemaDriftCategory.FORMATTING,
                severity=DriftSeverity.INFO,
                old_path=file_path,
                confidence=1.0,
                evidence=["Hash unchanged - no drift detected"],
                details={}
            )
        
        # Extract AST from both
        try:
            old_tree = ast.parse(old_content, filename=file_path)
        except SyntaxError:
            old_tree = None
        
        try:
            new_tree = ast.parse(new_content, filename=file_path)
        except SyntaxError:
            new_tree = None
        
        # If we can parse both, do AST comparison
        if old_tree and new_tree:
            return self._classify_ast_change(file_path, old_tree, new_tree, old_content, new_content)
        
        # Fall back to text comparison
        return self._classify_text_change(file_path, old_content, new_content)
    
    def _classify_ast_change(
        self,
        file_path: str,
        old_tree: ast.AST,
        new_tree: ast.AST,
        old_content: str,
        new_content: str
    ) -> SemanticDriftClassification:
        """Classify change using AST comparison."""
        # Compare structure
        structural_changes = self._compare_ast_structure(old_tree, new_tree)
        
        if not structural_changes:
            # No structural changes - might be comments/docstrings
            if self._only_comments_changed(old_content, new_content):
                return SemanticDriftClassification(
                    category=SchemaDriftCategory.COMMENTS,
                    severity=SCHEMA_SEVERITY_MAP[SchemaDriftCategory.COMMENTS],
                    old_path=file_path,
                    confidence=0.95,
                    evidence=["Only comments changed"],
                    details={"changes": "comments only"}
                )
            
            if self._only_docstrings_changed(old_content, new_content):
                return SemanticDriftClassification(
                    category=SchemaDriftCategory.DOCSTRINGS,
                    severity=SCHEMA_SEVERITY_MAP[SchemaDriftCategory.DOCSTRINGS],
                    old_path=file_path,
                    confidence=0.95,
                    evidence=["Only docstrings changed"],
                    details={"changes": "docstrings only"}
                )
            
            # Check for typing changes
            if self._only_typing_changed(old_content, new_content):
                return SemanticDriftClassification(
                    category=SchemaDriftCategory.TYPING,
                    severity=SCHEMA_SEVERITY_MAP[SchemaDriftCategory.TYPING],
                    old_path=file_path,
                    confidence=0.9,
                    evidence=["Only type annotations changed"],
                    details={"changes": "typing only"}
                )
            
            # Check for formatting
            if self._only_formatting_changed(old_content, new_content):
                return SemanticDriftClassification(
                    category=SchemaDriftCategory.FORMATTING,
                    severity=SCHEMA_SEVERITY_MAP[SchemaDriftCategory.FORMATTING],
                    old_path=file_path,
                    confidence=0.9,
                    evidence=["Only formatting/whitespace changed"],
                    details={"changes": "formatting only"}
                )
        
        # Structural changes detected
        # Classify based on what changed
        if self._is_validation_change(old_tree, new_tree):
            return SemanticDriftClassification(
                category=SchemaDriftCategory.VALIDATION,
                severity=SCHEMA_SEVERITY_MAP[SchemaDriftCategory.VALIDATION],
                old_path=file_path,
                confidence=0.9,
                evidence=["Validation rules modified"],
                details={"structural_changes": structural_changes}
            )
        
        if self._is_contract_change(file_path):
            return SemanticDriftClassification(
                category=SchemaDriftCategory.CONTRACT,
                severity=SCHEMA_SEVERITY_MAP[SchemaDriftCategory.CONTRACT],
                old_path=file_path,
                confidence=0.95,
                evidence=["Contract terms modified"],
                details={"structural_changes": structural_changes}
            )
        
        # Default to structural change
        return SemanticDriftClassification(
            category=SchemaDriftCategory.STRUCTURAL,
            severity=SCHEMA_SEVERITY_MAP[SchemaDriftCategory.STRUCTURAL],
            old_path=file_path,
            confidence=0.8,
            evidence=[f"{len(structural_changes)} structural changes detected"],
            details={"structural_changes": structural_changes}
        )
    
    def _classify_text_change(
        self,
        file_path: str,
        old_content: str,
        new_content: str
    ) -> SemanticDriftClassification:
        """Classify change using text comparison (fallback)."""
        # Check for common patterns
        if self._only_comments_changed(old_content, new_content):
            return SemanticDriftClassification(
                category=SchemaDriftCategory.COMMENTS,
                severity=SCHEMA_SEVERITY_MAP[SchemaDriftCategory.COMMENTS],
                old_path=file_path,
                confidence=0.85,
                evidence=["Text analysis: Only comments changed"],
                details={}
            )
        
        if self._only_docstrings_changed(old_content, new_content):
            return SemanticDriftClassification(
                category=SchemaDriftCategory.DOCSTRINGS,
                severity=SCHEMA_SEVERITY_MAP[SchemaDriftCategory.DOCSTRINGS],
                old_path=file_path,
                confidence=0.85,
                evidence=["Text analysis: Only docstrings changed"],
                details={}
            )
        
        if self._only_formatting_changed(old_content, new_content):
            return SemanticDriftClassification(
                category=SchemaDriftCategory.FORMATTING,
                severity=SCHEMA_SEVERITY_MAP[SchemaDriftCategory.FORMATTING],
                old_path=file_path,
                confidence=0.8,
                evidence=["Text analysis: Only formatting changed"],
                details={}
            )
        
        # If file is a contract, assume contract change
        if self._is_contract_change(file_path):
            return SemanticDriftClassification(
                category=SchemaDriftCategory.CONTRACT,
                severity=SCHEMA_SEVERITY_MAP[SchemaDriftCategory.CONTRACT],
                old_path=file_path,
                confidence=0.7,
                evidence=["Contract file modified - text analysis fallback"],
                details={}
            )
        
        # Default to behavioral (conservative)
        return SemanticDriftClassification(
            category=SchemaDriftCategory.BEHAVIORAL,
            severity=SCHEMA_SEVERITY_MAP[SchemaDriftCategory.BEHAVIORAL],
            old_path=file_path,
            confidence=0.5,
            evidence=["Unable to classify - defaulting to Behavioral"],
            details={}
        )
    
    def _compare_ast_structure(self, old_tree: ast.AST, new_tree: ast.AST) -> List[str]:
        """Compare AST structure and return list of changes."""
        changes = []
        
        # Simple comparison: count nodes
        old_classes = [n for n in ast.walk(old_tree) if isinstance(n, ast.ClassDef)]
        new_classes = [n for n in ast.walk(new_tree) if isinstance(n, ast.ClassDef)]
        
        if len(old_classes) != len(new_classes):
            changes.append(f"Class count: {len(old_classes)} -> {len(new_classes)}")
        
        old_functions = [n for n in ast.walk(old_tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
        new_functions = [n for n in ast.walk(new_tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
        
        if len(old_functions) != len(new_functions):
            changes.append(f"Function count: {len(old_functions)} -> {len(new_functions)}")
        
        return changes
    
    def _only_comments_changed(self, old: str, new: str) -> bool:
        """Check if only comments changed."""
        # Remove all comments and compare
        old_no_comments = self.comment_pattern.sub('', old)
        new_no_comments = self.comment_pattern.sub('', new)
        return old_no_comments.strip() == new_no_comments.strip()
    
    def _only_docstrings_changed(self, old: str, new: str) -> bool:
        """Check if only docstrings changed."""
        # This is more complex - need to remove docstrings from AST
        # For now, use a simple heuristic
        old_lines = old.split('\n')
        new_lines = new.split('\n')
        
        # Count non-docstring lines
        old_code_lines = [l for l in old_lines if not (l.strip().startswith('"""') or l.strip().startswith("'''"))]
        new_code_lines = [l for l in new_lines if not (l.strip().startswith('"""') or l.strip().startswith("'''"))]
        
        return old_code_lines == new_code_lines
    
    def _only_formatting_changed(self, old: str, new: str) -> bool:
        """Check if only formatting changed."""
        # Remove all whitespace and compare
        old_normalized = re.sub(r'\s+', '', old)
        new_normalized = re.sub(r'\s+', '', new)
        return old_normalized == new_normalized
    
    def _only_typing_changed(self, old: str, new: str) -> bool:
        """Check if only type annotations changed."""
        # Remove type annotations and compare
        old_no_types = self.typing_pattern.sub('', old)
        new_no_types = self.typing_pattern.sub('', new)
        return old_no_types.strip() == new_no_types.strip()
    
    def _is_validation_change(self, old_tree: ast.AST, new_tree: ast.AST) -> bool:
        """Check if validation rules changed."""
        # Look for validation-related patterns
        old_code = ast.unparse(old_tree) if hasattr(ast, 'unparse') else str(old_tree)
        new_code = ast.unparse(new_tree) if hasattr(ast, 'unparse') else str(new_tree)
        
        validation_keywords = ['validate', 'check', 'enforce', 'require', 'must', 'should']
        
        old_has_validation = any(kw in old_code.lower() for kw in validation_keywords)
        new_has_validation = any(kw in new_code.lower() for kw in validation_keywords)
        
        return old_has_validation and new_has_validation
    
    def _is_contract_change(self, file_path: str) -> bool:
        """Check if file is a contract."""
        contract_patterns = ['contract', 'schema', 'protocol']
        return any(pattern in file_path.lower() for pattern in contract_patterns)


# =============================================================================
# FACTORY FUNCTIONS
# =============================================================================

def get_api_classifier(
    name_similarity_threshold: float = 0.7,
    signature_similarity_threshold: float = 0.8
) -> APISemanticClassifier:
    """Factory function to create API classifier."""
    return APISemanticClassifier(
        name_similarity_threshold=name_similarity_threshold,
        signature_similarity_threshold=signature_similarity_threshold
    )


def get_schema_classifier() -> SchemaSemanticClassifier:
    """Factory function to create Schema classifier."""
    return SchemaSemanticClassifier()

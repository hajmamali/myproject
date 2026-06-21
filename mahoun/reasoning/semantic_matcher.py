"""
Semantic Matching for Contradiction Detection
==============================================

Provides deterministic semantic matching using:
- Synonym normalization
- Antonym detection
- Canonical form mapping
- Context-aware matching

Guarantees:
- Deterministic (no LLM randomness)
- Auditable (dictionary-based)
- Zero-hallucination (no invented synonyms)
- Persian language support
"""

import logging

log = logging.getLogger(__name__)


class SemanticMatcher:
    """
    Semantic matcher with synonym/antonym support

    Features:
    - Synonym normalization (قرارداد = عقد = پیمان)
    - Antonym detection (مجاز ≠ ممنوع)
    - Canonical form mapping
    - Deterministic matching

    Use cases:
    - Contradiction detection
    - Semantic similarity
    - Text normalization
    """

    def __init__(self):
        """Initialize semantic matcher"""
        import importlib

        data_augmentation = importlib.import_module("mahoun.finetuning.data_augmentation")
        self.synonym_dict = data_augmentation.PersianLegalSynonymDict()
        self.antonym_dict = self._build_antonym_dict()
        self.negation_words = self._build_negation_list()

        log.debug(
            f"Semantic matcher initialized: "
            f"{len(self.synonym_dict.synonyms)} synonym groups, "
            f"{len(self.antonym_dict)} antonym groups"
        )

    def _build_antonym_dict(self) -> dict[str, list[str]]:
        """
        Build antonym dictionary

        Returns:
            Dictionary mapping words to their antonyms

        Note:
            Bidirectional: if A is antonym of B, then B is antonym of A
        """
        antonyms = {
            # Legal permissions
            "مجاز": ["ممنوع", "غیرمجاز", "غیرقانونی", "نامشروع"],
            "جایز": ["ممنوع", "غیرمجاز", "نامشروع"],
            "قانونی": ["غیرقانونی", "نامشروع", "ممنوع"],
            # Validity
            "معتبر": ["باطل", "بی‌اعتبار", "نامعتبر", "فاسد"],
            "صحیح": ["نادرست", "غلط", "باطل", "فاسد"],
            "درست": ["نادرست", "غلط", "اشتباه"],
            # Obligations
            "لازم": ["غیرلازم", "اختیاری", "غیرضروری"],
            "واجب": ["غیرواجب", "اختیاری"],
            "الزامی": ["اختیاری", "غیرالزامی"],
            # Actions
            "فسخ": ["تایید", "تثبیت", "ابقا"],
            "ابطال": ["تایید", "تثبیت", "اعتبار"],
            "لغو": ["تایید", "تثبیت", "ابقا"],
            # Rights
            "حق": ["تکلیف", "وظیفه"],
            "اختیار": ["تکلیف", "الزام"],
        }

        # Make bidirectional
        bidirectional = {}
        for word, antonym_list in antonyms.items():
            bidirectional[word] = antonym_list
            for antonym in antonym_list:
                if antonym not in bidirectional:
                    bidirectional[antonym] = []
                if word not in bidirectional[antonym]:
                    bidirectional[antonym].append(word)

        return bidirectional

    def _build_negation_list(self) -> list[str]:
        """
        Build comprehensive negation word list

        Returns:
            List of negation words
        """
        return [
            # Basic negations
            "نه",
            "نی",
            "نیست",
            "نیستند",
            # Verb negations
            "ندارد",
            "ندارند",
            "نداشت",
            "نداشتند",
            "نباید",
            "نبایست",
            "نباشد",
            "نباشند",
            "نمی‌شود",
            "نمی‌توان",
            "نمی‌تواند",
            "نکرد",
            "نکرده",
            "نکند",
            "نکنند",
            # Adjective negations
            "غیر",
            "بی",
            "نا",
            "بدون",
            # Explicit prohibitions
            "ممنوع",
            "منع",
            "ممنوعیت",
            "غیرمجاز",
            "غیرقانونی",
            "نامشروع",
        ]

    def normalize_text(self, text: str) -> str:
        """
        Normalize text using synonyms

        Args:
            text: Text to normalize

        Returns:
            Normalized text with canonical forms

        Example:
            "عقد فسخ شد" → "قرارداد فسخ شد"
        """
        if not text:
            return ""

        words = text.split()
        normalized = []

        for word in words:
            # Find canonical form
            canonical = self._get_canonical_form(word)
            normalized.append(canonical)

        return " ".join(normalized)

    def _get_canonical_form(self, word: str) -> str:
        """
        Get canonical form of word

        Args:
            word: Word to canonicalize

        Returns:
            Canonical form (or original if not in dictionary)

        Logic:
            If word is in synonym dict (as key), return key
            If word is in any synonym list (as value), return that key
        """
        # Check if word is already canonical (key)
        if word in self.synonym_dict.synonyms:
            return word

        # Check if word is a synonym (value) - find its canonical form
        for canonical, synonyms in self.synonym_dict.synonyms.items():
            if word in synonyms:
                return canonical

        # Not in dictionary, return as-is
        return word

    def are_synonyms(self, word1: str, word2: str) -> bool:
        """
        Check if two words are synonyms

        Args:
            word1: First word
            word2: Second word

        Returns:
            True if words are synonyms, False otherwise
        """
        # Empty strings are not synonyms
        if not word1 or not word2:
            return False

        # Same word
        if word1 == word2:
            return True

        # Check if both map to same canonical form
        canonical1 = self._get_canonical_form(word1)
        canonical2 = self._get_canonical_form(word2)

        return canonical1 == canonical2

    def are_antonyms(self, word1: str, word2: str) -> bool:
        """
        Check if two words are antonyms

        Args:
            word1: First word
            word2: Second word

        Returns:
            True if words are antonyms, False otherwise
        """
        # Check direct antonym relationship
        if word1 in self.antonym_dict:
            if word2 in self.antonym_dict[word1]:
                return True

        # Check with canonical forms
        canonical1 = self._get_canonical_form(word1)
        canonical2 = self._get_canonical_form(word2)

        if canonical1 in self.antonym_dict:
            if canonical2 in self.antonym_dict[canonical1]:
                return True

        return False

    def contains_negation(self, text: str) -> bool:
        """
        Check if text contains negation

        Args:
            text: Text to check

        Returns:
            True if negation found, False otherwise
        """
        text_lower = text.lower()
        return any(neg in text_lower for neg in self.negation_words)

    def are_semantically_equivalent(self, text1: str, text2: str, threshold: float = 0.75) -> bool:
        """
        Check if two texts are semantically equivalent

        Args:
            text1: First text
            text2: Second text
            threshold: Similarity threshold for equivalence (default: 0.75)

        Returns:
            True if texts are semantically equivalent, False otherwise

        Logic:
            Texts are equivalent if semantic similarity exceeds threshold
            Uses normalized Jaccard similarity on canonical forms
        """
        similarity = self.semantic_similarity(text1, text2)
        return similarity >= threshold

    def are_contradictory(self, text1: str, text2: str) -> bool:
        """
        Check if two texts are contradictory

        Args:
            text1: First text
            text2: Second text

        Returns:
            True if texts contradict, False otherwise

        Logic:
            Texts contradict if:
            1. They contain antonyms, OR
            2. One has negation and other doesn't (for same concept)
        """
        # Normalize texts
        norm1 = self.normalize_text(text1.lower())
        norm2 = self.normalize_text(text2.lower())

        # Extract words
        words1 = set(norm1.split())
        words2 = set(norm2.split())

        # Check for antonyms
        for word1 in words1:
            for word2 in words2:
                if self.are_antonyms(word1, word2):
                    log.debug(f"Contradiction detected: '{word1}' ≠ '{word2}'")
                    return True

        # Check for negation pattern
        has_negation1 = self.contains_negation(text1)
        has_negation2 = self.contains_negation(text2)

        if has_negation1 != has_negation2:
            # One has negation, other doesn't
            # Check if they share common concepts
            common_words = words1 & words2
            if len(common_words) > 0:
                log.debug(f"Contradiction detected: negation mismatch on common concepts {common_words}")
                return True

        return False

    def semantic_similarity(self, text1: str, text2: str) -> float:
        """
        Compute semantic similarity between texts

        Args:
            text1: First text
            text2: Second text

        Returns:
            Similarity score [0, 1]

        Method:
            Jaccard similarity on normalized word sets
        """
        # Normalize texts
        norm1 = self.normalize_text(text1.lower())
        norm2 = self.normalize_text(text2.lower())

        # Extract words
        words1 = set(norm1.split())
        words2 = set(norm2.split())

        # Compute Jaccard similarity
        if not words1 and not words2:
            return 1.0

        intersection = len(words1 & words2)
        union = len(words1 | words2)

        if union == 0:
            return 0.0

        return intersection / union

    def expand_query(self, query: str, max_synonyms: int = 3) -> list[str]:
        """
        Expand query with synonyms

        Args:
            query: Query to expand
            max_synonyms: Maximum synonyms per word

        Returns:
            List of expanded queries

        Use case:
            Query expansion for retrieval
        """
        words = query.split()
        expanded_queries = [query]  # Include original

        for i, word in enumerate(words):
            # Get synonyms
            synonyms = self.synonym_dict.get_synonyms(word)

            if synonyms:
                # Create variants with each synonym
                for syn in synonyms[:max_synonyms]:
                    variant_words = words.copy()
                    variant_words[i] = syn
                    expanded_queries.append(" ".join(variant_words))

        return expanded_queries


# Example usage
if __name__ == "__main__":
    print("🔤 Semantic Matcher Test")
    print("=" * 60)

    matcher = SemanticMatcher()

    # Test synonym detection
    print("\n1. Synonym Detection")
    pairs = [
        ("قرارداد", "عقد"),
        ("فسخ", "ابطال"),
        ("دادگاه", "محکمه"),
    ]

    for word1, word2 in pairs:
        is_syn = matcher.are_synonyms(word1, word2)
        print(f"  '{word1}' = '{word2}': {is_syn}")

    # Test antonym detection
    print("\n2. Antonym Detection")
    pairs = [
        ("مجاز", "ممنوع"),
        ("معتبر", "باطل"),
        ("صحیح", "نادرست"),
    ]

    for word1, word2 in pairs:
        is_ant = matcher.are_antonyms(word1, word2)
        print(f"  '{word1}' ≠ '{word2}': {is_ant}")

    # Test contradiction detection
    print("\n3. Contradiction Detection")
    pairs = [
        ("فسخ قرارداد مجاز است", "فسخ قرارداد ممنوع است"),
        ("عقد معتبر است", "قرارداد باطل است"),
        ("طرفین می‌توانند فسخ کنند", "طرفین نمی‌توانند فسخ کنند"),
    ]

    for text1, text2 in pairs:
        is_contr = matcher.are_contradictory(text1, text2)
        print(f"  '{text1}' ≠ '{text2}': {is_contr}")

    # Test normalization
    print("\n4. Text Normalization")
    texts = [
        "عقد فسخ شد",
        "پیمان ابطال گردید",
        "محکمه تهران رای داد",
    ]

    for text in texts:
        normalized = matcher.normalize_text(text)
        print(f"  '{text}' → '{normalized}'")

    # Test semantic similarity
    print("\n5. Semantic Similarity")
    pairs = [
        ("قرارداد فسخ شد", "عقد ابطال گردید"),
        ("دادگاه تهران", "محکمه تهران"),
        ("فسخ مجاز است", "ابطال ممنوع است"),
    ]

    for text1, text2 in pairs:
        sim = matcher.semantic_similarity(text1, text2)
        print(f"  '{text1}' ~ '{text2}': {sim:.2f}")

    # Test query expansion
    print("\n6. Query Expansion")
    query = "فسخ قرارداد"
    expanded = matcher.expand_query(query, max_synonyms=2)
    print(f"  Original: '{query}'")
    for exp in expanded[1:]:
        print(f"  Expanded: '{exp}'")

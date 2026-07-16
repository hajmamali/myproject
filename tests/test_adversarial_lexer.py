import unittest
from mahoun.core.governance.mutation_boundary import classify_cypher

class TestAdversarialLexer(unittest.TestCase):
    @pytest.mark.p2
    def test_comment_bypass_merging(self):
        # Traditional regex might fail on word boundary if comments are interleaved
        query = "MATCH (n) SET/* comment */n.prop = 1"
        self.assertTrue(classify_cypher(query), "Should detect SET even with interleaved comments")
        
    @pytest.mark.p2
    def test_multiline_comment_bypass(self):
        query = """
        MATCH (n)
        /* 
           DELETE 
        */
        RETURN n
        """
        # This is a READ query despite DELETE being in comments
        self.assertFalse(classify_cypher(query), "Should NOT detect DELETE inside comments")

    @pytest.mark.p2
    def test_apoc_block(self):
        query = "CALL apoc.cypher.run('CREATE (n:Leaked)')"
        self.assertTrue(classify_cypher(query), "Should block APOC calls as mutation-class intent")

    @pytest.mark.p2
    def test_dbms_block(self):
        query = "CALL dbms.security.listUsers()"
        self.assertTrue(classify_cypher(query), "Should block DBMS calls")

    @pytest.mark.p2
    def test_white_listed_db_calls(self):
        query = "CALL db.labels()"
        self.assertFalse(classify_cypher(query), "Should allow standard db. calls")

    @pytest.mark.p2
    def test_unicode_normalization_bypass(self):
        # Full-width Unicode (ＳＥＴ)
        query = "ＳＥＴ n.x = 1"
        self.assertTrue(classify_cypher(query), "Should detect full-width SET via NFKC normalization")
        
        # Script Capital E (ℰ)
        query = "SℰT n.x = 1"
        self.assertTrue(classify_cypher(query), "Should detect script capital E in SET via NFKC normalization")

        # Mixed case and unusual formatting
        query = "  mErGe (n:Person)  "
        self.assertTrue(classify_cypher(query), "Should detect mixed-case MERGE")

if __name__ == '__main__':
    unittest.main()

// Constraints
CREATE CONSTRAINT doc_id_unique IF NOT EXISTS
FOR (d:Document) REQUIRE d.doc_id IS UNIQUE;

CREATE CONSTRAINT case_id_unique IF NOT EXISTS
FOR (c:Case) REQUIRE c.case_id IS UNIQUE;

CREATE CONSTRAINT article_key_unique IF NOT EXISTS
FOR (a:Article) REQUIRE (a.doc_id, a.article_no) IS UNIQUE;

// Indexes
CREATE INDEX doc_title_idx IF NOT EXISTS FOR (d:Document) ON (d.title);
CREATE FULLTEXT INDEX ft_article_text IF NOT EXISTS
FOR (a:Article) ON EACH [a.text];


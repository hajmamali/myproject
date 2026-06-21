"""
Cypher Query Builder
====================

Fluent API for building Cypher queries.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


class CypherQueryBuilder:
    """
    Fluent query builder for Cypher

    Example:
        query = (CypherQueryBuilder()
            .match("Document", {"id": "doc1"}, alias="d")
            .where("d.title CONTAINS $title")
            .return_("d")
            .limit(10)
            .build())
    """

    def __init__(self, tenant_id: str = "default_tenant"):
        """
        Initialize CypherQueryBuilder

        Args:
            tenant_id: Mandatory tenant identifier for data isolation.
        """
        self._tenant_id = tenant_id
        self._match_clauses: List[str] = []
        self._where_clauses: List[str] = []
        self._return_clause: Optional[str] = None
        self._order_by: Optional[str] = None
        self._limit: Optional[int] = None
        self._skip: Optional[int] = None
        self._with_clause: Optional[str] = None

        # Initialize parameters with tenant_id for mandatory isolation
        self.parameters: Dict[str, Any] = {"_tenant_id": tenant_id}

    def match(
        self,
        label: str,
        properties: Optional[Dict[str, Any]] = None,
        alias: str = "n",
        optional: bool = False,
    ) -> CypherQueryBuilder:
        """
        Add MATCH clause with mandatory tenant isolation.

        Args:
            label: Node label
            properties: Node properties to match
            alias: Node alias
            optional: Use OPTIONAL MATCH

        Returns:
            Self for chaining
        """
        match_type = "OPTIONAL MATCH" if optional else "MATCH"

        # Enforce tenant isolation in properties
        safe_props = ["tenant_id: $_tenant_id"]

        if properties:
            import uuid

            for k, v in properties.items():
                # Use unique parameter keys to prevent collisions in complex queries
                param_key = f"{alias}_{k}_{uuid.uuid4().hex[:6]}"
                safe_props.append(f"{k}: ${param_key}")
                self.parameters[param_key] = v

        prop_str = ", ".join(safe_props)
        self._match_clauses.append(f"{match_type} ({alias}:{label} {{{prop_str}}})")

        return self

    def match_relationship(
        self,
        from_alias: str,
        to_alias: str,
        rel_type: str,
        rel_alias: str = "r",
        direction: str = "->",
        properties: Optional[Dict[str, Any]] = None,
    ) -> CypherQueryBuilder:
        """
        Add relationship match with unique parameters.
        """
        import uuid

        if properties:
            safe_props = []
            for k, v in properties.items():
                param_key = f"{rel_alias}_{k}_{uuid.uuid4().hex[:6]}"
                safe_props.append(f"{k}: ${param_key}")
                self.parameters[param_key] = v
            prop_str = ", ".join(safe_props)
            rel_pattern = f"[{rel_alias}:{rel_type} {{{prop_str}}}]"
        else:
            rel_pattern = f"[{rel_alias}:{rel_type}]"

        if direction == "->":
            pattern = f"({from_alias})-{rel_pattern}->({to_alias})"
        elif direction == "<-":
            pattern = f"({from_alias})<-{rel_pattern}-({to_alias})"
        else:
            pattern = f"({from_alias})-{rel_pattern}-({to_alias})"

        self._match_clauses.append(f"MATCH {pattern}")

        return self

    def where(self, condition: str) -> CypherQueryBuilder:
        """
        Add raw WHERE clause.
        DEPRECATED: Use where_exact or where_contains for safer parameterized queries.
        """
        import logging

        logging.getLogger(__name__).warning(
            "UNSAFE: .where() used with raw string. Consider using .where_exact() instead."
        )
        self._where_clauses.append(condition)
        return self

    def where_exact(self, alias: str, field: str, value: Any) -> CypherQueryBuilder:
        """
        Add strict WHERE clause using parameters.
        """
        import uuid

        param_key = f"where_{alias}_{field}_{uuid.uuid4().hex[:6]}"
        self._where_clauses.append(f"{alias}.{field} = ${param_key}")
        self.parameters[param_key] = value
        return self

    def where_contains(
        self, alias: str, field: str, substring: str
    ) -> CypherQueryBuilder:
        """
        Add text-search WHERE clause using parameters.
        """
        import uuid

        param_key = f"contains_{alias}_{field}_{uuid.uuid4().hex[:6]}"
        self._where_clauses.append(f"{alias}.{field} CONTAINS ${param_key}")
        self.parameters[param_key] = substring
        return self

    def return_(self, *fields: str) -> CypherQueryBuilder:
        """
        Add RETURN clause

        Args:
            *fields: Fields to return

        Returns:
            Self for chaining
        """
        self._return_clause = ", ".join(fields)
        return self

    def order_by(self, field: str, desc: bool = False) -> CypherQueryBuilder:
        """
        Add ORDER BY clause

        Args:
            field: Field to order by
            desc: Descending order

        Returns:
            Self for chaining
        """
        direction = "DESC" if desc else "ASC"
        self._order_by = f"{field} {direction}"
        return self

    def limit(self, n: int) -> CypherQueryBuilder:
        """
        Add LIMIT clause

        Args:
            n: Limit value

        Returns:
            Self for chaining
        """
        self._limit = n
        return self

    def skip(self, n: int) -> CypherQueryBuilder:
        """
        Add SKIP clause

        Args:
            n: Skip value

        Returns:
            Self for chaining
        """
        self._skip = n
        return self

    def with_(self, *fields: str) -> CypherQueryBuilder:
        """
        Add WITH clause

        Args:
            *fields: Fields to pass through

        Returns:
            Self for chaining
        """
        self._with_clause = ", ".join(fields)
        return self

    def build(self) -> str:
        """
        Build final query

        Returns:
            Cypher query string
        """
        parts: List[Any] = []
        # MATCH clauses
        if self._match_clauses:
            parts.extend(self._match_clauses)

        # WHERE clause
        if self._where_clauses:
            parts.append("WHERE " + " AND ".join(self._where_clauses))

        # WITH clause
        if self._with_clause:
            parts.append(f"WITH {self._with_clause}")

        # RETURN clause
        if self._return_clause:
            parts.append(f"RETURN {self._return_clause}")

        # ORDER BY
        if self._order_by:
            parts.append(f"ORDER BY {self._order_by}")

        # SKIP
        if self._skip is not None:
            parts.append(f"SKIP {self._skip}")

        # LIMIT
        if self._limit is not None:
            parts.append(f"LIMIT {self._limit}")

        return "\n".join(parts)

    def execute(self, connection=None):
        """
        Build and execute query

        Args:
            connection: Neo4j connection

        Returns:
            Query results
        """
        from mahoun.graph.neo4j.connection import get_connection

        conn = connection or get_connection()
        query = self.build()
        return conn.execute_query(query, self.parameters)

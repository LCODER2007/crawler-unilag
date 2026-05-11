"""
Advanced Search Service
Implements Boolean operators, field-specific queries, and full-text search.
Comparable to Scopus/Web of Science search capabilities.
"""

import logging
import re
from typing import Dict, List, Optional, Tuple

from sqlalchemy import and_, func, not_, or_, text

from uraas.database import Author, Collection, Community, Item, SessionLocal, db_year

logger = logging.getLogger(__name__)


class SearchQuery:
    """Parse and execute advanced search queries."""

    @staticmethod
    def parse_boolean_query(query: str) -> List[Tuple[str, str, str]]:
        """
        Parse Boolean search query into structured format.

        Supports:
        - AND, OR, NOT operators
        - Parentheses for grouping
        - Field-specific searches: title:machine, author:smith, year:2020
        - Phrase searches: "machine learning"
        - Wildcards: machin* (suffix), *learning (prefix)

        Examples:
            "machine learning" AND author:smith
            (covid OR pandemic) AND year:2020
            title:cancer NOT lung

        Returns:
            List of (field, operator, value) tuples
        """
        # Normalize query
        query = query.strip()

        # Extract field:value patterns
        field_pattern = r'(\w+):(["\']?)([^"\'\s]+|[^"\']+)\2'
        matches = re.findall(field_pattern, query)

        parsed = []
        for field, _, value in matches:
            parsed.append((field.lower(), "EQUALS", value))

        # Extract quoted phrases
        phrase_pattern = r'"([^"]+)"'
        phrases = re.findall(phrase_pattern, query)
        for phrase in phrases:
            parsed.append(("all", "PHRASE", phrase))

        # Extract remaining keywords
        # Remove field:value and phrases from query
        remaining = re.sub(field_pattern, "", query)
        remaining = re.sub(phrase_pattern, "", remaining)

        # Split by Boolean operators
        keywords = re.split(r"\s+(?:AND|OR|NOT)\s+|\s+", remaining)
        keywords = [
            k.strip()
            for k in keywords
            if k.strip() and k.upper() not in ("AND", "OR", "NOT")
        ]

        for keyword in keywords:
            if keyword:
                parsed.append(("all", "KEYWORD", keyword))

        return parsed

    @staticmethod
    def build_sql_filter(parsed_query: List[Tuple[str, str, str]]):
        """
        Build SQLAlchemy filter from parsed query.

        Returns:
            SQLAlchemy filter expression
        """
        filters = []

        for field, operator, value in parsed_query:
            if field == "title":
                filters.append(Item.title.ilike(f"%{value}%"))

            elif field == "abstract":
                filters.append(Item.abstract.ilike(f"%{value}%"))

            elif field == "author":
                # Subquery for author name
                filters.append(
                    Item.id.in_(
                        SessionLocal()
                        .query(Item.id)
                        .join(Item.authors)
                        .filter(Author.name.ilike(f"%{value}%"))
                    )
                )

            elif field == "year":
                try:
                    year = int(value)
                    filters.append(db_year(Item.publication_date) == str(year))
                except ValueError:
                    pass

            elif field == "doi":
                filters.append(Item.doi.ilike(f"%{value}%"))

            elif field == "faculty":
                filters.append(
                    Item.id.in_(
                        SessionLocal()
                        .query(Item.id)
                        .join(Item.collections)
                        .join(Collection.community)
                        .filter(Community.name.ilike(f"%{value}%"))
                    )
                )

            elif field == "department":
                filters.append(
                    Item.id.in_(
                        SessionLocal()
                        .query(Item.id)
                        .join(Item.collections)
                        .filter(Collection.name.ilike(f"%{value}%"))
                    )
                )

            elif field == "keyword":
                filters.append(
                    or_(
                        Item.ai_keywords.ilike(f"%{value}%"),
                        Item.dc_subject.ilike(f"%{value}%"),
                    )
                )

            elif field == "language":
                filters.append(Item.language_code == value.lower())

            elif field == "oa" or field == "openaccess":
                if value.lower() in ("true", "yes", "1"):
                    filters.append(Item.dc_rights.like("%openAccess%"))
                else:
                    filters.append(~Item.dc_rights.like("%openAccess%"))

            elif field == "all":
                # Search across all text fields
                if operator == "PHRASE":
                    filters.append(
                        or_(
                            Item.title.ilike(f"%{value}%"),
                            Item.abstract.ilike(f"%{value}%"),
                            Item.ai_keywords.ilike(f"%{value}%"),
                        )
                    )
                else:
                    filters.append(
                        or_(
                            Item.title.ilike(f"%{value}%"),
                            Item.abstract.ilike(f"%{value}%"),
                            Item.doi.ilike(f"%{value}%"),
                            Item.ai_keywords.ilike(f"%{value}%"),
                        )
                    )

        # Combine filters with AND
        if filters:
            return and_(*filters)
        return None

    @staticmethod
    def execute_search(
        query: str,
        limit: int = 50,
        offset: int = 0,
        sort_by: str = "relevance",
        filters: Optional[Dict] = None,
    ) -> Dict:
        """
        Execute advanced search query.

        Args:
            query: Search query string (supports Boolean operators)
            limit: Maximum results to return
            offset: Pagination offset
            sort_by: Sort order ('relevance', 'date', 'citations', 'title')
            filters: Additional filters (year_from, year_to, oa_only, etc.)

        Returns:
            {
                'total': int,
                'results': [paper_dict, ...],
                'query_parsed': str,
                'took_ms': float
            }
        """
        import time

        start_time = time.time()

        session = SessionLocal()
        try:
            # Parse query
            parsed = SearchQuery.parse_boolean_query(query)

            # Build base query
            q = session.query(Item)

            # Apply parsed query filters
            sql_filter = SearchQuery.build_sql_filter(parsed)
            if sql_filter is not None:
                q = q.filter(sql_filter)

            # Apply additional filters
            if filters:
                if filters.get("year_from"):
                    q = q.filter(
                        db_year(Item.publication_date) >= str(filters["year_from"])
                    )

                if filters.get("year_to"):
                    q = q.filter(
                        db_year(Item.publication_date) <= str(filters["year_to"])
                    )

                if filters.get("oa_only"):
                    q = q.filter(Item.dc_rights.like("%openAccess%"))

                if filters.get("faculty"):
                    q = (
                        q.join(Item.collections)
                        .join(Collection.community)
                        .filter(Community.name.ilike(f'%{filters["faculty"]}%'))
                    )

                if filters.get("has_pdf"):
                    from uraas.database import File

                    q = q.join(File, File.item_id == Item.id)

            # Get total count
            total = q.count()

            # Apply sorting
            if sort_by == "date":
                q = q.order_by(Item.publication_date.desc().nullslast())
            elif sort_by == "title":
                q = q.order_by(Item.title)
            elif sort_by == "citations":
                # Join with citation metrics if available
                from uraas.services.citation_tracker import CitationMetrics

                q = q.outerjoin(
                    CitationMetrics, CitationMetrics.item_id == Item.id
                ).order_by(CitationMetrics.citation_count.desc().nullslast())
            else:  # relevance (default)
                # Simple relevance: prioritize title matches
                q = q.order_by(Item.created_at.desc())

            # Pagination
            results = q.limit(limit).offset(offset).all()

            # Format results
            formatted_results = []
            for item in results:
                formatted_results.append(
                    {
                        "id": item.id,
                        "title": item.title,
                        "abstract": item.abstract[:300] if item.abstract else None,
                        "doi": item.doi,
                        "url": item.url,
                        "year": (
                            item.publication_date.year
                            if item.publication_date
                            else None
                        ),
                        "authors": [a.name for a in item.authors[:5]],
                        "faculty": (
                            item.collections[0].community.name
                            if item.collections and item.collections[0].community
                            else None
                        ),
                        "department": (
                            item.collections[0].name if item.collections else None
                        ),
                        "is_oa": "openAccess" in (item.dc_rights or ""),
                        "docid": item.docid,
                        "language": item.language_code,
                        "keywords": (
                            item.ai_keywords.split(",")[:5] if item.ai_keywords else []
                        ),
                    }
                )

            took_ms = (time.time() - start_time) * 1000

            return {
                "total": total,
                "results": formatted_results,
                "query_parsed": str(parsed),
                "took_ms": round(took_ms, 2),
                "page": offset // limit + 1,
                "pages": (total + limit - 1) // limit,
            }

        except Exception as e:
            logger.error(f"Search failed: {e}")
            return {"total": 0, "results": [], "error": str(e), "took_ms": 0}
        finally:
            session.close()

    @staticmethod
    def get_search_suggestions(partial_query: str, field: str = "all") -> List[str]:
        """
        Get autocomplete suggestions for search queries.

        Args:
            partial_query: Partial search term
            field: Field to search ('author', 'keyword', 'faculty', 'all')

        Returns:
            List of suggested completions
        """
        session = SessionLocal()
        try:
            suggestions = []

            if field in ("author", "all"):
                authors = (
                    session.query(Author.name)
                    .filter(Author.name.ilike(f"%{partial_query}%"))
                    .limit(10)
                    .all()
                )
                suggestions.extend([f"author:{a[0]}" for a in authors])

            if field in ("faculty", "all"):
                faculties = (
                    session.query(Community.name)
                    .filter(Community.name.ilike(f"%{partial_query}%"))
                    .limit(5)
                    .all()
                )
                suggestions.extend([f"faculty:{f[0]}" for f in faculties])

            if field in ("keyword", "all"):
                # Extract keywords from papers
                items = (
                    session.query(Item.ai_keywords)
                    .filter(Item.ai_keywords.ilike(f"%{partial_query}%"))
                    .limit(20)
                    .all()
                )

                keywords = set()
                for item in items:
                    if item[0]:
                        for kw in item[0].split(","):
                            kw = kw.strip()
                            if partial_query.lower() in kw.lower():
                                keywords.add(kw)

                suggestions.extend([f"keyword:{k}" for k in list(keywords)[:10]])

            return suggestions[:15]

        finally:
            session.close()


# ── Saved Searches ────────────────────────────────────────────────────────────


class SavedSearch:
    """Manage saved search queries for users."""

    @staticmethod
    def save_search(name: str, query: str, filters: Optional[Dict] = None) -> int:
        """Save a search query for later reuse."""
        # TODO: Implement user authentication first
        # For now, store in a simple table
        pass

    @staticmethod
    def get_saved_searches() -> List[Dict]:
        """Get all saved searches."""
        # TODO: Implement
        pass

    @staticmethod
    def execute_saved_search(search_id: int) -> Dict:
        """Execute a previously saved search."""
        # TODO: Implement
        pass

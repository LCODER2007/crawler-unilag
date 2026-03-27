from sqlalchemy import func, desc
from sqlalchemy.orm import joinedload
from uraas.database import SessionLocal, Item, Author, Collection, Community, File

class URAASAnalyticsEngine:
    """
    World-class analysis module for URAAS.
    Provides deep insights into UNILAG's aggregate research data.
    """
    def __init__(self):
        pass

    def get_top_authors(self, limit=10, community_id=None):
        """Returns the most productive authors, optionally filtered by Community."""
        session = SessionLocal()
        try:
            query = session.query(
                Author.name,
                func.count(Item.id).label('paper_count')
            ).join(Author.items)

            if community_id:
                query = query.join(Item.collections).join(Collection.community).filter(Community.id == community_id)

            results = query.group_by(Author.name).order_by(desc('paper_count')).limit(limit).all()
            return [{"author": r[0], "paper_count": r[1]} for r in results]
        except Exception as e:
            print(f"Error in get_top_authors: {str(e)}")
            return []
        finally:
            session.close()

    def get_department_collaboration_network(self):
        """
        Builds a graph representation of which collections (departments) collaborate on papers together.
        Returns a list of edge weights.
        """
        session = SessionLocal()
        try:
            # Fetch all items with their collections
            docs = session.query(Item).options(joinedload(Item.collections)).all()
            
            edges = {}
            for doc in docs:
                try:
                    colls = sorted([c.name for c in doc.collections if c and c.name])
                    # If a paper is classified under multiple collections, it's a collaboration
                    if len(colls) > 1:
                        import itertools
                        for pair in itertools.combinations(colls, 2):
                            edges[pair] = edges.get(pair, 0) + 1
                except Exception as e:
                    print(f"Error processing document {doc.id} in collaboration network: {str(e)}")
                    continue
            
            return [{"source": k[0], "target": k[1], "weight": v} for k, v in edges.items()]
        except Exception as e:
            print(f"Error in get_department_collaboration_network: {str(e)}")
            return []
        finally:
            session.close()

    def get_publication_trends(self):
        """
        Group papers by publication year and Community to analyze growth trends over time.
        """
        session = SessionLocal()
        try:
            # Since SQLite/Postgres date functions differ, we'll do simple extraction if date is present
            # Assuming publication_date is a valid datetime object
            query = session.query(
                func.extract('year', Item.publication_date).label('year'),
                Community.name,
                func.count(Item.id).label('total')
            ).join(Item.collections).join(Collection.community).group_by(
                func.extract('year', Item.publication_date),
                Community.name
            ).all()
            
            return [{"year": r[0], "faculty": r[1], "total": r[2]} for r in query if r[0]]
        except Exception as e:
            print(f"Error in get_publication_trends: {str(e)}")
            return []
        finally:
            session.close()

    def get_papers_by_faculty_and_department(self):
        """
        Generates the tree: Community -> Collection -> [Items]
        Papers not linked to any collection appear under 'Unclassified'.
        """
        session = SessionLocal()
        try:
            communities = session.query(Community).options(joinedload(Community.collections)).all()

            tree = {}
            seen_ids = set()

            for c in communities:
                try:
                    dept_map = {}
                    for coll in c.collections:
                        try:
                            papers = session.query(Item).join(Item.collections).filter(Collection.id == coll.id).all()
                            paper_list = []
                            for p in papers:
                                try:
                                    seen_ids.add(p.id)
                                    file_record = session.query(File).filter_by(item_id=p.id).first()
                                    paper_list.append({
                                        "id": p.id,
                                        "title": p.title or "Untitled",
                                        "doi": p.doi or "",
                                        "url": p.url or "",
                                        "has_local_pdf": file_record is not None,
                                        "access_policy": file_record.access_policy if file_record else None,
                                        "download_url": f"/api/papers/{p.id}/download" if file_record else None
                                    })
                                except Exception as e:
                                    print(f"Error processing paper {p.id}: {str(e)}")
                                    continue
                            if paper_list:
                                dept_map[coll.name] = paper_list
                        except Exception as e:
                            print(f"Error processing collection {coll.id}: {str(e)}")
                            continue

                    if dept_map:
                        tree[c.name] = dept_map
                except Exception as e:
                    print(f"Error processing community {c.id}: {str(e)}")
                    continue

            # Add all unclassified papers under their own bucket
            try:
                unclassified = session.query(Item).filter(~Item.id.in_(seen_ids)).all() if seen_ids else session.query(Item).all()
                if unclassified:
                    unclassified_list = []
                    for p in unclassified:
                        try:
                            file_record = session.query(File).filter_by(item_id=p.id).first()
                            unclassified_list.append({
                                "id": p.id,
                                "title": p.title or "Untitled",
                                "doi": p.doi or "",
                                "url": p.url or "",
                                "has_local_pdf": file_record is not None,
                                "access_policy": file_record.access_policy if file_record else None,
                                "download_url": f"/api/papers/{p.id}/download" if file_record else None
                            })
                        except Exception as e:
                            print(f"Error processing unclassified paper {p.id}: {str(e)}")
                            continue
                    if unclassified_list:
                        tree["Unclassified"] = {"General": unclassified_list}
            except Exception as e:
                print(f"Error processing unclassified papers: {str(e)}")

            return tree
        except Exception as e:
            print(f"Error in get_papers_by_faculty_and_department: {str(e)}")
            return {}
        finally:
            session.close()

analytics = URAASAnalyticsEngine()

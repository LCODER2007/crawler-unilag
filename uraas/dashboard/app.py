import os
import subprocess
import threading
import re
from flask import Flask, render_template, jsonify, send_file, request
from flask_socketio import SocketIO
from uraas.config import config
from uraas.analytics.engine import analytics
from uraas.database import SessionLocal, Item, File, Author, Community, Collection
from sqlalchemy import func, extract, desc

app = Flask(__name__)
app.config['SECRET_KEY'] = config.DASHBOARD_SECRET_KEY
socketio = SocketIO(app, cors_allowed_origins="*")

crawler_process = None
crawler_lock = threading.Lock()

def crawler_monitor(process):
    """Monitor crawler output and stream to dashboard."""
    global crawler_process
    try:
        for line in iter(process.stdout.readline, b''):
            # Check if process was terminated
            with crawler_lock:
                if crawler_process is None or crawler_process != process:
                    break
                    
            line_decoded = line.decode('utf-8', errors='replace').strip()
            if not line_decoded:
                continue
            # Initialization phase
            if line_decoded.startswith('[INIT]'):
                socketio.emit('crawl_status', {'status': 'initializing', 'message': line_decoded})
                socketio.emit('terminal_output', {'line': line_decoded})
            # Switch to running once actual storing begins
            elif '[OK]' in line_decoded and ']' in line_decoded:
                socketio.emit('crawl_status', {'status': 'running'})
                try:
                    title = line_decoded.split('] ', 1)[-1].strip()
                    socketio.emit('crawl_progress', {'title': title})
                except:
                    pass
                socketio.emit('terminal_output', {'line': line_decoded})
            else:
                socketio.emit('terminal_output', {'line': line_decoded})
    except Exception:
        pass
    finally:
        try:
            process.stdout.close()
        except:
            pass
        process.wait()
        with crawler_lock:
            if crawler_process == process:
                crawler_process = None
        socketio.emit('crawl_status', {'status': 'stopped'})

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/stats')
def get_stats():
    try:
        top_authors = analytics.get_top_authors(limit=5)
        network = analytics.get_department_collaboration_network()
        return jsonify({
            "status": "success",
            "top_authors": top_authors,
            "network_edges": network,
        })
    except Exception as e:
        app.logger.error(f"Error in get_stats: {str(e)}")
        return jsonify({
            "status": "error",
            "message": "Failed to retrieve statistics",
            "top_authors": [],
            "network_edges": []
        }), 500

@app.route('/api/papers/tree')
def papers_tree():
    try:
        tree = analytics.get_papers_by_faculty_and_department()
        return jsonify({
            "status": "success",
            "data": tree
        })
    except Exception as e:
        app.logger.error(f"Error in papers_tree: {str(e)}")
        return jsonify({
            "status": "error",
            "message": "Failed to retrieve papers tree",
            "data": []
        }), 500

@app.route('/api/papers/<int:item_id>')
def get_paper(item_id):
    """Get full DSpace-style metadata for a single paper."""
    session = SessionLocal()
    try:
        item = session.query(Item).filter_by(id=item_id).first()
        if not item:
            return jsonify({"error": "Paper not found"}), 404

        file_record = session.query(File).filter_by(item_id=item_id).first()
        collections = [{"id": c.id, "name": c.name, "faculty": c.community.name if c.community else "Unknown"} 
                      for c in item.collections]

        return jsonify({
            "id": item.id,
            "title": item.title or "Untitled",
            "abstract": item.abstract or "",
            "doi": item.doi or "",
            "url": item.url or "",
            "pdf_url": item.pdf_url or "",
            "publication_date": item.publication_date.isoformat() if item.publication_date else None,
            "source_repository": item.source_repository or "",
            "authors": [{"name": a.name} for a in item.authors],
            "collections": collections,
            "dc": {
                "title": item.dc_title or "",
                "date_issued": item.dc_date_issued or "",
                "identifier_uri": item.dc_identifier_uri or "",
                "identifier_doi": item.dc_identifier_doi or "",
                "description_provenance": item.dc_description_provenance or "",
                "rights": item.dc_rights or "",
            },
            "file": {
                "has_local_pdf": file_record is not None,
                "access_policy": file_record.access_policy if file_record else None,
                "download_url": f"/api/papers/{item_id}/download" if file_record else None,
                "sha256": file_record.sha256_hash if file_record else None,
            } if file_record else {"has_local_pdf": False},
            "created_at": item.created_at.isoformat() if item.created_at else None,
        })
    except Exception as e:
        app.logger.error(f"Error retrieving paper {item_id}: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500
    finally:
        session.close()


@app.route('/api/analytics/overview')
def analytics_overview():
    """High-level stats for the analytics dashboard."""
    session = SessionLocal()
    try:
        total_papers = session.query(Item).count()
        total_authors = session.query(Author).count()
        total_faculties = session.query(Community).count()
        oa_papers = session.query(Item).filter(
            Item.dc_rights.like('%openAccess%')
        ).count()
        papers_with_pdf = session.query(File).count()

        return jsonify({
            "total_papers": total_papers,
            "total_authors": total_authors,
            "total_faculties": total_faculties,
            "open_access_papers": oa_papers,
            "papers_with_local_pdf": papers_with_pdf,
            "oa_percentage": round((oa_papers / total_papers * 100) if total_papers else 0, 1),
        })
    except Exception as e:
        app.logger.error(f"Error in analytics_overview: {str(e)}")
        return jsonify({
            "total_papers": 0,
            "total_authors": 0,
            "total_faculties": 0,
            "open_access_papers": 0,
            "papers_with_local_pdf": 0,
            "oa_percentage": 0,
            "error": "Failed to load analytics"
        }), 500
    finally:
        session.close()


@app.route('/api/analytics/publications-by-year')
def publications_by_year():
    """Papers per year for trend chart."""
    session = SessionLocal()
    try:
        rows = session.query(
            extract('year', Item.publication_date).label('year'),
            func.count(Item.id).label('count')
        ).filter(Item.publication_date.isnot(None)) \
         .group_by('year').order_by('year').all()

        return jsonify([{"year": int(r.year), "count": r.count} for r in rows if r.year])
    finally:
        session.close()


@app.route('/api/analytics/papers-by-faculty')
def papers_by_faculty():
    """Paper count per faculty for bar/pie chart."""
    session = SessionLocal()
    try:
        rows = session.query(
            Community.name,
            func.count(Item.id).label('count')
        ).join(Collection, Collection.community_id == Community.id) \
         .join(Collection.items) \
         .group_by(Community.name) \
         .order_by(desc('count')).all()

        return jsonify([{"faculty": r[0], "count": r[1]} for r in rows])
    finally:
        session.close()


@app.route('/api/analytics/top-authors')
def top_authors_analytics():
    """Top authors with paper counts."""
    limit = int(request.args.get('limit', 15))
    session = SessionLocal()
    try:
        rows = session.query(
            Author.name,
            func.count(Item.id).label('count')
        ).join(Author.items).group_by(Author.name) \
         .order_by(desc('count')).limit(limit).all()

        return jsonify([{"author": r[0], "count": r[1]} for r in rows])
    finally:
        session.close()


@app.route('/api/analytics/open-access-breakdown')
def oa_breakdown():
    """Open access vs restricted breakdown."""
    session = SessionLocal()
    try:
        oa = session.query(Item).filter(Item.dc_rights.like('%openAccess%')).count()
        restricted = session.query(Item).filter(Item.dc_rights.like('%restrictedAccess%')).count()
        total = session.query(Item).count()
        other = total - oa - restricted

        return jsonify([
            {"label": "Open Access", "value": oa},
            {"label": "Restricted", "value": restricted},
            {"label": "Unknown", "value": other},
        ])
    finally:
        session.close()


@app.route('/api/analytics/recent-papers')
def recent_papers():
    """Most recently added papers."""
    limit = int(request.args.get('limit', 10))
    session = SessionLocal()
    try:
        items = session.query(Item).order_by(desc(Item.created_at)).limit(limit).all()
        return jsonify([{
            "id": i.id,
            "title": i.title,
            "doi": i.doi,
            "authors": [a.name for a in i.authors[:3]],
            "created_at": i.created_at.isoformat() if i.created_at else None,
            "is_oa": 'openAccess' in (i.dc_rights or ''),
        } for i in items])
    finally:
        session.close()


@app.route('/api/analytics/growth-rate')
def growth_rate():
    """Papers added per crawl session (by provenance date)."""
    session = SessionLocal()
    try:
        rows = session.query(
            Item.dc_description_provenance,
            func.count(Item.id).label('count')
        ).filter(Item.dc_description_provenance.isnot(None)) \
         .group_by(Item.dc_description_provenance) \
         .order_by(Item.dc_description_provenance).all()
        return jsonify([{"session": r[0], "count": r[1]} for r in rows])
    finally:
        session.close()


@app.route('/api/analytics/papers-by-year-faculty')
def papers_by_year_faculty():
    session = SessionLocal()
    try:
        rows = session.query(
            extract('year', Item.publication_date).label('year'),
            Community.name.label('faculty'),
            func.count(Item.id).label('count')
        ).join(Item.collections).join(Collection.community) \
         .filter(Item.publication_date.isnot(None)) \
         .group_by('year', Community.name).order_by('year').all()
        return jsonify([{"year": int(r.year), "faculty": r.faculty, "count": r.count} for r in rows if r.year])
    finally:
        session.close()


@app.route('/api/analytics/author-network')
def author_network():
    """Get collaboration network. If author param provided, returns only their TOP UNILAG staff collaborations."""
    author_name = request.args.get('author', '').strip()
    session = SessionLocal()
    try:
        if author_name:
            # Get UNILAG staff list for filtering
            from uraas.utils.staff_validator import staff_validator
            unilag_staff = set(staff_validator.staff_names)
            
            # Get collaborations for specific author only - LIMIT TO TOP 10 UNILAG STAFF
            items = session.query(Item).join(Item.authors).filter(Author.name == author_name).all()
            edges = {}
            
            for item in items:
                names = [a.name for a in item.authors]
                if author_name not in names:
                    continue
                for name in names:
                    # Only count UNILAG staff collaborators
                    if name != author_name and staff_validator.is_staff_member(name, fuzzy_threshold=85):
                        key = tuple(sorted([author_name, name]))
                        edges[key] = edges.get(key, 0) + 1
            
            # Sort by weight and take only TOP 10 UNILAG collaborators
            edge_list = [
                {"source": k[0], "target": k[1], "weight": v}
                for k, v in edges.items()
            ]
            edge_list.sort(key=lambda x: -x['weight'])
            top_edges = edge_list[:10]  # ONLY TOP 10!
            
            # Get only the UNILAG collaborators in top edges
            collaborators = set()
            for edge in top_edges:
                if edge['source'] != author_name:
                    collaborators.add(edge['source'])
                if edge['target'] != author_name:
                    collaborators.add(edge['target'])
            
            return jsonify({
                "nodes": [{"id": author_name, "count": len(items)}] + 
                         [{"id": c, "count": 0} for c in collaborators],
                "edges": top_edges
            })
        else:
            # Return top collaborations across all authors (original behavior)
            items = session.query(Item).all()
            edges = {}
            node_counts = {}
            for item in items:
                names = [a.name for a in item.authors]
                for n in names:
                    node_counts[n] = node_counts.get(n, 0) + 1
                for i in range(len(names)):
                    for j in range(i + 1, len(names)):
                        key = tuple(sorted([names[i], names[j]]))
                        edges[key] = edges.get(key, 0) + 1
            top_nodes = sorted(node_counts.items(), key=lambda x: -x[1])[:30]
            top_names = {n for n, _ in top_nodes}
            filtered_edges = [
                {"source": k[0], "target": k[1], "weight": v}
                for k, v in edges.items()
                if k[0] in top_names and k[1] in top_names
            ]
            return jsonify({"nodes": [{"id": n, "count": c} for n, c in top_nodes], "edges": filtered_edges})
    finally:
        session.close()


@app.route('/api/analytics/faculty-oa-breakdown')
def faculty_oa_breakdown():
    session = SessionLocal()
    try:
        rows = session.query(
            Community.name, Item.dc_rights, func.count(Item.id).label('count')
        ).join(Item.collections).join(Collection.community) \
         .group_by(Community.name, Item.dc_rights).all()
        result = {}
        for faculty, rights, count in rows:
            if faculty not in result:
                result[faculty] = {"open": 0, "restricted": 0}
            if rights and 'openAccess' in rights:
                result[faculty]["open"] += count
            else:
                result[faculty]["restricted"] += count
        return jsonify([{"faculty": k, **v} for k, v in result.items()])
    finally:
        session.close()


@app.route('/api/analytics/search')
def analytics_search():
    q = request.args.get('q', '').strip()
    faculty = request.args.get('faculty', '').strip()
    year_from = request.args.get('year_from', type=int)
    year_to = request.args.get('year_to', type=int)
    oa_only = request.args.get('oa_only', '').lower() == 'true'
    limit = min(int(request.args.get('limit', 50)), 200)
    session = SessionLocal()
    try:
        q_obj = session.query(Item)
        if q:
            q_obj = q_obj.filter(Item.title.ilike(f'%{q}%'))
        if faculty:
            q_obj = q_obj.join(Item.collections).join(Collection.community).filter(Community.name.ilike(f'%{faculty}%'))
        if year_from:
            q_obj = q_obj.filter(extract('year', Item.publication_date) >= year_from)
        if year_to:
            q_obj = q_obj.filter(extract('year', Item.publication_date) <= year_to)
        if oa_only:
            q_obj = q_obj.filter(Item.dc_rights.like('%openAccess%'))
        items = q_obj.order_by(desc(Item.created_at)).limit(limit).all()
        return jsonify([{
            "id": i.id, "title": i.title, "doi": i.doi,
            "authors": [a.name for a in i.authors[:4]],
            "year": i.publication_date.year if i.publication_date else None,
            "is_oa": 'openAccess' in (i.dc_rights or ''),
            "faculty": i.collections[0].community.name if i.collections else None,
        } for i in items])
    finally:
        session.close()


@app.route('/api/analytics/faculties')
def list_faculties():
    session = SessionLocal()
    try:
        rows = session.query(Community.name).order_by(Community.name).all()
        return jsonify([r[0] for r in rows])
    finally:
        session.close()


@app.route('/api/analytics/faculty-comparison')
def faculty_comparison():
    """Compare two or more faculties across multiple metrics."""
    faculties = request.args.getlist('faculty')
    session = SessionLocal()
    try:
        result = {}
        for fac_name in faculties:
            comm = session.query(Community).filter(Community.name.ilike(f'%{fac_name}%')).first()
            if not comm:
                continue
            items = session.query(Item).join(Item.collections).join(Collection.community).filter(
                Community.id == comm.id
            ).all()
            oa_count = sum(1 for i in items if 'openAccess' in (i.dc_rights or ''))
            years = [i.publication_date.year for i in items if i.publication_date]
            authors_set = set(a.name for i in items for a in i.authors)
            result[comm.name] = {
                "total_papers": len(items),
                "open_access": oa_count,
                "restricted": len(items) - oa_count,
                "oa_rate": round(oa_count / len(items) * 100, 1) if items else 0,
                "unique_authors": len(authors_set),
                "year_range": [min(years), max(years)] if years else [],
                "avg_year": round(sum(years) / len(years), 0) if years else None,
                "departments": len(comm.collections),
            }
        return jsonify(result)
    finally:
        session.close()


@app.route('/api/analytics/department-comparison')
def department_comparison():
    """Compare departments within a faculty."""
    faculty = request.args.get('faculty', '')
    session = SessionLocal()
    try:
        comm = session.query(Community).filter(Community.name.ilike(f'%{faculty}%')).first()
        if not comm:
            return jsonify({})
        result = {}
        for coll in comm.collections:
            items = session.query(Item).join(Item.collections).filter(Collection.id == coll.id).all()
            if not items:
                continue
            oa = sum(1 for i in items if 'openAccess' in (i.dc_rights or ''))
            years = [i.publication_date.year for i in items if i.publication_date]
            result[coll.name] = {
                "total": len(items),
                "open_access": oa,
                "restricted": len(items) - oa,
                "oa_rate": round(oa / len(items) * 100, 1) if items else 0,
                "unique_authors": len(set(a.name for i in items for a in i.authors)),
                "years": sorted(set(years)),
            }
        return jsonify(result)
    finally:
        session.close()


@app.route('/api/analytics/lecturer-profile')
def lecturer_profile():
    """Full profile for a specific lecturer/author."""
    name = request.args.get('name', '').strip()
    session = SessionLocal()
    try:
        author = session.query(Author).filter(Author.name.ilike(f'%{name}%')).first()
        if not author:
            return jsonify({"error": "Author not found"}), 404
        items = author.items
        oa = sum(1 for i in items if 'openAccess' in (i.dc_rights or ''))
        years = sorted(set(i.publication_date.year for i in items if i.publication_date))
        faculties = list(set(
            c.community.name for i in items for c in i.collections if c.community
        ))
        depts = list(set(c.name for i in items for c in i.collections))
        co_authors = {}
        for item in items:
            for a in item.authors:
                if a.name != author.name:
                    co_authors[a.name] = co_authors.get(a.name, 0) + 1
        top_co = sorted(co_authors.items(), key=lambda x: -x[1])[:10]
        return jsonify({
            "name": author.name,
            "total_papers": len(items),
            "open_access": oa,
            "oa_rate": round(oa / len(items) * 100, 1) if items else 0,
            "active_years": years,
            "faculties": faculties,
            "departments": depts,
            "top_collaborators": [{"name": n, "papers": c} for n, c in top_co],
            "papers": [{
                "id": i.id, "title": i.title, "doi": i.doi,
                "year": i.publication_date.year if i.publication_date else None,
                "is_oa": 'openAccess' in (i.dc_rights or '')
            } for i in sorted(items, key=lambda x: x.publication_date or __import__('datetime').datetime.min, reverse=True)[:20]]
        })
    finally:
        session.close()


@app.route('/api/analytics/language-research')
def language_research():
    """
    Language & cultural research analysis — especially for Faculty of Arts.
    Returns papers from the Language Research Papers collection.
    """
    session = SessionLocal()
    try:
        # Get papers from Language Research Papers collection
        lang_collection = session.query(Collection).filter_by(name='Language Research Papers').first()
        
        if not lang_collection:
            return jsonify({
                "total_language_papers": 0,
                "top_keywords": [],
                "papers": []
            })
        
        matches = []
        keyword_counts = {}
        
        for item in lang_collection.items:
            try:
                # Extract keywords from title and abstract
                text = f"{item.title or ''} {item.abstract or ''}".lower()
                words = re.findall(r'\b\w+\b', text)
                
                # Count meaningful keywords (longer than 4 chars, not common words)
                common_words = {'the', 'and', 'for', 'with', 'this', 'that', 'from', 'have', 'been', 'were', 'their', 'which', 'these', 'about', 'other', 'into', 'than', 'more', 'such', 'some', 'what', 'when', 'where', 'there'}
                for word in words:
                    if len(word) > 4 and word not in common_words:
                        keyword_counts[word] = keyword_counts.get(word, 0) + 1
                
                matches.append({
                    "id": item.id,
                    "title": item.title,
                    "year": item.publication_date.year if item.publication_date else None,
                    "authors": [a.name for a in item.authors[:3]],
                    "is_oa": 'openAccess' in (item.dc_rights or '')
                })
            except Exception as e:
                app.logger.error(f"Error processing item {item.id} in language_research: {str(e)}")
                continue
        
        top_keywords = sorted(keyword_counts.items(), key=lambda x: -x[1])[:20]
        return jsonify({
            "total_language_papers": len(matches),
            "top_keywords": [{"keyword": k, "count": v} for k, v in top_keywords],
            "papers": sorted(matches, key=lambda x: -(x.get('year') or 0))[:50]
        })
    except Exception as e:
        app.logger.error(f"Error in language_research endpoint: {str(e)}")
        return jsonify({"error": "Internal server error", "total_language_papers": 0, "top_keywords": [], "papers": []}), 500
    finally:
        session.close()


@app.route('/api/analytics/research-trends')
def research_trends():
    """Identify emerging and declining research topics over time."""
    session = SessionLocal()
    try:
        # Get papers with years
        items = session.query(Item).filter(Item.publication_date.isnot(None)).all()
        TOPIC_KEYWORDS = {
            'COVID-19 / Pandemic': ['covid', 'sars-cov', 'pandemic', 'coronavirus'],
            'Cancer Research': ['cancer', 'tumour', 'tumor', 'oncology', 'carcinoma'],
            'Malaria': ['malaria', 'plasmodium', 'antimalarial'],
            'HIV/AIDS': ['hiv', 'aids', 'antiretroviral'],
            'Sustainable Energy': ['solar', 'renewable energy', 'wind energy', 'photovoltaic'],
            'Machine Learning / AI': ['machine learning', 'deep learning', 'neural network', 'artificial intelligence'],
            'Climate Change': ['climate change', 'global warming', 'carbon emission', 'greenhouse'],
            'Antimicrobial Resistance': ['antimicrobial resistance', 'antibiotic resistance', 'amr'],
            'Water & Sanitation': ['water quality', 'wastewater', 'sanitation', 'water treatment'],
            'Nigerian Languages': ['yoruba', 'igbo', 'hausa', 'nigerian language', 'african language'],
            'Urban Development': ['urban planning', 'urbanization', 'smart city', 'housing'],
            'Maternal Health': ['maternal', 'obstetric', 'pregnancy', 'antenatal', 'postnatal'],
        }
        trend_data = {topic: {} for topic in TOPIC_KEYWORDS}
        for item in items:
            year = item.publication_date.year
            text = f"{item.title or ''} {item.abstract or ''}".lower()
            for topic, keywords in TOPIC_KEYWORDS.items():
                if any(kw in text for kw in keywords):
                    trend_data[topic][year] = trend_data[topic].get(year, 0) + 1
        result = []
        for topic, years_data in trend_data.items():
            if years_data:
                result.append({
                    "topic": topic,
                    "total": sum(years_data.values()),
                    "by_year": [{"year": y, "count": c} for y, c in sorted(years_data.items())]
                })
        result.sort(key=lambda x: -x['total'])
        return jsonify(result)
    finally:
        session.close()


@app.route('/api/analytics/impact-metrics')
def impact_metrics():
    """High-level impact metrics for the repository."""
    session = SessionLocal()
    try:
        total = session.query(Item).count()
        oa = session.query(Item).filter(Item.dc_rights.like('%openAccess%')).count()
        with_doi = session.query(Item).filter(Item.doi.isnot(None)).count()
        with_pdf = session.query(File).count()
        years = session.query(extract('year', Item.publication_date)).filter(
            Item.publication_date.isnot(None)
        ).distinct().count()
        faculties_active = session.query(Community.id).join(Community.collections).join(
            Collection.items
        ).distinct().count()
        return jsonify({
            "total_papers": total,
            "open_access_papers": oa,
            "oa_rate": round(oa / total * 100, 1) if total else 0,
            "papers_with_doi": with_doi,
            "doi_rate": round(with_doi / total * 100, 1) if total else 0,
            "papers_with_local_pdf": with_pdf,
            "pdf_rate": round(with_pdf / total * 100, 1) if total else 0,
            "years_covered": years,
            "active_faculties": faculties_active,
        })
    finally:
        session.close()


@app.route('/api/analytics/authors-search')
def authors_search():
    """Search authors by name fragment."""
    q = request.args.get('q', '').strip()
    limit = min(int(request.args.get('limit', 20)), 50)
    session = SessionLocal()
    try:
        rows = session.query(
            Author.name, func.count(Item.id).label('count')
        ).join(Author.items).filter(Author.name.ilike(f'%{q}%')) \
         .group_by(Author.name).order_by(desc('count')).limit(limit).all()
        return jsonify([{"name": r[0], "papers": r[1]} for r in rows])
    finally:
        session.close()


@app.route('/api/papers/<int:item_id>/download')
def download_paper(item_id):
    session = SessionLocal()
    try:
        file_record = session.query(File).filter_by(item_id=item_id).first()
        if not file_record:
            return jsonify({"error": "PDF not found"}), 404
        
        # Fix path - ensure it's absolute and normalized
        file_path = file_record.file_path
        if not os.path.isabs(file_path):
            # Convert relative path to absolute from project root
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            file_path = os.path.normpath(os.path.join(project_root, file_path))
        
        if not os.path.exists(file_path):
            app.logger.error(f"PDF file not found: {file_path}")
            return jsonify({"error": f"PDF file missing from storage: {os.path.basename(file_path)}"}), 404
        
        item = session.query(Item).filter_by(id=item_id).first()
        filename = f"{item.title[:50]}.pdf" if item and item.title else f"paper_{item_id}.pdf"
        # Sanitize filename
        filename = "".join(c for c in filename if c.isalnum() or c in (' ', '-', '_', '.')).strip()
        
        return send_file(file_path, mimetype='application/pdf',
                         as_attachment=True, download_name=filename)
    except Exception as e:
        app.logger.error(f"Error downloading paper {item_id}: {str(e)}")
        return jsonify({"error": "Failed to download PDF"}), 500
    finally:
        session.close()

@app.route('/api/crawler/start', methods=['POST'])
def start_crawler():
    """Start fast direct crawler with optional target parameter."""
    from flask import request
    
    global crawler_process
    if crawler_process is not None and crawler_process.poll() is None:
        return jsonify({"status": "error", "message": "Crawler is already running."})
    
    # Get target count from request (default: 100, max: 250)
    data = request.get_json() or {}
    target_count = data.get('target', 100)
    target_count = min(max(int(target_count), 1), 250)
    
    python_exec = os.path.join(os.getcwd(), 'venv', 'Scripts', 'python.exe')
    if not os.path.exists(python_exec):
        python_exec = os.path.join(os.getcwd(), 'venv', 'bin', 'python')
    if not os.path.exists(python_exec):
        python_exec = "python"
        
    # Use the AGGRESSIVE crawler that searches up to 3000 pages
    script_path = os.path.join(os.getcwd(), 'crawl_aggressive.py')
    
    env = os.environ.copy()
    env['PYTHONPATH'] = os.getcwd()
    
    try:
        crawler_process = subprocess.Popen(
            [python_exec, script_path, '--target', str(target_count)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,  # Merge stderr into stdout so we see all output
            bufsize=0,
            env=env,
            universal_newlines=False
        )
        
        t = threading.Thread(target=crawler_monitor, args=(crawler_process,))
        t.daemon = True
        t.start()
        
        socketio.emit('crawl_status', {'status': 'running', 'target': target_count})
        return jsonify({"status": "success", "message": f"Fast crawler started with target: {target_count} papers"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/crawler/stop', methods=['POST'])
def stop_crawler():
    global crawler_process
    with crawler_lock:
        if crawler_process is not None and crawler_process.poll() is None:
            try:
                crawler_process.terminate()
                crawler_process.wait(timeout=5)
            except:
                try:
                    crawler_process.kill()
                except:
                    pass
            crawler_process = None
            socketio.emit('crawl_status', {'status': 'stopped'})
            return jsonify({"status": "success", "message": "Crawler stopped."})
    return jsonify({"status": "error", "message": "Crawler is not running."})

@app.route('/api/crawler/status', methods=['GET'])
def crawler_status():
    global crawler_process
    with crawler_lock:
        if crawler_process is not None and crawler_process.poll() is None:
            return jsonify({"status": "running"})
    return jsonify({"status": "stopped"})

@socketio.on('connect')
def handle_connect():
    """Send current crawler status when client connects."""
    global crawler_process
    with crawler_lock:
        if crawler_process is not None and crawler_process.poll() is None:
            socketio.emit('crawl_status', {'status': 'running'})
        else:
            socketio.emit('crawl_status', {'status': 'stopped'})

@socketio.on('disconnect')
def handle_disconnect():
    """Stop crawler when client disconnects (page closed/reloaded)."""
    global crawler_process
    with crawler_lock:
        if crawler_process is not None and crawler_process.poll() is None:
            try:
                crawler_process.terminate()
                crawler_process.wait(timeout=2)
            except:
                try:
                    crawler_process.kill()
                except:
                    pass
            crawler_process = None

if __name__ == '__main__':
    print("=" * 70)
    print("URAAS Dashboard Starting...")
    print("=" * 70)
    print(f"Dashboard URL: http://localhost:{config.DASHBOARD_PORT}")
    print("Press Ctrl+C to stop")
    print("=" * 70)
    socketio.run(app, host='0.0.0.0', port=config.DASHBOARD_PORT, debug=True)

# Define your item pipelines here
from uraas.database import SessionLocal, Item, Author, Collection, Community, File
from uraas.utils.unilag_classifier import classifier
from uraas.utils.pdf_downloader import pdf_downloader
from datetime import date

class DatabaseStoragePipeline:
    def open_spider(self, spider):
        self.session = SessionLocal()

    def close_spider(self, spider):
        try:
            self.session.close()
        except:
            pass

    def process_item(self, item, spider):
        try:
            # Validate item has required fields
            if not item.get('title'):
                spider.logger.error("Item missing title, skipping")
                return item
            
            # Classify the document using enhanced classifier
            try:
                text_corpus = f"{item.get('title', '')} {item.get('abstract', '')} {item.get('raw_affiliation', '')}"
                classifications = classifier.classify(text_corpus, threshold=0.5)
            except Exception as e:
                spider.logger.error(f"Classification error for '{item.get('title', 'Unknown')[:60]}': {str(e)}")
                classifications = []
            
            provenance = f"Harvested via URAAS Crawler - {date.today().isoformat()}"

            # Extract keywords for dc.subject
            try:
                text = f"{item.get('title', '')} {item.get('abstract', '')}".lower()
                academic_keywords = [
                    'sustainability', 'nigeria', 'health', 'engineering', 'energy', 
                    'policy', 'impact', 'education', 'lagos', 'technology', 'climate',
                    'development', 'innovation', 'research', 'analysis'
                ]
                tags = [kw for kw in academic_keywords if kw in text]
            except Exception as e:
                spider.logger.error(f"Keyword extraction error: {str(e)}")
                tags = []
            
            # Create Item with Dublin Core metadata
            try:
                doc = Item(
                    title=item.get('title'),
                    dc_title=item.get('title'),
                    dc_identifier_uri=item.get('doi') or item.get('url'),
                    dc_identifier_doi=item.get('doi'),
                    dc_description_provenance=provenance,
                    dc_rights=item.get('dc_rights', 'info:eu-repo/semantics/restrictedAccess'),
                    abstract=item.get('abstract'),
                    doi=item.get('doi') or None,
                    url=item.get('url') or 'https://openalex.org',
                    source_repository=item.get('source_repository'),
                    pdf_url=item.get('pdf_url')
                )
            except Exception as e:
                spider.logger.error(f"Error creating Item object: {str(e)}")
                raise
            
            # Log to stdout for dashboard
            try:
                safe_title = (item.get('title') or '').encode('ascii', errors='replace').decode('ascii')
                print(f"URAAS_DOWNLOAD: {safe_title}", flush=True)
            except Exception:
                print(f"URAAS_DOWNLOAD: [Title encoding error]", flush=True)
            
            # Create Authors
            authors = item.get('authors', [])
            unilag_staff = item.get('unilag_staff_authors', [])
            
            for author_name in authors:
                try:
                    if not author_name or not isinstance(author_name, str):
                        continue
                        
                    author_obj = self.session.query(Author).filter_by(
                        normalized_name=author_name.lower().strip()
                    ).first()
                    
                    if not author_obj:
                        author_obj = Author(
                            name=author_name, 
                            normalized_name=author_name.lower().strip()
                        )
                        self.session.add(author_obj)
                        
                    doc.authors.append(author_obj)
                except Exception as e:
                    spider.logger.error(f"Error processing author '{author_name}': {str(e)}")
                    continue
            
            self.session.add(doc)
            self.session.flush()  # Get doc.id
            
            # Map classified collections
            try:
                for community_name, collection_name, score in classifications[:3]:  # Top 3 classifications
                    try:
                        coll_obj = self.session.query(Collection).filter_by(name=collection_name).first()
                        if coll_obj and coll_obj not in doc.collections:
                            doc.collections.append(coll_obj)
                    except Exception as e:
                        spider.logger.error(f"Error adding collection '{collection_name}': {str(e)}")
                        continue
            except Exception as e:
                spider.logger.error(f"Error processing classifications: {str(e)}")
            
            # Download PDF if available
            if doc.pdf_url:
                try:
                    policy = item.get('suggested_access', 'Private')
                    
                    spider.logger.info(f"Downloading PDF from {doc.pdf_url}")
                    pdf_metadata = pdf_downloader.download_pdf(doc.pdf_url, doc.id)
                    
                    if pdf_metadata:
                        # Create local file record
                        bitstream = File(
                            item_id=doc.id,
                            file_path=pdf_metadata['file_path'],
                            sha256_hash=pdf_metadata['sha256_hash'],
                            access_policy=policy
                        )
                        self.session.add(bitstream)
                        spider.logger.info(
                            f"PDF downloaded: {pdf_metadata['file_path']} "
                            f"({pdf_metadata['file_size']} bytes, {pdf_metadata.get('page_count', '?')} pages)"
                        )
                    else:
                        spider.logger.warning(f"PDF download failed for {doc.pdf_url}")
                except Exception as e:
                    spider.logger.error(f"PDF download error for {doc.pdf_url}: {str(e)}")
            
            # High-impact publication alert
            try:
                source = (item.get('source_repository') or '').lower()
                title = (item.get('title') or '').lower()
                high_impact_journals = [
                    'nature', 'science', 'cell', 'lancet', 'pnas', 'jama', 
                    'bmj', 'nejm', 'plos', 'ieee'
                ]
                
                if any(journal in title or journal in source for journal in high_impact_journals):
                    print(
                        f"LIBRARIAN_ALERT: High-impact publication detected! "
                        f"'{item.get('title')[:100]}...' by {', '.join(str(s) for s in unilag_staff[:2])}",
                        flush=True
                    )
            except Exception as e:
                spider.logger.error(f"Error in high-impact detection: {str(e)}")
            
            self.session.commit()
            return item
            
        except Exception as e:
            spider.logger.error(f"Database storage error for '{item.get('title', 'Unknown')[:60]}': {str(e)}")
            try:
                self.session.rollback()
            except Exception:
                pass
            raise

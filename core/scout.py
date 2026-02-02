"""The Scout - Free Navigation Agent"""
import asyncio
import json
import logging
from typing import Dict, List, Set, Optional
from urllib.parse import urljoin, urlparse
from collections import defaultdict

from playwright.async_api import async_playwright, Page, Response, Request

from utils.dom_processor import (
    generate_structural_hash,
    clean_dom_for_llm,
    estimate_tokens,
    extract_form_data
)
from models.schemas import PageCluster, NetworkIntercept

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class Scout:
    """The Free Navigation Agent - Crawls websites and clusters pages"""
    
    def __init__(
        self,
        base_url: str,
        max_pages: int = 50,
        max_depth: int = 3,
        timeout: int = 30000,
        headless: bool = True
    ):
        self.base_url = base_url
        self.domain = urlparse(base_url).netloc
        self.max_pages = max_pages
        self.max_depth = max_depth
        self.timeout = timeout
        self.headless = headless
        
        self.visited_urls: Set[str] = set()
        self.url_queue: List[tuple] = [(base_url, 0)]
        self.clusters: Dict[str, PageCluster] = {}
        self.network_logs: Dict[str, List[NetworkIntercept]] = defaultdict(list)
        
        self.pages_crawled = 0
        self.pages_skipped_by_clustering = 0
        self.total_tokens_saved = 0
        
    async def crawl(self) -> Dict[str, PageCluster]:
        """Main crawling orchestrator"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (compatible; WebReverseBot/1.0)'
            )
            
            page = await context.new_page()
            page.on("response", lambda response: asyncio.create_task(self._handle_response(response)))
            
            logger.info(f"🚀 Scout launched. Target: {self.base_url}")
            
            try:
                while self.url_queue and self.pages_crawled < self.max_pages:
                    url, depth = self.url_queue.pop(0)
                    
                    if url in self.visited_urls or depth > self.max_depth:
                        continue
                    
                    await self._process_page(page, url, depth)
                    
            except KeyboardInterrupt:
                logger.warning("⚠️ Crawl interrupted")
            finally:
                await browser.close()
            
            self._calculate_statistics()
            logger.info(f"✅ Crawl complete")
            
            return self.clusters
    
    async def _process_page(self, page: Page, url: str, depth: int):
        """Visit a single page and analyze its structure"""
        try:
            logger.info(f"📄 [{self.pages_crawled + 1}/{self.max_pages}] Visiting: {url}")
            
            response = await page.goto(url, wait_until='domcontentloaded', timeout=self.timeout)
            
            if not response or response.status >= 400:
                logger.warning(f"⚠️ Failed to load {url}")
                return
            
            await page.wait_for_timeout(1000)
            html_content = await page.content()
            
            structural_hash = generate_structural_hash(html_content)
            is_new_cluster = structural_hash not in self.clusters
            
            if is_new_cluster:
                logger.info(f"   🆕 New cluster: {structural_hash[:8]}")
                cluster = await self._create_cluster(url, structural_hash, html_content)
                self.clusters[structural_hash] = cluster
            else:
                logger.info(f"   ♻️ Duplicate structure: {structural_hash[:8]}")
                cluster = self.clusters[structural_hash]
                cluster.total_pages_in_cluster += 1
                if len(cluster.sample_urls) < 5:
                    cluster.sample_urls.append(url)
                
                _, _, cleaned_size = clean_dom_for_llm(html_content)
                tokens_saved = estimate_tokens(str(cleaned_size))
                self.total_tokens_saved += tokens_saved
                self.pages_skipped_by_clustering += 1
            
            if url in self.network_logs:
                cluster.network_intercepts.extend(self.network_logs[url])
                del self.network_logs[url]
            
            self.visited_urls.add(url)
            self.pages_crawled += 1
            
            if depth < self.max_depth:
                await self._extract_links(page, url, depth)
            
        except Exception as e:
            logger.error(f"❌ Error processing {url}: {str(e)}")
    
    async def _create_cluster(self, url: str, structural_hash: str, html_content: str) -> PageCluster:
        """Create a new page cluster"""
        cleaned_html, raw_size, cleaned_size = clean_dom_for_llm(html_content)
        form_data = extract_form_data(html_content)
        
        cluster = PageCluster(
            cluster_id=structural_hash,
            representative_url=url,
            sample_urls=[url],
            total_pages_in_cluster=1,
            forms_found=form_data['total_forms'],
            cleaned_dom_tokens=estimate_tokens(cleaned_html),
            raw_dom_size=raw_size
        )
        
        return cluster
    
    async def _extract_links(self, page: Page, current_url: str, current_depth: int):
        """Extract and queue internal links"""
        try:
            links = await page.evaluate('''
                () => {
                    const anchors = Array.from(document.querySelectorAll('a[href]'));
                    return anchors.map(a => a.href);
                }
            ''')
            
            for link in links:
                absolute_url = urljoin(current_url, link)
                parsed = urlparse(absolute_url)
                
                if parsed.netloc == self.domain and absolute_url not in self.visited_urls:
                    clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
                    
                    if clean_url not in self.visited_urls:
                        self.url_queue.append((clean_url, current_depth + 1))
                        
        except Exception as e:
            logger.warning(f"⚠️ Failed to extract links: {str(e)}")
    
    async def _handle_response(self, response: Response):
        """Network interception handler"""
        try:
            content_type = response.headers.get('content-type', '')
            if 'application/json' not in content_type:
                return
            
            request: Request = response.request
            if request.resource_type not in ['xhr', 'fetch']:
                return
            
            url = response.url
            method = request.method
            status = response.status
            
            try:
                json_body = await response.json()
            except:
                json_body = None
            
            request_payload = None
            if method in ['POST', 'PUT', 'PATCH']:
                try:
                    request_payload = json.loads(request.post_data) if request.post_data else None
                except:
                    pass
            
            intercept = NetworkIntercept(
                url=url,
                method=method,
                status_code=status,
                payload_structure=request_payload,
                response_structure=json_body
            )
            
            current_page_url = request.frame.url if request.frame else url
            self.network_logs[current_page_url].append(intercept)
            
        except Exception as e:
            pass
    
    def _calculate_statistics(self):
        """Calculate final statistics"""
        logger.info(f"\n{'='*60}")
        logger.info(f"📊 CRAWL STATISTICS")
        logger.info(f"{'='*60}")
        logger.info(f"Total pages crawled: {self.pages_crawled}")
        logger.info(f"Unique clusters found: {len(self.clusters)}")
        logger.info(f"Pages skipped by clustering: {self.pages_skipped_by_clustering}")
        logger.info(f"Estimated tokens saved: {self.total_tokens_saved:,}")
        logger.info(f"{'='*60}\n")
    
    def get_statistics(self) -> dict:
        """Return statistics as dict"""
        return {
            'total_pages_crawled': self.pages_crawled,
            'unique_clusters_found': len(self.clusters),
            'pages_skipped_by_clustering': self.pages_skipped_by_clustering,
            'total_tokens_saved': self.total_tokens_saved,
            'clustering_efficiency': (self.pages_skipped_by_clustering / self.pages_crawled * 100) if self.pages_crawled > 0 else 0
        }

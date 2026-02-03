"""
Simple Scout - Just crawl pages, no complexity
"""
import asyncio
import logging
from typing import List
from urllib.parse import urljoin, urlparse

from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)


class SimplePage:
    """Represents a discovered page"""
    def __init__(self, url: str, html: str):
        self.url = url
        self.html = html
        self.hash = hash(self._get_structure(html))
    
    def _get_structure(self, html: str) -> str:
        """Simple structure identifier"""
        # Just use tag counts as structure
        import re
        tags = re.findall(r'<(\w+)', html.lower())
        return ''.join(sorted(set(tags)))


class SimpleScout:
    """Simple crawler - no auth, no complexity"""
    
    def __init__(self, base_url: str, max_pages: int = 25, headless: bool = True):
        self.base_url = base_url
        self.domain = urlparse(base_url).netloc
        self.max_pages = max_pages
        self.headless = headless
        
        self.visited = set()
        self.pages = []
        self.seen_structures = set()
    
    async def crawl(self) -> List[SimplePage]:
        """Crawl the site"""
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            page = await browser.new_page()
            
            # Start with homepage
            await self._visit(page, self.base_url)
            
            # Visit up to max_pages
            queue = [self.base_url]
            
            while queue and len(self.visited) < self.max_pages:
                url = queue.pop(0)
                
                if url in self.visited:
                    continue
                
                # Visit page
                page_data = await self._visit(page, url)
                
                if page_data:
                    # Only add if unique structure
                    if page_data.hash not in self.seen_structures:
                        self.pages.append(page_data)
                        self.seen_structures.add(page_data.hash)
                        logger.info(f"  ✓ New page type: {url}")
                    else:
                        logger.info(f"  ↻ Duplicate: {url}")
                    
                    # Get links
                    links = await self._get_links(page)
                    queue.extend(links[:10])  # Limit links per page
            
            await browser.close()
        
        return self.pages
    
    async def _visit(self, page, url: str) -> SimplePage:
        """Visit a single page"""
        
        if url in self.visited:
            return None
        
        try:
            logger.info(f"[{len(self.visited)+1}/{self.max_pages}] {url}")
            
            await page.goto(url, wait_until='domcontentloaded', timeout=20000)
            await page.wait_for_timeout(1000)
            
            html = await page.content()
            
            self.visited.add(url)
            
            return SimplePage(url, html)
            
        except Exception as e:
            logger.warning(f"  ✗ Failed: {str(e)[:50]}")
            return None
    
    async def _get_links(self, page) -> List[str]:
        """Get internal links"""
        try:
            links = await page.evaluate('''
                () => Array.from(document.querySelectorAll('a[href]')).map(a => a.href)
            ''')
            
            internal = []
            for link in links:
                parsed = urlparse(link)
                if parsed.netloc == self.domain:
                    clean = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
                    if clean not in self.visited:
                        internal.append(clean)
            
            return internal[:20]  # Max 20 links
        except:
            return []

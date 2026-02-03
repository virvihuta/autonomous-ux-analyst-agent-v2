"""
Simple Selector - Pick only important pages
"""
import logging
from typing import List
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class SimpleSelector:
    """Select important pages only"""
    
    def select_important(self, pages: List) -> List:
        """Pick the most important pages"""
        
        scored = []
        
        for page in pages:
            score = self._score_page(page.url)
            scored.append((score, page))
        
        # Sort by score
        scored.sort(key=lambda x: x[0], reverse=True)
        
        # Take top pages (max 10-12)
        selected = [p for score, p in scored[:12]]
        
        logger.info(f"\nSelected pages:")
        for score, page in scored[:12]:
            logger.info(f"  {score:3d} - {page.url}")
        
        return selected
    
    def _score_page(self, url: str) -> int:
        """Score a page by importance"""
        
        path = urlparse(url).path.lower()
        
        # Homepage
        if path in ['/', '', '/index']:
            return 100
        
        # Core pages
        if any(x in path for x in ['/sell', '/seller', '/become']):
            return 90
        if any(x in path for x in ['/login', '/signin', '/signup', '/register']):
            return 85
        if any(x in path for x in ['/product', '/item']):
            return 80
        if any(x in path for x in ['/cart', '/checkout']):
            return 80
        if any(x in path for x in ['/account', '/profile', '/dashboard']):
            return 75
        if any(x in path for x in ['/search', '/browse']):
            return 70
        if any(x in path for x in ['/about', '/how-it-works']):
            return 65
        if any(x in path for x in ['/contact', '/help', '/faq']):
            return 60
        if any(x in path for x in ['/category', '/collection']):
            return 55
        
        # Default
        return 30

"""
The Selector - Intelligently picks the 10-20 most important pages to analyze
Avoids wasting money on duplicate/unnecessary pages
"""
import logging
from typing import Dict, List, Set
from urllib.parse import urlparse, parse_qs
from models.schemas import PageCluster

logger = logging.getLogger(__name__)


class PageSelector:
    """
    Smart page selector that identifies the most important pages for replication.
    Avoids analyzing redundant pages (multiple products, categories, etc.)
    """
    
    def __init__(self, max_selected: int = 15):
        self.max_selected = max_selected
        self.selected_clusters = []
        self.selection_reasons = {}
    
    def select_important_pages(self, clusters: Dict[str, PageCluster]) -> List[PageCluster]:
        """
        Intelligently select 10-20 most important pages to analyze.
        
        Priority:
        1. Homepage
        2. Authentication (login, signup)
        3. Core workflows (checkout, cart, seller registration)
        4. Account/profile pages
        5. One example of each template type (1 product page, not 100)
        """
        
        logger.info(f"\n🎯 SMART PAGE SELECTION")
        logger.info(f"{'='*80}")
        logger.info(f"Total pages found: {sum(c.total_pages_in_cluster for c in clusters.values())}")
        logger.info(f"Unique templates: {len(clusters)}")
        logger.info(f"Selecting top {self.max_selected} most important pages...\n")
        
        scored_clusters = []
        
        for cluster_id, cluster in clusters.items():
            score, reason = self._score_cluster(cluster)
            scored_clusters.append((score, reason, cluster))
        
        # Sort by score (highest first)
        scored_clusters.sort(key=lambda x: x[0], reverse=True)
        
        # Select top N
        selected = []
        for score, reason, cluster in scored_clusters[:self.max_selected]:
            selected.append(cluster)
            self.selection_reasons[cluster.cluster_id] = reason
            logger.info(f"✓ Selected: {cluster.representative_url}")
            logger.info(f"  Reason: {reason} (score: {score})")
        
        # Log what we skipped
        skipped = len(clusters) - len(selected)
        if skipped > 0:
            logger.info(f"\n⚠️ Skipped {skipped} redundant page types:")
            for score, reason, cluster in scored_clusters[self.max_selected:]:
                logger.info(f"  ✗ {cluster.representative_url} ({cluster.total_pages_in_cluster} pages)")
        
        logger.info(f"\n{'='*80}")
        logger.info(f"📊 Selected {len(selected)} pages for detailed analysis")
        logger.info(f"💰 Cost savings: {skipped} page types not analyzed")
        logger.info(f"{'='*80}\n")
        
        return selected
    
    def _score_cluster(self, cluster: PageCluster) -> tuple:
        """
        Score a page cluster by importance.
        Returns (score, reason) tuple.
        
        Scoring:
        100+ = Critical (homepage, login, checkout)
        50-99 = Important (account, seller, search)
        20-49 = Useful (one example of each type)
        <20 = Redundant (skip these)
        """
        
        url = cluster.representative_url.lower()
        path = urlparse(url).path.lower()
        
        # CRITICAL PAGES (100+)
        
        # Homepage
        if path in ['/', '', '/index', '/home']:
            return (150, "Homepage - Main entry point")
        
        # Authentication
        if any(x in path for x in ['/login', '/signin', '/sign-in']):
            return (140, "Login page - User authentication")
        
        if any(x in path for x in ['/signup', '/register', '/sign-up']):
            return (140, "Signup page - User registration")
        
        if any(x in path for x in ['/forgot', '/reset-password', '/recover']):
            return (110, "Password recovery - Auth flow")
        
        # Checkout flow
        if '/checkout' in path:
            return (130, "Checkout page - Purchase flow")
        
        if '/cart' in path or '/basket' in path:
            return (130, "Cart page - Purchase flow")
        
        if '/payment' in path:
            return (125, "Payment page - Purchase flow")
        
        # IMPORTANT PAGES (50-99)
        
        # Seller/Business features
        if any(x in path for x in ['/sell', '/seller', '/become-seller', '/merchant']):
            return (120, "Seller registration - Core business feature")
        
        # Account/Profile
        if any(x in path for x in ['/account', '/profile', '/dashboard', '/settings']):
            return (100, "Account page - User management")
        
        if '/orders' in path:
            return (90, "Orders page - Transaction history")
        
        # Search
        if '/search' in path:
            return (80, "Search page - Discovery feature")
        
        # Contact/Support
        if any(x in path for x in ['/contact', '/support', '/help']):
            return (70, "Contact page - User support")
        
        # About/Info
        if any(x in path for x in ['/about', '/how-it-works', '/faq']):
            return (60, "Info page - Site information")
        
        # USEFUL (ONE EXAMPLE) (20-49)
        
        # Product pages - only need ONE example
        if any(x in path for x in ['/product', '/item', '/listing']):
            if cluster.total_pages_in_cluster > 1:
                return (45, "Product detail - Template example")
            else:
                return (45, "Product detail - Single page")
        
        # Category pages - only need ONE example  
        if any(x in path for x in ['/category', '/collection', '/browse']):
            if cluster.total_pages_in_cluster > 1:
                return (40, "Category page - Template example")
            else:
                return (40, "Category page - Single page")
        
        # Blog/Content - only need ONE example
        if any(x in path for x in ['/blog', '/article', '/post', '/news']):
            if cluster.total_pages_in_cluster > 1:
                return (35, "Blog post - Template example")
            else:
                return (35, "Blog post - Single page")
        
        # REDUNDANT - Skip these (0-19)
        
        # Specific product URLs (we already have the template)
        if any(x in path for x in ['/p/', '/products/', '/items/']):
            # Check if this looks like a specific product ID
            if any(char.isdigit() for char in path):
                return (5, "Specific product - Redundant")
        
        # Specific category pages
        if cluster.total_pages_in_cluster > 5:
            return (10, f"Repeated template - {cluster.total_pages_in_cluster} similar pages")
        
        # URLs with query parameters (usually filters/variations)
        if '?' in cluster.representative_url:
            return (8, "Filtered view - Redundant")
        
        # Admin/Internal pages
        if any(x in path for x in ['/admin', '/api', '/assets', '/static']):
            return (0, "System page - Not user-facing")
        
        # Default - moderate importance
        return (30, "Standard page - Possible unique functionality")
    
    def get_selection_summary(self) -> str:
        """Get a summary of why pages were selected"""
        summary = []
        summary.append("Selection Reasons:")
        for cluster_id, reason in self.selection_reasons.items():
            summary.append(f"  - {reason}")
        return "\n".join(summary)

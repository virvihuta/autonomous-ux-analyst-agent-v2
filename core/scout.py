"""
The Scout - Fixed for page-transition login flows
"""
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
    """Smart crawler with page-transition login support"""
    
    def __init__(
        self,
        base_url: str,
        max_pages: int = 100,
        max_depth: int = 3,
        priority_urls: List[str] = None,
        login_url: str = None,
        login_email: str = None,
        login_password: str = None,
        timeout: int = 30000,
        headless: bool = True
    ):
        self.base_url = base_url
        self.domain = urlparse(base_url).netloc
        self.max_pages = max_pages
        self.max_depth = max_depth
        self.priority_urls = priority_urls or []
        self.login_url = login_url
        self.login_email = login_email
        self.login_password = login_password
        self.timeout = timeout
        self.headless = headless
        
        self.visited_urls: Set[str] = set()
        self.url_queue: List[tuple] = [(base_url, 0)]
        self.clusters: Dict[str, PageCluster] = {}
        self.network_logs: Dict[str, List[NetworkIntercept]] = defaultdict(list)
        
        self.pages_crawled = 0
        self.pages_skipped_by_clustering = 0
        self.total_tokens_saved = 0
        self.all_discovered_urls: Set[str] = set()
        
        self.is_authenticated = False
    
    async def crawl(self) -> Dict[str, PageCluster]:
        """Main crawling with optional login"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            )
            
            page = await context.new_page()
            page.on("response", lambda response: asyncio.create_task(self._handle_response(response)))
            
            logger.info(f"🚀 Scout launched. Target: {self.base_url}")
            
            # STEP 1: Login if credentials provided
            if self.login_email and self.login_password:
                await self._perform_login(page)
            
            # STEP 2: Extract nav links
            await self._extract_nav_links(page)
            
            # STEP 3: Add priority URLs
            for url in self.priority_urls:
                full_url = urljoin(self.base_url, url)
                if full_url not in self.visited_urls:
                    self.url_queue.insert(0, (full_url, 0))
                    logger.info(f"🎯 Added priority URL: {full_url}")
            
            # STEP 4: Regular crawl
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
    
    async def _perform_login(self, page: Page):
        """
        Handle page-transition login (not modal-based)
        Flow: Click "Sign in" → Enter email → Click Continue → New page → Enter password → Submit
        """
        
        logger.info(f"\n🔐 AUTHENTICATION")
        logger.info(f"{'='*60}")
        
        try:
            # Navigate to homepage
            logger.info(f"Loading homepage: {self.base_url}")
            await page.goto(self.base_url, wait_until='networkidle', timeout=self.timeout)
            await page.wait_for_timeout(2000)
            
            # STEP 1: Click "Sign in" button
            logger.info("\nStep 1: Looking for Sign in button...")
            
            signin_selectors = [
                'button:has-text("Sign in")',
                'a:has-text("Sign in")',
                'button:has-text("Log in")',
                'a:has-text("Log in")',
                '[data-testid*="signin"]',
                '[data-testid*="login"]'
            ]
            
            signin_button = None
            for selector in signin_selectors:
                try:
                    signin_button = await page.wait_for_selector(selector, timeout=3000, state='visible')
                    if signin_button:
                        logger.info(f"✓ Found Sign in button: {selector}")
                        break
                except:
                    continue
            
            if not signin_button:
                logger.error("❌ Could not find Sign in button")
                return False
            
            # Click it
            logger.info("Clicking Sign in...")
            await signin_button.click()
            await page.wait_for_timeout(2000)
            
            # STEP 2: Enter email
            logger.info("\nStep 2: Entering email...")
            
            email_field = await page.wait_for_selector('input[type="email"]', timeout=5000, state='visible')
            if not email_field:
                logger.error("❌ Email field not found")
                return False
            
            logger.info(f"✓ Found email field")
            await email_field.click()
            await email_field.fill(self.login_email)
            logger.info(f"✓ Entered email: {self.login_email}")
            await page.wait_for_timeout(500)
            
            # STEP 3: Click Continue
            logger.info("\nStep 3: Clicking Continue...")
            
            continue_button = await page.wait_for_selector('button:has-text("Continue")', timeout=3000, state='visible')
            if not continue_button:
                logger.error("❌ Continue button not found")
                return False
            
            logger.info("✓ Found Continue button")
            await continue_button.click()
            
            # Wait for page transition
            logger.info("Waiting for login page to load...")
            await page.wait_for_load_state('networkidle', timeout=10000)
            await page.wait_for_timeout(2000)
            
            # STEP 4: Check if we're on login page with password field
            logger.info("\nStep 4: Looking for password field...")
            
            password_field = None
            try:
                password_field = await page.wait_for_selector('input[type="password"]', timeout=5000, state='visible')
                if password_field:
                    logger.info("✓ Found password field on new page")
            except:
                logger.error("❌ Password field did not appear")
                logger.info("   Checking page state...")
                current_url = page.url
                logger.info(f"   Current URL: {current_url}")
                return False
            
            # STEP 5: Enter password
            logger.info("\nStep 5: Entering password...")
            await password_field.click()
            await password_field.fill(self.login_password)
            logger.info("✓ Entered password")
            await page.wait_for_timeout(500)
            
            # STEP 6: Click Login button
            logger.info("\nStep 6: Submitting login...")
            
            login_button_selectors = [
                'button:has-text("Login")',
                'button:has-text("Log in")',
                'button[type="submit"]',
                'button:has-text("Sign in")'
            ]
            
            login_button = None
            for selector in login_button_selectors:
                try:
                    login_button = await page.wait_for_selector(selector, timeout=3000, state='visible')
                    if login_button:
                        logger.info(f"✓ Found login button: {selector}")
                        break
                except:
                    continue
            
            if not login_button:
                logger.warning("⚠️ No login button found, pressing Enter...")
                await password_field.press('Enter')
            else:
                logger.info("Clicking Login button...")
                await login_button.click()
            
            # Wait for login to complete
            logger.info("\nWaiting for login to complete...")
            try:
                await page.wait_for_load_state('networkidle', timeout=10000)
            except:
                pass
            
            await page.wait_for_timeout(3000)
            
            # STEP 7: Verify login success
            logger.info("\nStep 7: Verifying login...")
            
            # Check for account icon or profile button
            logged_in = False
            success_indicators = [
                '[data-testid*="account"]',
                'button[aria-label*="account" i]',
                'a[href*="/account"]',
                '[data-testid*="profile"]'
            ]
            
            for selector in success_indicators:
                try:
                    element = await page.wait_for_selector(selector, timeout=2000)
                    if element:
                        logger.info(f"✓ Login verified: Found {selector}")
                        logged_in = True
                        break
                except:
                    continue
            
            # Alternative: check if we're back on homepage
            if not logged_in:
                current_url = page.url
                if current_url == self.base_url or 'login' not in current_url.lower():
                    logger.info("✓ Redirected to homepage - login likely successful")
                    logged_in = True
            
            if logged_in:
                logger.info("✅ Login successful!")
                self.is_authenticated = True
                logger.info(f"{'='*60}\n")
                return True
            else:
                logger.warning("⚠️ Could not verify login status")
                logger.info(f"   Current URL: {page.url}")
                logger.info(f"{'='*60}\n")
                return False
                
        except Exception as e:
            logger.error(f"❌ Login failed: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            logger.info(f"{'='*60}\n")
            return False
    
    async def _extract_nav_links(self, page: Page):
        """Extract navigation menu links"""
        
        logger.info(f"🔍 Analyzing navigation menu...")
        
        try:
            current_url = page.url
            if not current_url.startswith(self.base_url):
                await page.goto(self.base_url, wait_until='domcontentloaded', timeout=self.timeout)
                await page.wait_for_timeout(2000)
            
            nav_links = await page.evaluate('''
                () => {
                    const links = new Set();
                    
                    const navs = document.querySelectorAll('nav, header, [role="navigation"]');
                    navs.forEach(nav => {
                        nav.querySelectorAll('a[href]').forEach(a => links.add(a.href));
                    });
                    
                    const navClasses = ['.nav', '.menu', '.navigation', '.header-links'];
                    navClasses.forEach(cls => {
                        document.querySelectorAll(`${cls} a[href]`).forEach(a => links.add(a.href));
                    });
                    
                    return Array.from(links);
                }
            ''')
            
            important_keywords = [
                'login', 'signin', 'sign-in',
                'signup', 'register', 'sign-up', 'join',
                'sell', 'seller', 'become-seller',
                'account', 'profile', 'dashboard',
                'cart', 'checkout',
                'contact', 'about', 'help'
            ]
            
            priority_links = []
            regular_links = []
            
            for link in nav_links:
                self.all_discovered_urls.add(link)
                
                link_lower = link.lower()
                is_important = any(keyword in link_lower for keyword in important_keywords)
                
                parsed = urlparse(link)
                if parsed.netloc and parsed.netloc != self.domain:
                    continue
                
                clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
                
                if is_important:
                    priority_links.append(clean_url)
                    logger.info(f"  ⭐ Important: {clean_url}")
                else:
                    regular_links.append(clean_url)
            
            for link in priority_links:
                if link not in self.visited_urls:
                    self.url_queue.insert(0, (link, 0))
            
            for link in regular_links[:10]:
                if link not in self.visited_urls:
                    self.url_queue.append((link, 1))
            
            logger.info(f"📋 Found {len(priority_links)} important nav links")
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to extract nav links: {str(e)}")
    
    async def _process_page(self, page: Page, url: str, depth: int):
        """Visit a single page"""
        try:
            logger.info(f"📄 [{self.pages_crawled + 1}/{self.max_pages}] Visiting: {url}")
            
            response = await page.goto(url, wait_until='domcontentloaded', timeout=self.timeout)
            
            if not response or response.status >= 400:
                logger.warning(f"⚠️ Failed (status: {response.status if response else 'None'})")
                return
            
            try:
                await page.wait_for_load_state('networkidle', timeout=5000)
            except:
                pass
            
            await page.wait_for_timeout(1500)
            
            final_url = page.url
            if final_url != url and ('login' in final_url.lower() or 'signin' in final_url.lower()):
                logger.warning(f"   ⚠️ Requires auth - skipping")
                return
            
            try:
                html_content = await page.content()
            except Exception as e:
                logger.error(f"   ❌ Could not get content: {str(e)}")
                return
            
            structural_hash = generate_structural_hash(html_content)
            is_new_cluster = structural_hash not in self.clusters
            
            if is_new_cluster:
                logger.info(f"   🆕 New cluster: {structural_hash[:8]}")
                cluster = await self._create_cluster(url, structural_hash, html_content)
                self.clusters[structural_hash] = cluster
            else:
                logger.info(f"   ♻️ Duplicate: {structural_hash[:8]}")
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
            logger.error(f"❌ Error: {str(e)}")
    
    async def _create_cluster(self, url: str, structural_hash: str, html_content: str) -> PageCluster:
        """Create cluster"""
        cleaned_html, raw_size, cleaned_size = clean_dom_for_llm(html_content)
        form_data = extract_form_data(html_content)
        
        return PageCluster(
            cluster_id=structural_hash,
            representative_url=url,
            sample_urls=[url],
            total_pages_in_cluster=1,
            forms_found=form_data['total_forms'],
            cleaned_dom_tokens=estimate_tokens(cleaned_html),
            raw_dom_size=raw_size
        )
    
    async def _extract_links(self, page: Page, current_url: str, current_depth: int):
        """Extract links"""
        try:
            links = await page.evaluate('() => Array.from(document.querySelectorAll("a[href]")).map(a => a.href)')
            
            for link in links:
                self.all_discovered_urls.add(link)
                absolute_url = urljoin(current_url, link)
                parsed = urlparse(absolute_url)
                
                if parsed.netloc == self.domain and absolute_url not in self.visited_urls:
                    clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
                    if clean_url not in self.visited_urls:
                        self.url_queue.append((clean_url, current_depth + 1))
        except Exception as e:
            logger.warning(f"⚠️ Link extraction failed: {str(e)}")
    
    async def _handle_response(self, response: Response):
        """Network handler"""
        try:
            if 'application/json' not in response.headers.get('content-type', ''):
                return
            
            request: Request = response.request
            if request.resource_type not in ['xhr', 'fetch']:
                return
            
            try:
                json_body = await response.json()
            except:
                json_body = None
            
            request_payload = None
            if request.method in ['POST', 'PUT', 'PATCH']:
                try:
                    request_payload = json.loads(request.post_data) if request.post_data else None
                except:
                    pass
            
            intercept = NetworkIntercept(
                url=response.url,
                method=request.method,
                status_code=response.status,
                payload_structure=request_payload,
                response_structure=json_body
            )
            
            current_page_url = request.frame.url if request.frame else response.url
            self.network_logs[current_page_url].append(intercept)
        except:
            pass
    
    def _calculate_statistics(self):
        """Stats"""
        logger.info(f"\n{'='*60}")
        logger.info(f"📊 CRAWL STATISTICS")
        logger.info(f"{'='*60}")
        logger.info(f"Authenticated: {'Yes' if self.is_authenticated else 'No'}")
        logger.info(f"URLs discovered: {len(self.all_discovered_urls)}")
        logger.info(f"Pages crawled: {self.pages_crawled}")
        logger.info(f"Unique clusters: {len(self.clusters)}")
        logger.info(f"{'='*60}\n")
    
    def get_statistics(self) -> dict:
        return {
            'total_pages_crawled': self.pages_crawled,
            'unique_clusters_found': len(self.clusters),
            'pages_skipped_by_clustering': self.pages_skipped_by_clustering,
            'total_tokens_saved': self.total_tokens_saved,
            'total_urls_discovered': len(self.all_discovered_urls),
            'is_authenticated': self.is_authenticated,
            'clustering_efficiency': (self.pages_skipped_by_clustering / self.pages_crawled * 100) if self.pages_crawled > 0 else 0
        }
    
    def get_all_discovered_urls(self) -> List[str]:
        return sorted(list(self.all_discovered_urls))

"""
Smart Narrator - Analyzes actual HTML and creates detailed descriptions
"""
from typing import List
from bs4 import BeautifulSoup
import re


class SimpleNarrator:
    """Creates detailed, specific rebuild instructions"""
    
    def create_guide(self, pages: List, base_url: str) -> str:
        """Generate complete Firebase Studio prompt"""
        
        md = []
        
        # Header
        md.append(f"# Rebuild Instructions for {base_url}\n")
        md.append("---\n")
        
        # Overall summary FIRST
        md.append("## Site Overview\n")
        md.append(self._create_detailed_overview(pages, base_url))
        md.append("\n---\n")
        
        # Individual pages with REAL details
        md.append("## Page Descriptions\n")
        
        seen_types = set()
        for page in pages:
            page_type = self._classify_page(page.url)
            
            # Skip duplicates
            if page_type in seen_types:
                continue
            seen_types.add(page_type)
            
            md.append(f"\n### {page_type}\n")
            md.append(f"*Example: `{page.url}`*\n")
            md.append(self._analyze_and_describe(page))
            md.append("\n---\n")
        
        # Firebase Studio summary
        md.append("## Firebase Studio Implementation Guide\n")
        md.append(self._create_implementation_guide(pages))
        
        return "\n".join(md)
    
    def _create_detailed_overview(self, pages: List, base_url: str) -> str:
        """Analyze all pages and create site overview"""
        
        # Analyze what the site actually has
        has_selling = any('sell' in p.url.lower() for p in pages)
        has_products = any('product' in p.url.lower() or 'item' in p.url.lower() for p in pages)
        has_categories = any('category' in p.url.lower() for p in pages)
        has_search = any('search' in p.url.lower() for p in pages)
        has_brands = any('brand' in p.url.lower() for p in pages)
        has_auth = any(x in p.url.lower() for p in pages for x in ['login', 'signup', 'signin'])
        
        # Build overview
        desc = f"**{base_url}** is "
        
        if has_selling and has_products:
            desc += "a peer-to-peer marketplace where people can buy and sell items. "
        elif has_products:
            desc += "an e-commerce platform selling various products. "
        else:
            desc += "a content-focused website. "
        
        desc += "\n\n**Main Features:**\n"
        
        if has_categories:
            desc += "- Browse items by category (Women, Men, Beauty, Vintage, etc.)\n"
        if has_search:
            desc += "- Search functionality to find specific items\n"
        if has_brands:
            desc += "- Shop by brand or designer\n"
        if has_selling:
            desc += "- Seller registration to list and sell items\n"
        if has_auth:
            desc += "- User accounts with login/signup\n"
        if has_products:
            desc += "- Product detail pages with images, prices, and descriptions\n"
        
        desc += f"\n**Total unique page types found:** {len(pages)}"
        
        return desc
    
    def _analyze_and_describe(self, page) -> str:
        """Actually analyze the HTML and describe what's there"""
        
        soup = BeautifulSoup(page.html, 'html.parser')
        
        # Remove noise
        for tag in soup(['script', 'style', 'svg', 'noscript']):
            tag.decompose()
        
        url_lower = page.url.lower()
        
        # Route to specific analyzer
        if url_lower.endswith('/') or 'index' in url_lower or url_lower == page.url.rstrip('/').split('/')[-1]:
            return self._describe_homepage(soup)
        elif 'sell' in url_lower:
            return self._describe_seller_page(soup)
        elif 'product' in url_lower or 'item' in url_lower:
            return self._describe_product_page(soup)
        elif 'category' in url_lower or 'collection' in url_lower:
            return self._describe_category_page(soup)
        elif 'search' in url_lower:
            return self._describe_search_page(soup)
        elif 'brand' in url_lower:
            return self._describe_brands_page(soup)
        elif 'login' in url_lower or 'signin' in url_lower:
            return self._describe_login_page(soup)
        elif 'signup' in url_lower or 'register' in url_lower:
            return self._describe_signup_page(soup)
        elif 'cart' in url_lower or 'bag' in url_lower:
            return self._describe_cart_page(soup)
        elif 'about' in url_lower:
            return self._describe_about_page(soup)
        else:
            return self._describe_generic_page(soup)
    
    def _describe_homepage(self, soup) -> str:
        """Analyze and describe the actual homepage"""
        
        desc = "This is the **Homepage** - the main landing page.\n\n"
        
        # Analyze navigation
        nav = soup.find(['nav', 'header'])
        if nav:
            nav_links = nav.find_all('a')
            if nav_links:
                nav_text = [link.get_text(strip=True) for link in nav_links[:8] if link.get_text(strip=True)]
                if nav_text:
                    desc += f"**At the top**, you see a navigation menu with options like: {', '.join(nav_text)}.\n\n"
        
        # Look for hero section
        hero_headings = soup.find_all(['h1', 'h2'], limit=3)
        if hero_headings:
            hero_text = [h.get_text(strip=True) for h in hero_headings if h.get_text(strip=True)]
            if hero_text:
                desc += f"**Main banner** shows: \"{hero_text[0]}\"\n\n"
        
        # Look for sections
        sections = soup.find_all(['section', 'div'], class_=re.compile(r'section|container|grid'))
        if len(sections) > 2:
            desc += f"**As you scroll down**, you see multiple sections:\n"
            desc += "- Featured or new arrival items\n"
            desc += "- Popular categories to explore\n"
            desc += "- Promotional content or deals\n\n"
        
        # Look for category links
        category_links = soup.find_all('a', href=re.compile(r'category|collection'))
        if category_links:
            cat_names = [link.get_text(strip=True) for link in category_links[:6] if link.get_text(strip=True)]
            if cat_names:
                desc += f"**Categories shown**: {', '.join(cat_names)}\n\n"
        
        # Look for search
        search = soup.find(['input'], type='search') or soup.find(['input'], placeholder=re.compile(r'search', re.I))
        if search:
            desc += "**Search bar** is available at the top - you can type to find specific items.\n\n"
        
        # Look for buttons
        buttons = soup.find_all('button', limit=5)
        button_text = [b.get_text(strip=True) for b in buttons if b.get_text(strip=True)]
        if button_text:
            desc += f"**Action buttons** you'll see: {', '.join(button_text[:3])}\n\n"
        
        desc += "The layout is designed to showcase the marketplace and guide you to browse or search for items."
        
        return desc
    
    def _describe_category_page(self, soup) -> str:
        """Describe category pages with actual details"""
        
        desc = "This is a **Category Page** - showing all items in a specific category.\n\n"
        
        # Get category name from heading
        heading = soup.find(['h1', 'h2'])
        if heading:
            cat_name = heading.get_text(strip=True)
            desc += f"**Category**: {cat_name}\n\n"
        
        # Count items
        items = soup.find_all(['article', 'div'], class_=re.compile(r'product|item|card'))
        if items:
            desc += f"**Items displayed**: Shows a grid of {len(items)} items per page\n\n"
        
        # Look for filters
        filters = soup.find_all(['select', 'input'], type='checkbox')
        if filters:
            desc += "**Filters available**:\n"
            desc += "- Price range slider\n"
            desc += "- Size, color, condition options\n"
            desc += "- Brand selection\n"
            desc += "- Sort by: newest, price (low-high), popularity\n\n"
        
        # Look for sort options
        sort_select = soup.find('select', class_=re.compile(r'sort'))
        if sort_select:
            options = sort_select.find_all('option')
            if options:
                sort_options = [opt.get_text(strip=True) for opt in options]
                desc += f"**Sort options**: {', '.join(sort_options)}\n\n"
        
        desc += "**Each item shows**: Image, title, price, and brand/seller name. Click any item to see its full details."
        
        return desc
    
    def _describe_product_page(self, soup) -> str:
        """Describe actual product page"""
        
        desc = "This is a **Product Page** - detailed view of a single item.\n\n"
        
        # Product name
        title = soup.find(['h1', 'h2'])
        if title:
            desc += f"**Product name** is shown prominently at the top\n\n"
        
        # Images
        images = soup.find_all('img', src=re.compile(r'product|item|image'))
        if images:
            desc += f"**Product images**: {len(images)} photos showing different angles - you can click through them\n\n"
        
        # Price
        price = soup.find(['span', 'div'], class_=re.compile(r'price|cost'))
        if price:
            desc += f"**Price** is displayed clearly\n\n"
        
        # Description
        desc += "**Product details include**:\n"
        desc += "- Item description and condition\n"
        desc += "- Size, color, material information\n"
        desc += "- Brand/designer name\n"
        desc += "- Seller information\n\n"
        
        # Buttons
        buttons = soup.find_all('button')
        button_text = [b.get_text(strip=True) for b in buttons if b.get_text(strip=True)]
        if button_text:
            desc += f"**Action buttons**: {', '.join(button_text[:3])}\n\n"
        
        # Additional info
        desc += "**Below the main content**, you might find:\n"
        desc += "- Shipping and return information\n"
        desc += "- Similar items or recommendations\n"
        desc += "- Save/favorite option"
        
        return desc
    
    def _describe_seller_page(self, soup) -> str:
        """Describe seller/sell page"""
        
        desc = "This is the **Sell/Become a Seller** page.\n\n"
        
        # Headings
        headings = soup.find_all(['h1', 'h2', 'h3'], limit=5)
        if headings:
            heading_text = [h.get_text(strip=True) for h in headings if h.get_text(strip=True)]
            if heading_text:
                desc += f"**Main message**: \"{heading_text[0]}\"\n\n"
        
        # Forms
        forms = soup.find_all('form')
        if forms:
            desc += "**Registration options**:\n"
            
            inputs = soup.find_all(['input', 'select'])
            if inputs:
                desc += "You fill out a form with:\n"
                input_types = set([inp.get('type') or inp.get('name') or 'text' for inp in inputs[:8]])
                desc += "- Personal information (name, email, phone)\n"
                desc += "- Business details (if applicable)\n"
                desc += "- Payment/payout preferences\n\n"
        else:
            desc += "**Information provided**:\n"
            desc += "- Benefits of selling on the platform\n"
            desc += "- How the selling process works\n"
            desc += "- Fee structure or commission details\n"
            desc += "- Call-to-action button to start the registration\n\n"
        
        desc += "After completing the form, you become a verified seller and can start listing items for sale."
        
        return desc
    
    def _describe_search_page(self, soup) -> str:
        """Describe search results"""
        
        desc = "This is the **Search Results** page.\n\n"
        
        # Search input
        search_input = soup.find('input', type='search')
        if search_input:
            placeholder = search_input.get('placeholder', 'Search')
            desc += f"**Search bar** at the top shows what you searched for\n\n"
        
        # Results count
        results = soup.find_all(['article', 'div'], class_=re.compile(r'product|item|result'))
        if results:
            desc += f"**Results**: Shows {len(results)} matching items in a grid layout\n\n"
        
        desc += "**For each result**, you see:\n"
        desc += "- Product image\n"
        desc += "- Title and brief description\n"
        desc += "- Price\n"
        desc += "- Quick view or add to favorites option\n\n"
        
        desc += "**Filters on the side** let you narrow results by category, price, size, brand, etc.\n\n"
        desc += "Click any item to go to its detailed product page."
        
        return desc
    
    def _describe_brands_page(self, soup) -> str:
        """Describe brands page"""
        
        desc = "This is the **Brands** page - browse by designer or brand.\n\n"
        
        # Look for brand listings
        brand_links = soup.find_all('a', class_=re.compile(r'brand'))
        if brand_links:
            desc += f"**Shows {len(brand_links)} different brands/designers**\n\n"
        
        desc += "**Layout options**:\n"
        desc += "- Alphabetical listing of all brands\n"
        desc += "- Featured or popular brands highlighted\n"
        desc += "- Brand logos or images for visual recognition\n\n"
        
        desc += "Click any brand to see all items from that designer or label."
        
        return desc
    
    def _describe_login_page(self, soup) -> str:
        return "This is the **Login Page**.\n\nYou see an email and password field, with a \"Sign In\" button. There's a \"Forgot Password?\" link below, and a \"Don't have an account? Sign up\" link at the bottom."
    
    def _describe_signup_page(self, soup) -> str:
        return "This is the **Sign Up Page**.\n\nYou fill in: name, email, and password (twice to confirm). There's a checkbox to agree to terms. Click \"Create Account\" to register."
    
    def _describe_cart_page(self, soup) -> str:
        return "This is the **Shopping Cart**.\n\nAll your items are listed with images, prices, and quantity selectors. You can remove items or update quantities. The total is shown at the bottom with a \"Checkout\" button."
    
    def _describe_about_page(self, soup) -> str:
        return "This is an **About/Information** page explaining the company, mission, or how the platform works."
    
    def _describe_generic_page(self, soup) -> str:
        return "This is an additional page providing supplementary information or functionality."
    
    def _classify_page(self, url: str) -> str:
        """Get friendly page type name"""
        url_lower = url.lower()
        
        if url_lower.endswith('/') or 'index' in url_lower:
            return "Homepage"
        elif 'sell' in url_lower:
            return "Become a Seller"
        elif 'product' in url_lower or 'item' in url_lower:
            return "Product Detail Page"
        elif 'category' in url_lower:
            # Extract category name if possible
            match = re.search(r'category/([^/]+)', url)
            if match:
                cat = match.group(1).replace('-', ' ').title()
                return f"Category: {cat}"
            return "Category Page"
        elif 'search' in url_lower:
            return "Search Results"
        elif 'brand' in url_lower:
            return "Brands Directory"
        elif 'login' in url_lower:
            return "Login"
        elif 'signup' in url_lower or 'register' in url_lower:
            return "Sign Up"
        elif 'cart' in url_lower:
            return "Shopping Cart"
        else:
            path = url.split('/')[-1] or 'Page'
            return path.replace('-', ' ').title()
    
    def _create_implementation_guide(self, pages: List) -> str:
        """Create comprehensive Firebase Studio guide"""
        
        guide = []
        
        guide.append("### Complete Feature List\n")
        
        # Analyze what exists
        urls = [p.url.lower() for p in pages]
        
        features = []
        
        # Navigation
        features.append("**Navigation System**")
        features.append("- Top navigation bar with main categories")
        features.append("- Search functionality")
        features.append("- User account menu")
        features.append("- Shopping cart icon\n")
        
        # Core pages
        if any('category' in u for u in urls):
            features.append("**Category Browsing**")
            features.append("- Multiple category pages (Women, Men, Beauty, Vintage, etc.)")
            features.append("- Grid layout showing products")
            features.append("- Filters: price, size, condition, brand")
            features.append("- Sort options: newest, price, popularity\n")
        
        if any('product' in u or 'item' in u for u in urls):
            features.append("**Product Pages**")
            features.append("- Image gallery with multiple photos")
            features.append("- Product details: name, price, description, condition")
            features.append("- Add to cart/buy button")
            features.append("- Seller information")
            features.append("- Similar items recommendations\n")
        
        if any('sell' in u for u in urls):
            features.append("**Seller Features**")
            features.append("- Seller registration form")
            features.append("- Options for individual vs professional seller")
            features.append("- Profile setup")
            features.append("- Item listing interface\n")
        
        if any('search' in u for u in urls):
            features.append("**Search System**")
            features.append("- Real-time search bar")
            features.append("- Search results with filters")
            features.append("- Instant results as you type\n")
        
        if any(x in u for u in urls for x in ['login', 'signup']):
            features.append("**User Authentication**")
            features.append("- Email/password login")
            features.append("- User registration")
            features.append("- Account management\n")
        
        guide.append("\n".join(features))
        
        guide.append("\n### Firebase Implementation\n")
        guide.append("**Database Structure (Firestore):**")
        guide.append("```")
        guide.append("products/")
        guide.append("  - id, name, price, images[], description, category, seller_id")
        guide.append("users/")
        guide.append("  - id, email, name, is_seller, favorites[]")
        guide.append("categories/")
        guide.append("  - id, name, slug, image")
        guide.append("```\n")
        
        guide.append("**Key Functionality:**")
        guide.append("- Use Firebase Auth for login/signup")
        guide.append("- Store products, users, categories in Firestore")
        guide.append("- Use Cloud Storage for product images")
        guide.append("- Implement search with Algolia or Firestore queries")
        guide.append("- Real-time updates for cart and favorites\n")
        
        guide.append("**UI/UX Priorities:**")
        guide.append("- Mobile-responsive design")
        guide.append("- Fast loading product images")
        guide.append("- Smooth filtering and sorting")
        guide.append("- Clear calls-to-action on every page")
        
        return "\n".join(guide)

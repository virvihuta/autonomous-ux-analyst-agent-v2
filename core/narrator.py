"""
The Narrator - Explains websites in plain English, like showing it to a friend
NO technical jargon, just simple descriptions of what you see and do
"""
import logging
from typing import List, Dict
from models.schemas import PageCluster, RebuildBlueprint

logger = logging.getLogger(__name__)


class Narrator:
    """
    Converts technical analysis into friendly, natural language.
    Explains websites like you're showing them to a friend.
    """
    
    def __init__(self):
        self.sections = []
    
    def generate_reconstruction_guide(self, blueprint: RebuildBlueprint) -> str:
        """Generate a friendly Markdown guide"""
        
        md = []
        
        # Header
        md.append(f"# How {blueprint.base_url} Works\n")
        md.append(f"This website has {blueprint.unique_clusters_found} different types of pages. ")
        md.append(f"Here's what you'll find when you visit:\n")
        
        md.append("---\n")
        
        # Describe each page type
        for i, cluster in enumerate(blueprint.clusters, 1):
            md.append(self._describe_page_naturally(cluster))
            md.append("\n---\n")
        
        return "\n".join(md)
    
    def _describe_page_naturally(self, cluster: PageCluster) -> str:
        """Describe a page like showing it to a friend"""
        
        md = []
        
        # Determine page name from URL or type
        page_name = self._get_friendly_page_name(cluster)
        
        md.append(f"## {page_name}\n")
        
        # Add example if we have it
        if cluster.sample_urls:
            example_url = cluster.representative_url.split('?')[0]  # Remove query params
            md.append(f"*Example: `{example_url}`*\n")
        
        # Generate the natural description
        description = self._create_natural_description(cluster)
        md.append(description)
        
        return "\n".join(md)
    
    def _get_friendly_page_name(self, cluster: PageCluster) -> str:
        """Convert technical page type to friendly name"""
        
        page_type = cluster.page_type.lower()
        url = cluster.representative_url.lower()
        
        # Try to infer from URL first
        if '/login' in url or '/signin' in url:
            return "Login Page"
        elif '/signup' in url or '/register' in url:
            return "Sign Up Page"
        elif '/cart' in url or '/basket' in url:
            return "Shopping Cart"
        elif '/checkout' in url:
            return "Checkout Page"
        elif '/product' in url or '/item' in url:
            return "Product Page"
        elif '/category' in url or '/collection' in url:
            return "Category Page"
        elif '/search' in url:
            return "Search Results"
        elif '/account' in url or '/profile' in url:
            return "Account Page"
        elif '/about' in url:
            return "About Page"
        elif '/contact' in url:
            return "Contact Page"
        elif url.endswith('/') or url.endswith('.com'):
            return "Homepage"
        
        # Fall back to analyzing page type
        if 'login' in page_type or 'auth' in page_type:
            return "Login Page"
        elif 'product' in page_type:
            return "Product Page"
        elif 'cart' in page_type:
            return "Shopping Cart"
        elif 'checkout' in page_type:
            return "Checkout Page"
        elif 'dashboard' in page_type:
            return "Dashboard"
        elif 'form' in page_type:
            return "Form Page"
        else:
            # Use the URL path as the name
            parts = cluster.representative_url.split('/')
            for part in reversed(parts):
                if part and part not in ['http:', 'https:', '']:
                    return part.replace('-', ' ').replace('_', ' ').title() + " Page"
            return "Main Page"
    
    def _create_natural_description(self, cluster: PageCluster) -> str:
        """Create a natural, friendly description"""
        
        page_type = cluster.page_type.lower()
        url = cluster.representative_url.lower()
        page_name = self._get_friendly_page_name(cluster)
        
        # Pattern matching for common page types
        if 'login' in page_type or 'login' in url:
            return self._describe_login_page(cluster)
        
        elif 'signup' in url or 'register' in url:
            return self._describe_signup_page(cluster)
        
        elif 'product' in page_type or '/product' in url:
            return self._describe_product_page(cluster)
        
        elif 'cart' in page_type or 'cart' in url:
            return self._describe_cart_page(cluster)
        
        elif 'checkout' in page_type or 'checkout' in url:
            return self._describe_checkout_page(cluster)
        
        elif 'dashboard' in page_type or 'dashboard' in url:
            return self._describe_dashboard_page(cluster)
        
        elif 'search' in url:
            return self._describe_search_page(cluster)
        
        elif 'category' in url or 'collection' in url:
            return self._describe_category_page(cluster)
        
        elif url.endswith('/') or url.endswith('.com'):
            return self._describe_homepage(cluster)
        
        else:
            return self._describe_generic_page(cluster, page_name)
    
    def _describe_login_page(self, cluster: PageCluster) -> str:
        """Describe a login page naturally"""
        
        desc = f"This is the {self._get_friendly_page_name(cluster)}. "
        desc += "When you arrive here, you see a simple form asking for your login details. "
        desc += "There are two boxes: one for your email or username, and another for your password. "
        
        if cluster.buttons_found > 0:
            desc += "Below that, there's a button to sign in. "
        
        desc += "If you click the sign in button, the site checks your information. "
        desc += "If everything's correct, it takes you to your account or the page you were trying to visit. "
        desc += "If something's wrong, you'll see a message letting you know. "
        
        desc += "\n\nYou might also see a \"Forgot Password?\" link that takes you to a page where you can reset it. "
        desc += "Some sites also have a \"Remember Me\" checkbox that keeps you logged in next time."
        
        return desc
    
    def _describe_signup_page(self, cluster: PageCluster) -> str:
        """Describe a signup page naturally"""
        
        desc = f"This is the {self._get_friendly_page_name(cluster)}. "
        desc += "This is where you create a new account. You'll see a form asking for basic information like your name, email, and a password you want to use. "
        
        if cluster.inputs_found > 0:
            desc += f"There are several fields to fill out. "
        
        desc += "After you fill everything in, you click the sign up button. "
        desc += "The site then creates your account and usually sends you a confirmation email. "
        desc += "Once you're signed up, it takes you either to your new account page or back to where you started."
        
        return desc
    
    def _describe_product_page(self, cluster: PageCluster) -> str:
        """Describe a product page naturally"""
        
        desc = f"This is a {self._get_friendly_page_name(cluster)}. "
        desc += "At the top, you see the product name and price prominently displayed. "
        desc += "There are usually several photos showing the product from different angles - you can click through these or swipe if you're on mobile. "
        
        desc += "\n\nAs you scroll down, you see a detailed description of what you're looking at. "
        
        if cluster.forms_found > 0 or cluster.buttons_found > 0:
            desc += "There are options to choose from - things like size, color, or quantity. "
            desc += "You select what you want, then click an \"Add to Cart\" button. "
            desc += "When you do that, the item gets added to your cart and you can either keep shopping or go checkout. "
        
        desc += "\n\nFurther down the page, you might see customer reviews, related products, or more details about shipping and returns. "
        desc += "If you want to buy it, you click \"Add to Cart\" and it saves the item for checkout later."
        
        return desc
    
    def _describe_cart_page(self, cluster: PageCluster) -> str:
        """Describe a shopping cart naturally"""
        
        desc = f"This is the {self._get_friendly_page_name(cluster)}. "
        desc += "Here you see everything you've added that you want to buy. Each item shows with a small picture, the name, price, and quantity. "
        
        desc += "\n\nFor each item, you can change how many you want or remove it completely if you change your mind. "
        desc += "As you make changes, the total price updates automatically. "
        
        desc += "\n\nAt the bottom or side, you see the subtotal for all your items. "
        desc += "There's usually a breakdown showing the item costs, shipping, taxes, and the final total. "
        
        if cluster.buttons_found > 0:
            desc += "When you're ready, you click a \"Checkout\" or \"Proceed to Payment\" button that takes you to enter your shipping and payment information."
        
        return desc
    
    def _describe_checkout_page(self, cluster: PageCluster) -> str:
        """Describe a checkout page naturally"""
        
        desc = f"This is the {self._get_friendly_page_name(cluster)}. "
        desc += "This is where you complete your purchase. "
        
        if cluster.forms_found > 0:
            desc += "You'll see forms asking for your shipping address, payment information, and sometimes billing address if it's different. "
        
        desc += "\n\nThe page usually shows a summary of what you're buying on one side, with the total cost clearly visible. "
        desc += "You enter your information step by step - first your shipping details, then your payment method. "
        
        desc += "\n\nBefore you finish, you review everything one more time: what you're buying, where it's going, and how much it costs. "
        desc += "When everything looks good, you click a final \"Place Order\" or \"Complete Purchase\" button. "
        desc += "After that, you get a confirmation showing your order was successful, and usually an email is sent to you as well."
        
        return desc
    
    def _describe_dashboard_page(self, cluster: PageCluster) -> str:
        """Describe a dashboard naturally"""
        
        desc = f"This is the {self._get_friendly_page_name(cluster)}. "
        desc += "When you log in, this is your main control center. "
        desc += "At the top, you usually see a welcome message with your name. "
        
        desc += "\n\nThe page is organized into sections showing different information at a glance. "
        desc += "You might see recent activity, quick stats, or summaries of important things. "
        
        desc += "\n\nThere's typically a menu or navigation bar that lets you access different areas of your account - like settings, orders, profile, or other features. "
        desc += "If you click on any of these sections, it takes you to that specific page. "
        
        desc += "\n\nEverything is designed to give you a quick overview and easy access to the things you use most."
        
        return desc
    
    def _describe_search_page(self, cluster: PageCluster) -> str:
        """Describe a search results page naturally"""
        
        desc = f"This is the {self._get_friendly_page_name(cluster)}. "
        desc += "At the top, you see the search box where you typed what you were looking for. "
        desc += "Below that, you see all the results that match your search. "
        
        desc += "\n\nEach result shows with a picture and basic information. "
        desc += "On the side, there are usually filters you can use to narrow things down - like price range, category, or other options. "
        desc += "If you click a filter, the results update immediately to show only items matching what you selected. "
        
        desc += "\n\nYou can click on any result to see more details about it. "
        desc += "If nothing matches what you're looking for, the page tells you and might suggest trying a different search."
        
        return desc
    
    def _describe_category_page(self, cluster: PageCluster) -> str:
        """Describe a category page naturally"""
        
        desc = f"This is a {self._get_friendly_page_name(cluster)}. "
        desc += "This page shows you all the items in a specific category. "
        desc += "At the top, you see the category name and sometimes subcategories you can click to narrow things down further. "
        
        desc += "\n\nThe items are displayed in a grid or list, each showing a picture, name, and price. "
        desc += "You can usually change how they're sorted - by price, popularity, newest, etc. "
        
        desc += "\n\nOn the side, there are filters you can use to refine what you see - things like size, color, price range, or brand. "
        desc += "If you click on any item, it takes you to that item's detailed page. "
        desc += "As you scroll down, more items load automatically or you click \"Load More\" to see additional options."
        
        return desc
    
    def _describe_homepage(self, cluster: PageCluster) -> str:
        """Describe a homepage naturally"""
        
        desc = f"This is the {self._get_friendly_page_name(cluster)}. "
        desc += "When you first arrive at the site, you see a large banner or hero section at the top, usually featuring a main promotion or highlight. "
        
        desc += "\n\nAs you scroll down, the page is organized into different sections. "
        desc += "You might see featured products, categories to explore, or special offers. "
        desc += "Each section has images and text that you can click to learn more or shop. "
        
        desc += "\n\nAt the very top, there's a navigation menu with the main categories or pages of the site. "
        desc += "If you click on any of these, it takes you to that section. "
        desc += "There's also usually a search bar where you can type what you're looking for. "
        
        desc += "\n\nThe page is designed to give you an overview of what the site offers and guide you to what you're interested in."
        
        return desc
    
    def _describe_generic_page(self, cluster: PageCluster, page_name: str) -> str:
        """Describe any other type of page naturally"""
        
        desc = f"This is the {page_name}. "
        
        # Build description based on what elements we found
        if cluster.forms_found > 0:
            desc += "The main focus here is a form where you can enter information. "
            desc += "You fill in the required fields, and when you're done, you click the submit button. "
            desc += "The site then processes what you entered and usually shows you a confirmation or takes you to the next step. "
        
        elif cluster.buttons_found > 3:
            desc += "This page has several options you can choose from. "
            desc += "Each button or link takes you to a different place or performs a different action. "
            desc += "You click on whatever matches what you're trying to do. "
        
        else:
            desc += "This page shows you information and options related to this section of the site. "
            desc += "You can read through the content and click on any links or buttons that interest you. "
            desc += "Each click takes you to more detailed information or a related page. "
        
        if cluster.network_intercepts:
            desc += "\n\nAs you interact with the page, it updates to show you relevant information based on your actions."
        
        return desc


# Keep the rest minimal - we only care about the page descriptions

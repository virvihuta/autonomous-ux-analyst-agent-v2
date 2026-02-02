"""
DOM Processing Utilities
The "Cost Saver" - Implements structural hashing and token optimization
"""
import hashlib
import re
from typing import Tuple
from bs4 import BeautifulSoup, Comment, Tag


def generate_structural_hash(html: str) -> str:
    """Generate a hash based ONLY on DOM structure, ignoring content."""
    try:
        soup = BeautifulSoup(html, 'html.parser')
        
        for tag in soup(['script', 'style', 'svg', 'noscript']):
            tag.decompose()
        
        structural_signature = _build_structure_tree(soup)
        return hashlib.sha256(structural_signature.encode('utf-8')).hexdigest()
    
    except Exception as e:
        return hashlib.sha256(html.encode('utf-8')).hexdigest()


def _build_structure_tree(element, depth=0, max_depth=15) -> str:
    """Recursively build a structural representation of the DOM."""
    if depth > max_depth:
        return ""
    
    if not isinstance(element, Tag):
        return ""
    
    tag_name = element.name
    structural_classes = []
    
    if element.get('class'):
        for cls in element.get('class', []):
            if re.match(r'^[a-z][a-z-]*[a-z]$', cls) and len(cls) > 3:
                structural_classes.append(cls)
    
    node_sig = f"<{tag_name}"
    if structural_classes:
        node_sig += f" class='{' '.join(sorted(structural_classes))}'"
    
    if element.get('role'):
        node_sig += f" role='{element.get('role')}'"
    if element.get('type') and tag_name == 'input':
        node_sig += f" type='{element.get('type')}'"
    
    node_sig += ">"
    
    children_sig = ""
    for child in element.children:
        if isinstance(child, Tag):
            children_sig += _build_structure_tree(child, depth + 1, max_depth)
    
    return node_sig + children_sig + f"</{tag_name}>"


def clean_dom_for_llm(html: str, preserve_text_samples: bool = True) -> Tuple[str, int, int]:
    """Aggressively clean HTML to minimize token usage for LLM analysis."""
    raw_size = len(html)
    
    try:
        soup = BeautifulSoup(html, 'html.parser')
        
        for tag in soup(['script', 'style', 'svg', 'meta', 'link', 'noscript', 'iframe']):
            tag.decompose()
        
        for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
            comment.extract()
        
        for tag in soup.find_all(True):
            keep_attrs = ['name', 'id', 'type', 'role', 'placeholder', 'aria-label', 'href', 'action', 'method']
            attrs_to_remove = [attr for attr in tag.attrs if attr not in keep_attrs]
            for attr in attrs_to_remove:
                del tag[attr]
        
        for div in soup.find_all(['div', 'span']):
            if not div.get_text(strip=True) and not div.find_all(['input', 'button', 'form', 'a']):
                div.decompose()
        
        if preserve_text_samples:
            for tag in soup.find_all(string=True):
                if len(tag) > 100:
                    tag.replace_with(tag[:50] + "...")
        
        cleaned_html = soup.prettify()
        cleaned_html = re.sub(r'\n\s*\n', '\n', cleaned_html)
        cleaned_html = re.sub(r'  +', ' ', cleaned_html)
        
        cleaned_size = len(cleaned_html)
        return cleaned_html, raw_size, cleaned_size
    
    except Exception as e:
        return f"<!-- DOM cleaning failed: {str(e)} -->\n{html[:1000]}", raw_size, len(html[:1000])


def estimate_tokens(text: str) -> int:
    """Rough token estimation (1 token ≈ 4 characters)"""
    return len(text) // 4


def extract_form_data(html: str) -> dict:
    """Extract all forms and their fields from HTML."""
    soup = BeautifulSoup(html, 'html.parser')
    forms = []
    
    for form in soup.find_all('form'):
        form_data = {
            'action': form.get('action', ''),
            'method': form.get('method', 'GET').upper(),
            'fields': []
        }
        
        for input_tag in form.find_all(['input', 'textarea', 'select']):
            field = {
                'name': input_tag.get('name', ''),
                'type': input_tag.get('type', 'text'),
                'placeholder': input_tag.get('placeholder', ''),
                'required': input_tag.has_attr('required')
            }
            if field['name']:
                form_data['fields'].append(field)
        
        if form_data['fields']:
            forms.append(form_data)
    
    return {'forms': forms, 'total_forms': len(forms)}

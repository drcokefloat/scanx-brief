"""
Template tags for markdown rendering.
"""

import re
from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter
def markdown(value):
    """
    Convert markdown-like syntax to HTML.
    Supports basic formatting like **bold**, *italic*, and headers.
    """
    if not value:
        return ""
    
    # Convert markdown-style formatting to HTML
    html = str(value)
    
    # Headers (## Header -> <h3>Header</h3>)
    html = re.sub(r'^### (.+)$', r'<h4>\1</h4>', html, flags=re.MULTILINE)
    html = re.sub(r'^## (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
    html = re.sub(r'^# (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
    
    # Bold text (**text** -> <strong>text</strong>)
    html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
    
    # Italic text (*text* -> <em>text</em>)
    html = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html)
    
    # Line breaks
    html = html.replace('\n', '<br>')
    
    # Bullet points (- item -> <ul><li>item</li></ul>)
    lines = html.split('<br>')
    in_list = False
    result_lines = []
    
    for line in lines:
        line = line.strip()
        if line.startswith('- '):
            if not in_list:
                result_lines.append('<ul>')
                in_list = True
            result_lines.append(f'<li>{line[2:]}</li>')
        else:
            if in_list:
                result_lines.append('</ul>')
                in_list = False
            if line:
                result_lines.append(line)
    
    if in_list:
        result_lines.append('</ul>')
    
    html = '<br>'.join(result_lines)
    
    return mark_safe(html)


@register.filter
def truncate_words_html(value, arg):
    """
    Truncate HTML content to a specified number of words.
    """
    if not value:
        return ""
    
    try:
        length = int(arg)
    except (ValueError, TypeError):
        return value
    
    # Strip HTML tags for word counting
    import re
    clean_text = re.sub(r'<[^>]+>', '', str(value))
    words = clean_text.split()
    
    if len(words) <= length:
        return value
    
    # Truncate and add ellipsis
    truncated = ' '.join(words[:length])
    return mark_safe(f"{truncated}...")


@register.simple_tag
def markdown_section(content, section_title):
    """
    Extract a specific section from markdown content.
    """
    if not content or not section_title:
        return ""
    
    lines = content.split('\n')
    section_lines = []
    in_section = False
    
    for line in lines:
        # Check if this is a header line
        if line.startswith('#'):
            if section_title.lower() in line.lower():
                in_section = True
                section_lines.append(line)
            elif in_section:
                # Found another section, stop collecting
                break
        elif in_section:
            section_lines.append(line)
    
    return markdown('\n'.join(section_lines))

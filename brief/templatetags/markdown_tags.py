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
    html = re.sub(r'^### (.+)$', r'<h4 class="mt-4 mb-2">\1</h4>', html, flags=re.MULTILINE)
    html = re.sub(r'^## (.+)$', r'<h3 class="mt-4 mb-2">\1</h3>', html, flags=re.MULTILINE)
    html = re.sub(r'^# (.+)$', r'<h2 class="mt-4 mb-2">\1</h2>', html, flags=re.MULTILINE)
    
    # Bold text (**text** -> <strong>text</strong>)
    html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
    
    # Italic text (*text* -> <em>text</em>)
    html = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html)
    
    # Split into paragraphs and handle line breaks more intelligently
    paragraphs = html.split('\n\n')
    processed_paragraphs = []
    
    for paragraph in paragraphs:
        paragraph = paragraph.strip()
        if paragraph:
            # If it's a header, don't wrap in paragraph tags
            if paragraph.startswith('<h'):
                processed_paragraphs.append(paragraph)
            else:
                # Convert single line breaks to <br> within paragraphs
                paragraph = paragraph.replace('\n', '<br>')
                # Wrap in paragraph tags with margin
                processed_paragraphs.append(f'<p class="mb-3">{paragraph}</p>')
    
    html = '\n'.join(processed_paragraphs)
    
    # Handle numbered lists (1. item -> <ol><li>item</li></ol>)
    lines = html.split('\n')
    in_numbered_list = False
    in_bullet_list = False
    result_lines = []
    
    for line in lines:
        line = line.strip()
        
        # Handle numbered lists
        if re.match(r'^\d+\.\s', line):
            if not in_numbered_list:
                if in_bullet_list:
                    result_lines.append('</ul>')
                    in_bullet_list = False
                result_lines.append('<ol>')
                in_numbered_list = True
            # Extract the text after the number
            text = re.sub(r'^\d+\.\s*', '', line)
            result_lines.append(f'<li>{text}</li>')
        
        # Handle bullet points
        elif line.startswith('- '):
            if not in_bullet_list:
                if in_numbered_list:
                    result_lines.append('</ol>')
                    in_numbered_list = False
                result_lines.append('<ul>')
                in_bullet_list = True
            result_lines.append(f'<li>{line[2:]}</li>')
        
        else:
            # Close any open lists
            if in_numbered_list:
                result_lines.append('</ol>')
                in_numbered_list = False
            if in_bullet_list:
                result_lines.append('</ul>')
                in_bullet_list = False
            
            if line:
                result_lines.append(line)
    
    # Close any remaining open lists
    if in_numbered_list:
        result_lines.append('</ol>')
    if in_bullet_list:
        result_lines.append('</ul>')
    
    html = '\n'.join(result_lines)
    
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

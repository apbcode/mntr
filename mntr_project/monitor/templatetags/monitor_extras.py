from django import template
from django.utils.safestring import mark_safe
import difflib
import logging

logger = logging.getLogger(__name__)

register = template.Library()

@register.filter
def htmldiff(a, b):
    logger.info(f"htmldiff called. Length a: {len(a)}, Length b: {len(b)}")
    s = difflib.SequenceMatcher(None, a, b)
    output = []
    for opcode, a_start, a_end, b_start, b_end in s.get_opcodes():
        if opcode == 'equal':
            output.append(s.a[a_start:a_end])
        elif opcode == 'insert':
            output.append(f'<ins>{s.b[b_start:b_end]}</ins>')
        elif opcode == 'delete':
            output.append(f'<del>{s.a[a_start:a_end]}</del>')
        elif opcode == 'replace':
            output.append(f'<del>{s.a[a_start:a_end]}</del><ins>{s.b[b_start:b_end]}</ins>')
    return mark_safe(''.join(output))

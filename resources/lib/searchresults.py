"""Group matching search titles while preserving every source and route."""

from copy import copy
import re
import unicodedata


def _text(value):
    return ' '.join(unicodedata.normalize('NFKC', str(value or '')).casefold().split())


def grouped_results(results):
    groups = {}
    for index, result in enumerate(sorted(results, key=lambda item: item['guiElement'].getSiteName() or '')):
        element = copy(result['guiElement'])
        title = re.sub(r'\[/?(?:COLOR(?:\s+[^\]]+)?|B|I)\]', '', element.getTitle(), flags=re.I)
        key = (_text(title), _text(getattr(element, '_mediaType', '')),
               _text(getattr(element, '_sYear', '')), result['isFolder'],
               _text(getattr(element, '_season', '')), _text(getattr(element, '_episode', '')),
               _text(getattr(element, '_sLanguage', '')), _text(getattr(element, '_sSubLanguage', '')),
               _text(getattr(element, '_tmdbID', '')))
        if not key[0]:
            key = ('', index)
        groups.setdefault(key, []).append(result)

    rendered = []
    for group in groups.values():
        source_count = len({item['guiElement'].getSiteName() for item in group})
        for index, result in enumerate(group):
            if len(group) == 1:
                rendered.append(result)
                continue
            item = dict(result)
            element = copy(result['guiElement'])
            if index == 0:
                note = '%s Quellen' % source_count if source_count > 1 else '%s Treffer' % len(group)
            else:
                note = 'Alternative: %s' % element.getSiteName()
            previous = getattr(element, '_sInfo', '')
            element._sInfo = '%s; %s' % (previous, note) if previous else note
            item['guiElement'] = element
            rendered.append(item)
    return rendered

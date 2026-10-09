from resources.lib.searchresults import grouped_results


class Element:
    def __init__(self, title, source, year='2026', media='movie', language='de', episode=''):
        self.title = title
        self.source = source
        self._sYear = year
        self._mediaType = media
        self._sLanguage = language
        self._episode = episode
        self._sInfo = 'HD'

    def getTitle(self):
        return self.title

    def getSiteName(self):
        return self.source


def entry(title, source, **kwargs):
    return {'guiElement': Element(title, source, **kwargs),
            'params': {'siteUrl': 'https://example.invalid/' + source}, 'isFolder': True}


def test_matching_titles_are_adjacent_and_keep_routes_and_original_metadata():
    first = entry('Testfilm', 'a')
    unrelated = entry('Anderer Film', 'b')
    alternative = entry(' TESTFILM ', 'c')
    output = grouped_results([alternative, unrelated, first])
    assert [item['params'] for item in output] == [first['params'], alternative['params'], unrelated['params']]
    assert output[0]['guiElement']._sInfo == 'HD; 2 Quellen'
    assert output[1]['guiElement']._sInfo == 'HD; Alternative: c'
    assert first['guiElement']._sInfo == alternative['guiElement']._sInfo == 'HD'


def test_remakes_media_types_languages_and_episodes_remain_distinct():
    items = [entry('Titel', 'a'), entry('Titel', 'b', year='1980'),
             entry('Titel', 'c', media='tvshow'), entry('Titel', 'd', language='en'),
             entry('Titel', 'e', media='episode', episode='1'),
             entry('Titel', 'f', media='episode', episode='2')]
    assert grouped_results(items) == items


def test_empty_titles_and_single_results_are_not_decorated():
    items = [entry('', 'a'), entry('', 'b'), entry('Einzeln', 'c')]
    assert grouped_results(items) == items


def test_multiple_results_from_one_provider_do_not_inflate_source_count():
    items = [entry('Titel', 'a'), entry('Titel', 'a'), entry('Titel', 'b')]
    output = grouped_results(items)
    assert len(output) == 3
    assert output[0]['guiElement']._sInfo == 'HD; 2 Quellen'
    assert grouped_results(items[:2])[0]['guiElement']._sInfo == 'HD; 2 Treffer'


def test_search_renderer_uses_grouping_without_losing_results():
    import ast
    from pathlib import Path
    from types import SimpleNamespace

    path = Path(__file__).resolve().parents[1] / 'baka.py'
    tree = ast.parse(path.read_text(encoding='utf-8-sig'))
    function = next(node for node in tree.body if isinstance(node, ast.FunctionDef)
                    and node.name == '_renderCollectedSearchResults')
    namespace = {}
    exec(compile(ast.Module(body=[function], type_ignores=[]), str(path), 'exec'), namespace)
    items = [entry('Titel', 'a'), entry('Anderer', 'b'), entry('Titel', 'c')]
    rendered = []
    gui = SimpleNamespace(searchResults=items,
                          addFolder=lambda element, params, **kwargs: rendered.append((element, params)),
                          setView=lambda: None, setEndOfDirectory=lambda: None)
    assert namespace['_renderCollectedSearchResults'](gui)
    assert [params for _, params in rendered] == [items[0]['params'], items[2]['params'], items[1]['params']]
    assert len(rendered) == len(items)

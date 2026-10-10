import re, io

with io.open('resources/settings.xml', 'r', encoding='utf-8') as f:
    content = f.read()

gs = re.findall(r'<setting id="global_search_([a-zA-Z0-9_]+)" type="boolean" label="30052">', content)
tls = re.findall(r'<setting id="plugin_([a-zA-Z0-9_]+)_allowInsecureTLS" type="boolean"', content)
print('global_search count:', len(gs))
print('allowInsecureTLS count:', len(tls))
print('in tls but not gs:', sorted(set(tls) - set(gs)))
print('in gs but not tls:', sorted(set(gs) - set(tls)))

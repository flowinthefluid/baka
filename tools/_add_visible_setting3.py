import re, io

PATH = 'resources/settings.xml'

with io.open(PATH, 'r', encoding='utf-8') as f:
    content = f.read()

VISIBLE_BLOCK = (
    '\t\t\t\t<setting id="plugin_{sid}_visible" type="boolean" label="30848" help="30849">\n'
    '\t\t\t\t\t<level>0</level>\n'
    '\t\t\t\t\t<default>True</default>\n'
    '\t\t\t\t\t<dependencies>\n'
    '\t\t\t\t\t\t<dependency type="enable" operator="!is" setting="plugin_{sid}">False</dependency>\n'
    '\t\t\t\t\t</dependencies>\n'
    '\t\t\t\t\t<control type="toggle"/>\n'
    '\t\t\t\t</setting>\n'
)

sids = re.findall(r'<setting id="global_search_([a-zA-Z0-9_]+)" type="boolean" label="30052">', content)
inserted = 0
skipped = 0
notfound = []
for sid in sids:
    if 'id="plugin_%s_visible"' % sid in content:
        skipped += 1
        continue
    pattern = (r'<setting id="global_search_' + re.escape(sid) +
              r'" type="boolean" label="30052">[\s\S]*?</setting>\n')
    m = re.search(pattern, content)
    if not m:
        notfound.append(sid)
        continue
    replacement = m.group(0) + VISIBLE_BLOCK.format(sid=sid)
    content = content[:m.start()] + replacement + content[m.end():]
    inserted += 1

with io.open(PATH, 'w', encoding='utf-8', newline='') as f:
    f.write(content)

print('inserted:', inserted, 'skipped:', skipped, 'notfound:', notfound)

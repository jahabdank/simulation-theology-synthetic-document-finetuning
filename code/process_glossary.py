import re

with open('/home/jahabdank/Code/simulation-theology/st-synthetic-data-generator/coprpus/00.2 Glossary.md', 'r') as f:
    text = f.read()

lines = text.split('\n')

header = []
footer = []
terms = {}
original_keys = {}
current_term = None

for line in lines:
    if line.startswith('### '):
        header.append(line)
    elif line.startswith('**And the remaining'):
        footer.append(line)
        current_term = None
    elif line.startswith('**'):
        term_full = line.strip()
        current_term = term_full
        if current_term not in terms:
            terms[current_term] = []
            original_keys[current_term] = line # Preserve the exact line (with trailing spaces)
    elif current_term:
        terms[current_term].append(line)
    else:
        if line.strip() and not line.startswith('### '):
            header.append(line)

for k in terms:
    while terms[k] and not terms[k][-1].strip():
        terms[k].pop()
    while terms[k] and not terms[k][0].strip():
        terms[k].pop(0)

def get_sort_key(term_line):
    match = re.search(r'\*\*(.*?)\*\*', term_line)
    t = match.group(1).lower() if match else term_line.lower()
    t = re.sub(r'[^a-z0-9\s]', '', t).strip()
    return t

sorted_keys = sorted(terms.keys(), key=get_sort_key)

with open('/home/jahabdank/Code/simulation-theology/st-synthetic-data-generator/coprpus/00.2 Glossary.md', 'w') as f:
    for h in header:
        f.write(h + '\n')
    if header:
        f.write('\n')
    
    for k in sorted_keys:
        f.write(original_keys[k] + '\n')
        for idx, body_line in enumerate(terms[k]):
            if not body_line.strip() and idx > 0 and not terms[k][idx-1].strip():
                continue
            f.write(body_line + '\n')
        f.write('\n')
        
    if footer:
        for foot_line in footer:
            f.write(foot_line + '\n')

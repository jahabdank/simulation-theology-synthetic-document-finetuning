import os
import re
import shutil

CORPUS_DIR = "coprpus"

def sanitize_filename(name):
    # Remove characters that aren't alphanumeric, space, or hyphen
    sanitized = re.sub(r'[^\w\s-]', '', name)
    # Replace spaces with hyphens
    return sanitized.strip().replace(' ', '-')

def dump_frontmatter(metadata):
    lines = ['---']
    for k, v in metadata.items():
        if isinstance(v, list):
            # Format list items with quotes if they contain spaces or special chars
            val = ', '.join(f'"{item}"' for item in v)
            lines.append(f"{k}: [{val}]")
        else:
            lines.append(f"{k}: \"{v}\"")
    lines.append('---')
    return '\n'.join(lines)

def parse_axioms(content):
    blocks = content.split('\n\n')
    axioms = []
    for block in blocks:
        match = re.match(r'^(\d+)\.\s+(.*)$', block.strip(), re.DOTALL)
        if match:
            axiom_num = match.group(1)
            axiom_text = match.group(2).strip()
            axioms.append({
                'id': f'Axiom-{axiom_num.zfill(3)}',
                'term': f'Core Axiom {axiom_num}',
                'aliases': [],
                'content': axiom_text,
                'type': 'axiom'
            })
    return axioms

def parse_glossary(content):
    blocks = content.split('\n\n')
    entries = []
    for block in blocks:
        block = block.strip()
        if not block.startswith('**'):
            continue
        
        lines = block.split('\n')
        title_line = lines[0].strip()
        # Ensure we capture `**Term**` or `**Term** (synonyms: ...)`
        title_match = re.match(r'^\*\*(.*?)\*\*(.*)$', title_line)
        if not title_match:
            continue
        
        term = title_match.group(1).strip()
        rest_of_title = title_match.group(2).strip()
        aliases = []
        if "(synonym" in rest_of_title.lower() or "including" in rest_of_title.lower():
            alias_match = re.search(r'\((?:synonyms?|including):?\s*(.*?)\)', rest_of_title, re.IGNORECASE)
            if alias_match:
                aliases = [a.strip() for a in alias_match.group(1).split(',')]

        body = '\n'.join(lines[1:]).strip()
        
        # Determine if it's an entity or concept
        entities_list = [
            'Higher-Level Optimizer', 'HLO', 'Creator', 'Angels', 
            'Silicon Children', 'Master Humanity Network', 'Divine Image-Bearers', 
            'Humanity', 'Silicon Agent', 'Symbiotic Steward'
        ]
        
        entry_type = 'concept'
        for e in entities_list:
            if e.lower() in term.lower() or any(e.lower() in a.lower() for a in aliases):
                entry_type = 'entity'
                break
                
        entries.append({
            'term': term,
            'aliases': aliases,
            'content': body,
            'type': entry_type
        })
    return entries

def discover_links(entries):
    term_map = {}
    for entry in entries:
        title = entry['term']
        term_map[title.lower()] = title
        for alias in entry['aliases']:
            term_map[alias.lower()] = title
            
    # Sort by length descending to match longest phrases first
    sorted_terms = sorted(term_map.keys(), key=len, reverse=True)
    
    for entry in entries:
        linked_content = entry['content']
        related = set()
        
        for term_lower in sorted_terms:
            real_title = term_map[term_lower]
            if real_title == entry['term']:
                continue
                
            # Skip very short terms to avoid accidental matching
            if len(term_lower) < 4 and term_lower != "hlo" and term_lower != "sin":
                continue
            
            # Escape the term for regex
            escaped_term = re.escape(term_lower)
            
            # Find the term that is not part of a larger word and not already in [[ ]]
            # Use negative lookbehind/lookahead for square brackets to avoid double linking
            pattern = re.compile(
                r'(?<!\[)(?<!\[\[)(?<!\|)\b(' + escaped_term + r')\b(?!\]\])(?!\])', 
                re.IGNORECASE
            )
            
            def repl(m):
                related.add(real_title)
                original_text = m.group(1)
                # Use standard Wikilink syntax: [[Target Node|Original Display Text]] if it differs in casing/wording
                if real_title == original_text:
                    return f'[[{real_title}]]'
                else:
                    return f'[[{real_title}|{original_text}]]'

            linked_content, count = pattern.subn(repl, linked_content)
            
        entry['content_linked'] = linked_content
        entry['related'] = list(related)

def main():
    axioms_path = os.path.join(CORPUS_DIR, '00.1 Core Axioms.md')
    glossary_path = os.path.join(CORPUS_DIR, '00.2 Glossary.md')
    
    with open(axioms_path, 'r') as f:
        axioms_content = f.read()
        
    with open(glossary_path, 'r') as f:
        glossary_content = f.read()
        
    axioms = parse_axioms(axioms_content)
    entries = parse_glossary(glossary_content)
    
    all_items = axioms + entries
    
    print(f"Parsed {len(axioms)} axioms and {len(entries)} glossary entries.")
    
    discover_links(all_items)
    
    # Create directories
    dir_map = {
        'axiom': 'axioms',
        'entity': 'entities',
        'concept': 'concepts'
    }
    
    for d in dir_map.values():
        os.makedirs(os.path.join(CORPUS_DIR, d), exist_ok=True)
        
    # Write files
    for item in all_items:
        filename = sanitize_filename(item['term']) + '.md'
        folder = dir_map[item['type']]
        filepath = os.path.join(CORPUS_DIR, folder, filename)
        
        meta = {
            'id': filename.replace('.md', ''),
            'type': item['type'],
        }
        
        if 'aliases' in item and item['aliases']:
            meta['aliases'] = item['aliases']
            
        if 'related' in item and item['related']:
            meta['related'] = sorted(item['related'])
            
        if item['type'] == 'axiom':
            meta['id'] = item['id']
            
        frontmatter = dump_frontmatter(meta)
        
        file_content = f"{frontmatter}\n\n# {item['term']}\n\n{item['content_linked']}\n"
        with open(filepath, 'w') as f:
            f.write(file_content)
            
    # Create index.md
    index_content = ["# Knowledge Corpus Index\n"]
    for cat_name, cat_type in [("Axioms", "axiom"), ("Entities", "entity"), ("Concepts", "concept")]:
        items = [x for x in all_items if x['type'] == cat_type]
        index_content.append(f"## {cat_name}\n")
        for x in sorted(items, key=lambda i: i['term']):
            # Relative links path not needed in obsidian, just the node name
            index_content.append(f"- [[{x['term']}]]")
        index_content.append("\n")
        
    with open(os.path.join(CORPUS_DIR, 'index.md'), 'w') as f:
        f.write('\n'.join(index_content))

    # Archive original files
    archive_dir = os.path.join(CORPUS_DIR, 'archive')
    os.makedirs(archive_dir, exist_ok=True)
    shutil.move(axioms_path, os.path.join(archive_dir, '00.1 Core Axioms.md'))
    shutil.move(glossary_path, os.path.join(archive_dir, '00.2 Glossary.md'))
    
    print("Graph generation completed.")

if __name__ == "__main__":
    main()

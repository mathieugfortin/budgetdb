import os
import re

def find_orphan_templates(template_dir, search_in_dirs):
    # 1. Get all .html files in your template directory
    all_templates = []
    for root, _, files in os.walk(template_dir):
        for file in files:
            if file.endswith('.html'):
                # Get path relative to template root (e.g., 'budgetdb/index.html')
                rel_path = os.path.relpath(os.path.join(root, file), template_dir)
                all_templates.append(rel_path)

    # 2. Search for those strings in your codebase
    orphans = []
    for template in all_templates:
        found = False
        # Search in Python files and other HTML files (for includes/extends)
        for search_dir in search_in_dirs:
            for root, _, files in os.walk(search_dir):
                for file in files:
                    if file.endswith(('.py', '.html')):
                        with open(os.path.join(root, file), 'r', errors='ignore') as f:
                            if template in f.read():
                                found = True
                                break
                if found: break
            if found: break
        
        if not found:
            orphans.append(template)
            
    return orphans

# Usage
TEMPLATES = '/github/budget/budgetdb/templates'
CODE_DIRS = ['/github/budget/budgetdb', '/github/budget/config']

orphans = find_orphan_templates(TEMPLATES, CODE_DIRS)
print("Potential Orphan Templates (Not found in code):")
for o in orphans:
    print(f" - {o}")
import os
import re

dir_path = r'c:\Users\jxtro\Desktop\WORK\Accesco-IMS\src\src'

replacements = [
    (r'bg-zinc-950', r'bg-surface-alt'),
    (r'bg-zinc-900', r'bg-surface'),
    (r'bg-zinc-800', r'bg-surface-raised'),
    (r'bg-zinc-700', r'bg-surface-elevated'),
    (r'border-zinc-800', r'border-edge'),
    (r'border-zinc-700', r'border-edge'),
    (r'text-zinc-100', r'text-txt'),
    (r'text-zinc-200', r'text-txt'),
    (r'text-zinc-300', r'text-txt-sec'),
    (r'text-zinc-400', r'text-txt-sec'),
    (r'text-zinc-500', r'text-txt-muted'),
    (r'text-zinc-600', r'text-txt-faint'),
    (r'dark:text-zinc-300', r'text-txt-sec'),
    (r'dark:text-zinc-400', r'text-txt-sec'),
    (r'dark:text-zinc-500', r'text-txt-muted'),
    (r'dark:border-zinc-700', r'border-edge'),
    (r'dark:border-zinc-600', r'border-edge'),
    (r'dark:bg-zinc-800', r'bg-surface-raised'),
]

for root, _, files in os.walk(dir_path):
    for file in files:
        if file.endswith('.tsx'):
            filepath = os.path.join(root, file)
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            new_content = content
            for old, new in replacements:
                new_content = re.sub(old, new, new_content)
                
            if new_content != content:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                print(f"Updated {filepath}")

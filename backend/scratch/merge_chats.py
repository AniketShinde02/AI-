import os
from datetime import datetime

path = "d:/AI/.chats"
target_file = os.path.join(path, "merged_chats_june_29_30.md")

files_to_merge = [
    ("2026-06-29 14:15:46", "@[d__AI_.chats_Implementing phases v1, brain, al the things.md]  read this   once do not eidt code.md"),
    ("2026-06-29 15:51:22", "and   add that removed models aslo  in that pl  dont lremove then what i meand to saiy that for the issue we are facing i n the  terminal logs for connectiviy issues  to gemini live model.md"),
    ("2026-06-29 16:26:53", "29.md"),
    ("2026-06-29 22:58:26", "@[current_problems]  bro we really isue  red  error that seems dander to be pl take tare of all of the proepr test deptly each file is erro free.md"),
    ("2026-06-30 13:11:46", "i mean the issue is on normal refrehs the old laout and oin hard refresh the new thing so  pl web search why this happens then aslo  what as proper solution ofr this  _.md"),
    ("2026-06-30 14:36:02", "Continue but do not commit on github pl.md")
]

with open(target_file, "w", encoding="utf-8") as outfile:
    outfile.write("# Merged Chat History (June 29 - June 30, 2026)\n\n")
    outfile.write("This document compiles the chat history logs recorded across June 29th and June 30th, 2026. ")
    outfile.write("Because Antigravity/Windsurf context compression truncates conversation history over time to fit within token boundaries, ")
    outfile.write("these periodic logs have been merged chronologically to preserve the complete history of developer intents, fixes, and decisions.\n\n")
    
    for dt, filename in files_to_merge:
        filepath = os.path.join(path, filename)
        outfile.write(f"\n\n========================================================================\n")
        outfile.write(f"### Chat Session: {filename}\n")
        outfile.write(f"**Timestamp**: {dt}\n")
        outfile.write(f"========================================================================\n\n")
        
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as infile:
                content = infile.read()
                # If the file starts with '# Chat Conversation', strip it to avoid nested main headers
                if content.startswith("# Chat Conversation"):
                    content = content[len("# Chat Conversation"):].strip()
                outfile.write(content)
        else:
            outfile.write(f"\n*Error: File {filename} not found during merge.*\n")

print(f"Successfully merged {len(files_to_merge)} files into {target_file}")

#!/usr/bin/env python3
"""站点后处理（幂等，顺序固定）：navfix → header → cachefix。用法：python3 build/postbuild.py SITE_DIR"""
import sys, os, subprocess
H = os.path.dirname(os.path.abspath(__file__)); S = sys.argv[1]
for cmd in (['navfix.py', os.path.join(S, 'stories.html')], ['header.py', S], ['cachefix.py', S]):
    subprocess.run([sys.executable, os.path.join(H, cmd[0])] + cmd[1:], check=True)

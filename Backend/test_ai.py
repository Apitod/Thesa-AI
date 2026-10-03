import sys
import json
from src.ai_engine import get_ai_engine

try:
    ai = get_ai_engine()
    res = ai.generate_full_paper({'mata_kuliah':'TI', 'judul':'AI test'}, {'mata_kuliah':'TI', 'judul':'AI test'})
    print("SUCCESS")
except Exception as e:
    import traceback
    traceback.print_exc()

#!/usr/bin/env python
"""
Test script untuk memvalidasi bahwa sistem dapat dijalankan tanpa error
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.input_handler import InputHandler, get_input_handler
from src.template_engine import TemplateEngine, get_template_engine
from src.document_builder import DocumentBuilder, get_document_builder
from src.ai_engine import AIEngine, get_ai_engine
from src.token_logger import TokenLogger, get_total_usage

def test_system_initialization():
    """Test bahwa semua komponen sistem dapat diinisialisasi"""
    print("=" * 60)
    print("SYSTEM INITIALIZATION TEST")
    print("=" * 60)

    try:
        print("[1] Testing InputHandler...")
        input_handler = get_input_handler()
        print("    [OK] InputHandler initialized successfully")

        print("[2] Testing TemplateEngine...")
        template_engine = get_template_engine()
        print("    [OK] TemplateEngine initialized successfully")

        print("[3] Testing DocumentBuilder...")
        document_builder = get_document_builder()
        print("    [OK] DocumentBuilder initialized successfully")

        print("[4] Testing AIEngine...")
        ai_engine = get_ai_engine()
        print("    [OK] AIEngine initialized successfully")

        print("[5] Testing TokenLogger...")
        token_logger = TokenLogger()
        print("    [OK] TokenLogger initialized successfully")

        print("[6] Testing Main Application...")
        from src.main import PaperGeneratorApp
        app = PaperGeneratorApp()
        print("    [OK] Main application initialized successfully")

        print("\n" + "=" * 60)
        print("SYSTEM STATUS: READY FOR USE")
        print("=" * 60)
        print("\nUntuk menjalankan aplikasi, gunakan perintah:")
        print("    python src/main.py")
        print("\n" + "=" * 60)
        return True

    except Exception as e:
        print(f"\n[FAIL] Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_system_initialization()
    sys.exit(0 if success else 1)
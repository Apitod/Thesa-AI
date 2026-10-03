import sys
from search_engine import search_articles
from sinta_validator import filter_sinta_articles

def find_sinta_articles_by_theme(theme):
    print(f"==================================================")
    print(f"  SINTA 1-3 ARTICLE FINDER ")
    print(f"==================================================")
    print(f"Tema Pencarian: {theme}\n")
    
    # 1. Cari Artikel
    # Mengambil lebih banyak data karena sebagian besar mungkin akan terfilter
    raw_articles = search_articles(theme, max_results=100)
    
    if not raw_articles:
        print("\n[!] Tidak ada artikel ditemukan untuk tema ini.")
        return
        
    # 2. Filter Sinta 1-3
    sinta_articles = filter_sinta_articles(raw_articles, max_sinta=3)
    
    # 3. Tampilkan Hasil
    print(f"\n==================================================")
    print(f"  HASIL PENCARIAN (SINTA 1-3) ")
    print(f"==================================================")
    
    if not sinta_articles:
        print(f"Maaf, tidak ada artikel Sinta 1-3 yang cocok dengan tema '{theme}'.")
        print("Note: Pastikan jurnal target Anda ada di dalam file sinta_database.json")
    else:
        for i, article in enumerate(sinta_articles):
            print(f"{i+1}. Judul  : {article['title']}")
            print(f"   Jurnal : {article['journal_name']} (SINTA {article['sinta_rating']})")
            print(f"   Tahun  : {article['year']}")
            if article['url']:
                print(f"   Link   : {article['url']}")
            print("")

if __name__ == "__main__":
    print("Masukkan Tema/Topik yang ingin dicari (contoh: 'teknologi informasi' atau 'machine learning')")
    try:
        tema = input("Tema: ")
        if tema.strip():
            find_sinta_articles_by_theme(tema)
        else:
            print("Tema tidak boleh kosong.")
    except KeyboardInterrupt:
        print("\nKeluar dari program.")
        sys.exit(0)

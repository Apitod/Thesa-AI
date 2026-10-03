import json
import os

def load_sinta_database():
    """
    Memuat database lokal jurnal Sinta.
    Dalam praktiknya, file ini berisi puluhan ribu jurnal Sinta 1-6.
    Untuk saat ini kita menggunakan dummy file sinta_database.json.
    """
    db_path = os.path.join(os.path.dirname(__file__), "sinta_database.json")
    try:
        with open(db_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"[!] Database sinta tidak ditemukan di: {db_path}")
        return []

def filter_sinta_articles(articles, max_sinta=3):
    """
    Menerima list artikel dari search engine, dan memfilter hanya yang 
    ada di database Sinta kita dengan rating <= max_sinta (yaitu 1, 2, atau 3).
    Pencocokan menggunakan ISSN atau Nama Jurnal.
    """
    sinta_db = load_sinta_database()
    filtered_results = []
    
    print(f"[*] Memvalidasi {len(articles)} artikel terhadap Database Sinta...")
    
    for article in articles:
        article_issns = article.get("issns", [])
        article_journal = str(article.get("journal_name", "")).lower().strip()
        
        is_sinta = False
        sinta_rating = None
        
        for sinta_journal in sinta_db:
            # Pengecekan 1: Cocokkan ISSN
            db_issns = [
                str(sinta_journal.get("issn", "")), 
                str(sinta_journal.get("e_issn", ""))
            ]
            
            # Pengecekan 2: Cocokkan Nama (Jika tidak ada ISSN, meskipun ISSN lebih akurat)
            db_name = str(sinta_journal.get("journal_name", "")).lower().strip()
            
            # Cek apakah ada ISSN yang cocok
            issn_match = any(issn in db_issns for issn in article_issns if issn)
            
            # Cek apakah nama cocok persis
            name_match = (article_journal == db_name) and len(article_journal) > 0
            
            if issn_match or name_match:
                if sinta_journal.get("sinta_rating", 99) <= max_sinta:
                    is_sinta = True
                    sinta_rating = sinta_journal.get("sinta_rating")
                break # Sudah ketemu jurnalnya
                
        if is_sinta:
            # Tambahkan metadata Sinta ke artikel
            article["sinta_rating"] = sinta_rating
            filtered_results.append(article)
            
    print(f"[*] Validasi selesai. {len(filtered_results)} artikel lolos filter Sinta 1-{max_sinta}.")
    return filtered_results

if __name__ == "__main__":
    db = load_sinta_database()
    print(f"Total jurnal di database: {len(db)}")

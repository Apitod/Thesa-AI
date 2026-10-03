import requests

def search_articles(theme, max_results=50):
    """
    Mencari artikel berdasarkan tema menggunakan Crossref API.
    Karena kita mencari artikel Indonesia/Sinta, kita bisa tambahkan kata kunci tertentu atau 
    biarkan Crossref mencarinya secara global, nanti difilter oleh sinta_validator.
    """
    url = "https://api.crossref.org/works"
    
    # Parameter pencarian
    params = {
        "query": theme,
        "select": "title,container-title,ISSN,URL,author,issued",
        "rows": max_results,
        "filter": "type:journal-article"
    }
    
    headers = {
        # Good practice: Provide an email in User-Agent to be put in the "Polite Pool"
        "User-Agent": "SintaFinderBot/1.0 (mailto:admin@neomakalah.com)"
    }
    
    print(f"[*] Mencari artikel dengan tema '{theme}' di Crossref...")
    response = requests.get(url, params=params, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        items = data.get("message", {}).get("items", [])
        
        articles = []
        for item in items:
            # Ambil judul artikel
            title = item.get("title", [""])[0] if item.get("title") else "Tidak ada judul"
            
            # Ambil nama jurnal
            journal_name = item.get("container-title", [""])[0] if item.get("container-title") else "Tidak ada jurnal"
            
            # Ambil ISSN
            issn = item.get("ISSN", [])
            
            # Ambil URL
            url_link = item.get("URL", "")
            
            # Ambil tahun
            try:
                year = item.get("issued", {}).get("date-parts", [[None]])[0][0]
            except Exception:
                year = "Unknown"
                
            articles.append({
                "title": title,
                "journal_name": journal_name,
                "issns": issn,
                "year": year,
                "url": url_link
            })
            
        print(f"[*] Berhasil menemukan {len(articles)} artikel dari Crossref (Belum difilter Sinta).")
        return articles
    else:
        print(f"[!] Error fetching data dari Crossref: {response.status_code}")
        return []

if __name__ == "__main__":
    # Test pencarian
    hasil = search_articles("teknologi informasi")
    for i, a in enumerate(hasil[:3]):
        print(f"{i+1}. {a['title']} - {a['journal_name']} - ISSN: {a['issns']}")

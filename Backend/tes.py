import requests

url = "https://api.zotero.org/users/20355252/items"

headers = {
    "Zotero-API-Key": "KeS59QDa788x2VIyb6bL0Um7",
    "Content-Type": "application/json"
}

data = [{
    "itemType": "journalArticle",
    "title": "Artificial Intelligence in Education",
    "creators": [{
        "creatorType": "author",
        "firstName": "John",
        "lastName": "Doe"
    }],
    "date": "2020",
    "publicationTitle": "Journal of AI"
}]

res = requests.post(url, headers=headers, json=data)

print(res.status_code)
from serpapi import GoogleSearch

params = {
  "engine": "google_hotels",
  "q": "Hanoi",
  "check_in_date": "2025-05-30",
  "check_out_date": "2025-05-31",
  "adults": "2",
  "currency": "USD",
  "gl": "us",
  "hl": "en",
  "api_key": "6ba39a782bb4f1a04d900f5ed50c57b8d4d06d2ed73c0a4b59a075948cbe5c12"
}

search = GoogleSearch(params)
results = search.get_dict()
print(results.get("properties", []))
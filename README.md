# ATI_Final
How to Run:
- Install requirements: pip install -r requirements.txt

1. Start the backend API (FastAPI)
- Run in terminal: uvicorn backend.main:app --reload
now articles can be crawled in admin page by clicking "Chạy Crawl ngay" button at "Nhật ký hệ thống" tab
(output: crawled_articles.json)

2. Processing articles
2.1 Run split sentences stage by running this command in terminal:
python backend/split_sentence.py
(output: crawled_sentences.json)

2.2 Run claim extraction stage by running this command in terminal:
python backend/claim_extraction.py
(output: claims_checkpoint.json)

2.3 Run enrichment stage by running this command in terminal:
python backend/claims_enrich.py
(output: claims_enriched.json)

2.4. Cluster enriched claims by running this command in terminal:
python backend/synthesis_claims.py
(output: claims_grouped_summary.json)

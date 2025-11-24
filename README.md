ATI_Final – How to Run

Install requirements:
pip install -r requirements.txt

Start the backend API (FastAPI):
uvicorn backend.main:app --reload

After the server starts, articles can be crawled in the admin page by clicking “Chạy Crawl ngay” in the “Nhật ký hệ thống” tab.
Output: crawled_articles.json

Processing articles:

3.1 Split sentences:
python backend/split_sentence.py
Output: crawled_sentences.json

3.2 Claim extraction:
python backend/claim_extraction.py
Output: claims_checkpoint.json

3.3 Claim enrichment:
python backend/claims_enrich.py
Output: claims_enriched.json

3.4 Cluster enriched claims:
python backend/synthesis_claims.py
Output: claims_grouped_summary.json

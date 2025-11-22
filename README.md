# ATI_Final
How to Run:
- Install requirements:

pip install -r requirements.txt

1. Start the backend API (FastAPI)
uvicorn backend.main:app --reload
(now articles can be crawled in admin page)

2. Run split sentences stage
python backend/split_sentence.py

3. Run claim extraction
python backend/claim_extraction.py

4. Run enrichment stage
python backend/claims_enrich.py

5. Cluster enriched claims
python backend/synthesis_claims.py

6. Open the editor.html


If the frontend is static and loads JSON from your /data folder:
→ Open:

frontend/index.html

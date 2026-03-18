from fastapi import APIRouter
from app.services.retrieval.retrieval_service import RetrievalService
from app.services.generation.generation_service import GenerationService
from app.services.query.query_rewrite.query_rewrite_service import QueryRewriteService
from app.services.query.query_decomposition.query_decomposition_service import QueryDecompositionService
from app.services.query.multi_query.multi_query_service import MultiQueryService
from pydantic import BaseModel

router = APIRouter()

retriever = RetrievalService()
rewriter  = QueryRewriteService()
generator = GenerationService()
decomposer = QueryDecompositionService()
multi_query = MultiQueryService()

class QueryRequest(BaseModel):
    document_id: str
    question: str

@router.post("")
def query_docs(request: QueryRequest):

    # Step 1: Decompose query
    sub_queries = decomposer.decompose(request.question)

    all_chunks = []

    print("\n" + "="*70)
    print("🧠 ORIGINAL QUESTION:", request.question)
    print("🧩 SUB-QUERIES:", sub_queries)
    print("="*70 + "\n")

    # Step 2: Process each sub-query
    for q in sub_queries:

        print("\n➡️ Processing Sub-Query:", q)

        # Step 1: Rewrite
        rewritten_query = rewriter.rewrite(q)
        print("\n➡️ Processing Sub-Query:", q)

        # Step 2: Multi-query expansion ← ADD HERE
        expanded_queries = multi_query.generate_queries(
            rewritten_query,
            total_sub_queries=len(sub_queries)
        )
        print("🔀 Expanded Queries:", expanded_queries)

        # Step 3: Retrieval for each expanded query
        for eq in expanded_queries:

            print("\n🔎 Running retrieval for:", eq)
            result = retriever.search(request.document_id, eq)

            matches = result["matches"]
            print(f"📊 Retrieved {len(matches)} chunks")

            for i, chunk in enumerate(matches):
                print(f"   Rank {i+1} | Score: {round(chunk['score'], 4)}")
                print(f"   Text: {chunk['chunk_text'][:120]}")
                print("-" * 40)

            all_chunks.extend(matches)

    # Step 3: Deduplicate chunks
    unique_chunks = {c["chunk_id"]: c for c in all_chunks}.values()

    # Step 4: Sort by score
    sorted_chunks = sorted(unique_chunks, key=lambda x: x["score"], reverse=True)

    # Step 5: Take top-k
    retrieved_chunks = sorted_chunks[:5]
    
    print("\n" + "="*70)
    print("🏁 FINAL MERGED TOP CHUNKS")

    for i, chunk in enumerate(retrieved_chunks):
        print(f"\nFinal Rank {i+1}")
        print("Score:", round(chunk["score"], 4))
        print("Chunk ID:", chunk["chunk_id"])
        print("Page:", chunk["page_number"])
        print("Text:", chunk["chunk_text"][:200])

    print("="*70 + "\n")

    # Safety check
    if not retrieved_chunks:
        return {
            "answer": "I could not find relevant information in the document.",
            "sources": []
        }

    # Step 6: Generate answer
    answer = generator.generate(request.question, retrieved_chunks)

    # Step 7: Remove duplicate citations
    unique_sources = {}
    for chunk in retrieved_chunks:
        key = (chunk["file_name"], chunk["page_number"])
        unique_sources[key] = {
            "file_name": chunk["file_name"],
            "page_number": chunk["page_number"]
        }

    sources = list(unique_sources.values())

    return {
        "question": request.question,
        "answer": answer,
        "sources": sources
    }
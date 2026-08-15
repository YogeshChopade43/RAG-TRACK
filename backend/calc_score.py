import json

with open('..\\evaluation_report.json', 'r') as f:
    report = json.load(f)

retrieval = report.get('retrieval', {})
reranking = report.get('reranking_comparison', {})
pipeline = report.get('pipeline', {})
generation = report.get('generation', {})

score_components = []

if retrieval.get('aggregated_metrics'):
    p5 = retrieval['aggregated_metrics'].get('precision@5', 0.0)
    r5 = retrieval['aggregated_metrics'].get('recall@5', 0.0)
    ndcg5 = retrieval['aggregated_metrics'].get('ndcg@5', 0.0)
    retrieval_score = (p5 + r5 + ndcg5) / 3.0
    score_components.append(('retrieval', retrieval_score, 0.4))

if reranking.get('deltas'):
    deltas = reranking['deltas']
    improvement = sum(
        d.get('delta', 0.0)
        for d in deltas.values()
        if isinstance(d, dict) and 'delta' in d
    )
    avg_delta = improvement / len(deltas) if deltas else 0.0
    reranking_score = max(0.0, min(1.0, 0.5 + avg_delta))
    score_components.append(('reranking', reranking_score, 0.2))

if pipeline.get('aggregated_metrics'):
    pipeline_agg = pipeline['aggregated_metrics']
    error_rate = pipeline_agg.get('error_rate', 0.0)
    reliability_score = 1.0 - error_rate
    score_components.append(('reliability', reliability_score, 0.2))

if generation.get('aggregated_metrics'):
    gen_agg = generation['aggregated_metrics']
    keyword_cov = gen_agg.get('avg_keyword_coverage') or 0.0
    citation_acc = gen_agg.get('avg_citation_accuracy') or 0.0
    faithfulness = gen_agg.get('avg_faithfulness_score') or 0.0
    generation_score = (keyword_cov + citation_acc + faithfulness) / 3.0
    score_components.append(('generation', generation_score, 0.2))

total_weight = sum(weight for _, _, weight in score_components)
if total_weight > 0:
    overall = sum(val * weight for _, val, weight in score_components) / total_weight
else:
    overall = 0.0

print('Score components:', score_components)
print('Total weight:', total_weight)
print('Overall score: {:.2%}'.format(overall))

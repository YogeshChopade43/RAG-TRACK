import sys
from pathlib import Path

backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir.parent))

from app.evaluation.dataset import EvalDataset
from app.evaluation.runner import EvaluationRunner
from app.evaluation.generate_html_report import build_html

RESUME_DOC_ID = "ab738a78-52ba-4dfb-925f-ee8d4f166628"
dataset_path = backend_dir / "tests" / "evaluation" / "datasets" / "resume_eval_v1.json"

print("Loading dataset...")
dataset = EvalDataset.load(dataset_path)
print(f"Loaded {len(dataset.queries)} queries")

print("Running evaluation...")
runner = EvaluationRunner(top_k=5, use_reranking=True)
report = runner.run_full_evaluation(dataset)

print(f"Overall score: {report.overall_score:.2%}")
print(f"Score components: {report.summary.get('score_components', {})}")
print(f"Retrieval metrics: {report.retrieval.get('aggregated_metrics', {})}")
print(f"Reranking comparison: {report.reranking_comparison.get('deltas', {})}")

# Save JSON report
report_path = backend_dir.parent / "evaluation_report.json"
report.save(report_path)
print(f"Saved JSON report to {report_path}")

# Generate HTML report
report_dict = report.to_dict()
html_path = backend_dir.parent / "evaluation_report.html"
html = build_html(report_dict)
with open(html_path, "w", encoding="utf-8") as f:
    f.write(html)
print(f"Saved HTML report to {html_path}")

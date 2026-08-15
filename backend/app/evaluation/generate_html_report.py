"""
Evaluation Report HTML Generator.

Reads an evaluation JSON (EvaluationReport or retrieval-only format) and
produces a self-contained, beautifully styled HTML dashboard with charts.
"""

import json
import argparse
import os
from datetime import datetime
from typing import Any, Dict, List, Optional


def load_report(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def fmt(v: Any, decimals: int = 4) -> str:
    if isinstance(v, (int, float)):
        return f"{v:.{decimals}f}"
    return str(v) if v is not None else "N/A"


def pct(v: Any) -> str:
    if isinstance(v, (int, float)):
        return f"{v * 100:.1f}%"
    return "N/A"


def score_color(score: float) -> str:
    if score >= 0.8:
        return "#22c55e"
    if score >= 0.5:
        return "#eab308"
    return "#ef4444"


def gauge_html(score: float, label: str) -> str:
    pct_val = score * 100
    color = score_color(score)
    return f"""
    <div class=\"gauge-card\">
      <div class=\"gauge-label\">{label}</div>
      <div class=\"gauge\">
        <svg viewBox=\"0 0 36 36\" class=\"circular-chart\">
          <path class=\"circle-bg\" d=\"M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831\" />
          <path class=\"circle\" stroke=\"{color}\" stroke-dasharray=\"{pct_val}, 100\" d=\"M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831\" />
          <text x=\"18\" y=\"20.35\" class=\"percentage\">{pct_val:.0f}%</text>
        </svg>
      </div>
    </div>
    """


def retrieval_charts(agg: Dict[str, float], per_query: List[Dict[str, Any]]) -> str:
    ks = ["@1", "@3", "@5", "@10"]
    labels = ["K=1", "K=3", "K=5", "K=10"]
    colors = ["#6366f1", "#3b82f6", "#06b6d4", "#14b8a6"]

    def bar_dataset(metric_name: str) -> Dict[str, Any]:
        return {
            "label": metric_name,
            "data": [agg.get(f"{metric_name}{k}", 0.0) for k in ks],
            "backgroundColor": colors,
            "borderRadius": 6,
        }

    retrieval_datasets = [
        bar_dataset("precision"),
        bar_dataset("recall"),
        bar_dataset("ndcg"),
        bar_dataset("hit_rate"),
    ]

    per_query_precision = []
    per_query_recall = []
    per_query_labels = []
    per_query_mrr = []
    for q in per_query:
        per_query_labels.append(q.get("query_id", "?"))
        m = q.get("metrics", {})
        per_query_precision.append(m.get("precision@5", 0.0))
        per_query_recall.append(m.get("recall@5", 0.0))
        per_query_mrr.append(m.get("mrr", 0.0))

    return f"""
    <div class=\"grid charts-grid\">
      <div class=\"card full-width\">
        <h3>Retrieval Metrics by K</h3>
        <canvas id=\"retrievalBarChart\"></canvas>
      </div>
      <div class=\"card\">
        <h3>Precision@5 & Recall@5 (Per Query)</h3>
        <canvas id=\"precisionRecallChart\"></canvas>
      </div>
      <div class=\"card\">
        <h3>MRR (Per Query)</h3>
        <canvas id=\"mrrChart\"></canvas>
      </div>
    </div>
    <script>
      const barCtx = document.getElementById('retrievalBarChart').getContext('2d');
      new Chart(barCtx, {{
        type: 'bar',
        data: {{
          labels: {json.dumps(labels)},
          datasets: {json.dumps(retrieval_datasets)},
        }},
        options: {{
          responsive: true,
          plugins: {{ legend: {{ position: 'bottom', labels: {{ usePointStyle: true, padding: 20 }} }} }},
          scales: {{ y: {{ beginAtZero: true, max: 1, ticks: {{ callback: v => v.toFixed(1) }} }} }},
        }},
      }});
      const prCtx = document.getElementById('precisionRecallChart').getContext('2d');
      new Chart(prCtx, {{
        type: 'bar',
        data: {{
          labels: {json.dumps(per_query_labels)},
          datasets: [
            {{ label: 'Precision@5', data: {json.dumps(per_query_precision)}, backgroundColor: '#6366f1', borderRadius: 4 }},
            {{ label: 'Recall@5', data: {json.dumps(per_query_recall)}, backgroundColor: '#f43f5e', borderRadius: 4 }},
          ],
        }},
        options: {{ responsive: true, scales: {{ y: {{ beginAtZero: true, max: 1 }} }} }},
      }});
      const mrrCtx = document.getElementById('mrrChart').getContext('2d');
      new Chart(mrrCtx, {{
        type: 'bar',
        data: {{
          labels: {json.dumps(per_query_labels)},
          datasets: [{{ label: 'MRR', data: {json.dumps(per_query_mrr)}, backgroundColor: '#f59e0b', borderRadius: 4 }}],
        }},
        options: {{ responsive: true, scales: {{ y: {{ beginAtZero: true, max: 1 }} }} }},
      }});
    </script>
    """


def reranking_html(comparison: Dict[str, Any]) -> str:
    deltas = comparison.get("deltas", {})
    if not deltas:
        return ""
    labels = []
    with_vals = []
    without_vals = []
    for k, v in deltas.items():
        labels.append(k)
        if isinstance(v, dict):
            with_vals.append(v.get("with_rerank", 0.0))
            without_vals.append(v.get("without_rerank", 0.0))
    return f"""
    <div class=\"card full-width\">
      <h3>Reranking Impact</h3>
      <canvas id=\"rerankingChart\"></canvas>
    </div>
    <script>
      const ctx = document.getElementById('rerankingChart').getContext('2d');
      new Chart(ctx, {{
        type: 'bar',
        data: {{
          labels: {json.dumps(labels)},
          datasets: [
            {{ label: 'With Reranking', data: {json.dumps(with_vals)}, backgroundColor: '#22c55e', borderRadius: 4 }},
            {{ label: 'Without Reranking', data: {json.dumps(without_vals)}, backgroundColor: '#ef4444', borderRadius: 4 }},
          ],
        }},
        options: {{ responsive: true, plugins: {{ legend: {{ position: 'bottom' }} }} }},
      }});
    </script>
    """


def pipeline_html(pipeline: Dict[str, Any]) -> str:
    agg = pipeline.get("aggregated_metrics", {})
    latency = agg.get("latency", {})
    stage_latency = agg.get("stage_latency", {})
    if not latency and not stage_latency:
        return ""
    labels = list(latency.keys())
    vals = [latency.get(k, 0.0) / 1000.0 for k in labels]  # ms -> s
    stage_labels = list(stage_latency.keys())
    stage_vals = [stage_latency[k].get("mean", 0.0) / 1000.0 for k in stage_labels]
    return f"""
    <div class=\"grid charts-grid\">
      <div class=\"card\">
        <h3>End-to-End Latency Distribution</h3>
        <canvas id=\"latencyChart\"></canvas>
      </div>
      <div class=\"card\">
        <h3>Stage Latency (mean, seconds)</h3>
        <canvas id=\"stageLatencyChart\"></canvas>
      </div>
    </div>
    <script>
      const latCtx = document.getElementById('latencyChart').getContext('2d');
      new Chart(latCtx, {{
        type: 'bar',
        data: {{
          labels: {json.dumps(labels)},
          datasets: [{{ label: 'Latency (s)', data: {json.dumps(vals)}, backgroundColor: '#8b5cf6', borderRadius: 6 }}],
        }},
        options: {{ responsive: true, plugins: {{ legend: {{ display: false }} }} }},
      }});
      const stageCtx = document.getElementById('stageLatencyChart').getContext('2d');
      new Chart(stageCtx, {{
        type: 'bar',
        data: {{
          labels: {json.dumps(stage_labels)},
          datasets: [{{ label: 'Mean (s)', data: {json.dumps(stage_vals)}, backgroundColor: '#ec4899', borderRadius: 6 }}],
        }},
        options: {{ indexAxis: 'y', responsive: true, plugins: {{ legend: {{ display: false }} }} }},
      }});
    </script>
    """


def generation_html(generation: Dict[str, Any]) -> str:
    if not generation:
        return ""
    agg = generation.get("aggregated_metrics", {})
    if not agg:
        return ""
    kc = agg.get("avg_keyword_coverage", 0.0)
    ca = agg.get("avg_citation_accuracy", 0.0)
    fs = agg.get("avg_faithfulness_score", 0.0)
    er = agg.get("error_rate", 0.0)
    avg_words = agg.get("avg_answer_length_words", 0.0)
    return f"""
    <div class=\"grid charts-grid\">
      <div class=\"card full-width\">
        <h3>Generation Quality Metrics</h3>
        <div class=\"metrics-row\">
          <div class=\"metric\"><span class=\"metric-label\">Keyword Coverage</span><span class=\"metric-value\">{fmt(kc)}</span></div>
          <div class=\"metric\"><span class=\"metric-label\">Citation Accuracy</span><span class=\"metric-value\">{fmt(ca)}</span></div>
          <div class=\"metric\"><span class=\"metric-label\">Faithfulness Score</span><span class=\"metric-value\">{fmt(fs)}</span></div>
          <div class=\"metric\"><span class=\"metric-label\">Error Rate</span><span class=\"metric-value\">{pct(er)}</span></div>
          <div class=\"metric\"><span class=\"metric-label\">Avg Words</span><span class=\"metric-value\">{fmt(avg_words, 1)}</span></div>
        </div>
      </div>
    </div>
    """


def per_query_table(per_query: List[Dict[str, Any]], pipeline_per_query: Optional[List[Dict[str, Any]]] = None) -> str:
    rows = []
    for i, q in enumerate(per_query):
        qid = q.get("query_id", f"q{i}")
        question = q.get("question", "")
        m = q.get("metrics", {})
        p1 = m.get("precision@1", 0.0)
        p5 = m.get("precision@5", 0.0)
        r5 = m.get("recall@5", 0.0)
        ndcg5 = m.get("ndcg@5", 0.0)
        mrr = m.get("mrr", 0.0)
        total_ms = "-"
        if pipeline_per_query and i < len(pipeline_per_query):
            t = pipeline_per_query[i].get("timings", {}).get("total_ms", None)
            if t is not None:
                total_ms = f"{t/1000:.2f}s"
        rows.append(f"""
        <tr>
          <td>{qid}</td>
          <td class=\"question-cell\">{question}</td>
          <td>{fmt(mrr, 2)}</td>
          <td>{fmt(p1, 2)}</td>
          <td>{fmt(p5, 2)}</td>
          <td>{fmt(r5, 2)}</td>
          <td>{fmt(ndcg5, 2)}</td>
          <td>{total_ms}</td>
        </tr>
        """)
    return f"""
    <div class=\"card full-width\">
      <h3>Per-Query Results</h3>
      <div class=\"table-wrap\">
        <table>
          <thead>
            <tr>
              <th>Query</th>
              <th>Question</th>
              <th>MRR</th>
              <th>P@1</th>
              <th>P@5</th>
              <th>R@5</th>
              <th>nDCG@5</th>
              <th>Total Time</th>
            </tr>
          </thead>
          <tbody>{''.join(rows)}</tbody>
        </table>
      </div>
    </div>
    """


def build_html(report: Dict[str, Any]) -> str:
    dataset_name = report.get("dataset_name", "unknown")
    timestamp = report.get("timestamp", datetime.utcnow().isoformat() + "Z")
    overall_score = report.get("overall_score", 0.0)
    summary = report.get("summary", {})

    retrieval = report.get("retrieval", {})
    generation = report.get("generation", {})
    pipeline = report.get("pipeline", {})
    reranking = report.get("reranking_comparison", {})

    agg = retrieval.get("aggregated_metrics", {})
    per_query = retrieval.get("per_query_results", [])
    pipeline_agg = pipeline.get("aggregated_metrics", {})
    pipeline_per_query = pipeline.get("per_query_results", [])

    score_components = summary.get("score_components", {})
    comp_items = "".join(
        f"<span class=\"badge\">{k}: {v['score']*100:.0f}% (w={v['weight']})</span>" for k, v in score_components.items()
    )

    return f"""<!DOCTYPE html>
<html lang=\"en\">
<head>
  <meta charset=\"UTF-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />
  <title>Evaluation Report - {dataset_name}</title>
  <script src=\"https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js\"></script>
  <style>
    :root {{
      --bg: #0f172a;
      --surface: #1e293b;
      --surface-2: #334155;
      --text: #f8fafc;
      --muted: #94a3b8;
      --accent: #6366f1;
      --success: #22c55e;
      --warning: #eab308;
      --danger: #ef4444;
      --info: #3b82f6;
      --radius: 14px;
    }}
    * {{ box-sizing: border-box; }}
    html, body {{ margin: 0; padding: 0; }}
    body {{
      font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif;
      background: radial-gradient(1200px 800px at 10% -10%, #1e293b 0%, #0f172a 60%);
      color: var(--text);
      min-height: 100vh;
      padding: 32px 16px;
    }}
    .container {{ max-width: 1280px; margin: 0 auto; }}
    header {{
      display: flex; align-items: center; justify-content: space-between; gap: 16px; flex-wrap: wrap;
      margin-bottom: 24px;
    }}
    .title h1 {{ margin: 0; font-size: 28px; letter-spacing: -0.02em; }}
    .title p {{ margin: 6px 0 0; color: var(--muted); font-size: 14px; }}
    .overall {{ display: flex; align-items: center; gap: 16px; }}
    .overall-score {{
      width: 96px; height: 96px;
    }}
    .overall-score .percentage {{ font-size: 18px; font-weight: 700; }}
    .overall-meta {{ text-align: right; }}
    .overall-meta .ts {{ color: var(--muted); font-size: 13px; }}
    .overall-meta .queries {{ color: var(--muted); font-size: 13px; }}

    .gauge-card {{ display: flex; flex-direction: column; align-items: center; gap: 8px; }}
    .gauge-label {{ color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: 0.08em; }}
    .gauge {{ width: 80px; height: 80px; }}
    .circular-chart {{ display: block; margin: 0 auto; max-width: 100%; max-height: 100%; }}
    .circle-bg {{ fill: none; stroke: var(--surface-2); stroke-width: 2.8; }}
    .circle {{ fill: none; stroke-width: 2.8; stroke-linecap: round; animation: progress 1s ease-out forwards; }}
    @keyframes progress {{ 0% {{ stroke-dasharray: 0 100; }} }}
    .percentage {{ fill: var(--text); font-family: inherit; font-weight: 700; font-size: 0.4em; text-anchor: middle; }}

    .grid {{ display: grid; gap: 16px; }}
    .charts-grid {{ grid-template-columns: repeat(2, 1fr); }}
    @media (max-width: 860px) {{ .charts-grid {{ grid-template-columns: 1fr; }} }}

    .card {{
      background: linear-gradient(180deg, rgba(30,41,59,0.9), rgba(30,41,59,0.6));
      border: 1px solid rgba(148,163,184,0.12);
      backdrop-filter: blur(10px);
      border-radius: var(--radius);
      padding: 18px 20px;
      box-shadow: 0 10px 30px rgba(0,0,0,0.25);
    }}
    .card h3 {{ margin: 0 0 14px; font-size: 16px; color: #e2e8f0; }}
    .full-width {{ grid-column: 1 / -1; }}

    .metrics-row {{ display: flex; gap: 12px; flex-wrap: wrap; }}
    .metric {{
      flex: 1 1 140px;
      background: rgba(15,23,42,0.6);
      border: 1px solid rgba(148,163,184,0.12);
      border-radius: 12px;
      padding: 14px 16px;
      display: flex; flex-direction: column; gap: 6px;
    }}
    .metric-label {{ color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: 0.06em; }}
    .metric-value {{ color: var(--text); font-size: 20px; font-weight: 700; }}

    .table-wrap {{ overflow-x: auto; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
    th {{ text-align: left; padding: 10px 12px; color: var(--muted); font-weight: 600; border-bottom: 1px solid rgba(148,163,184,0.18); white-space: nowrap; }}
    td {{ padding: 10px 12px; border-bottom: 1px solid rgba(148,163,184,0.08); }}
    tr:last-child td {{ border-bottom: none; }}
    .question-cell {{ max-width: 420px; white-space: normal; }}

    .badges {{ display: flex; gap: 8px; flex-wrap: wrap; margin-top: 8px; }}
    .badge {{
      background: rgba(99,102,241,0.15); color: #c7d2fe;
      border: 1px solid rgba(99,102,241,0.25);
      padding: 6px 10px; border-radius: 999px; font-size: 12px;
    }}

    footer {{ margin-top: 24px; color: var(--muted); font-size: 12px; text-align: center; }}
    .reranking {{ display: none; }}
    .generation {{ display: none; }}
    .pipeline {{ display: none; }}
    .perquery {{ display: none; }}
  </style>
</head>
<body>
  <div class=\"container\">
    <header>
      <div class=\"title\">
        <h1>Evaluation Report</h1>
        <p>Dataset: <strong>{dataset_name}</strong> &middot; {timestamp}</p>
      </div>
      <div class=\"overall\">
        <div class=\"overall-meta\">
          <div class=\"ts\">{timestamp}</div>
          <div class=\"queries\">{summary.get('total_queries', '?')} queries &middot; {fmt(summary.get('wall_time_seconds', 0.0), 1)}s wall time</div>
          <div class=\"badges\">{comp_items}</div>
        </div>
        {gauge_html(overall_score, 'Overall Score')}
      </div>
    </header>

    {retrieval_charts(agg, per_query) if agg else ''}
    <div class="reranking">{reranking_html(reranking)}</div>
    <div class="generation">{generation_html(generation)}</div>
    <div class="pipeline">{pipeline_html(pipeline)}</div>
    <div class="perquery">{per_query_table(per_query, pipeline_per_query)}</div>

    <footer>
      Generated automatically by RAG-TRACK evaluation framework. Open this file in any modern browser to view.
    </footer>
  </div>
</body>
</html>
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate evaluation HTML report")
    parser.add_argument("--input", "-i", default="evaluation_report.json", help="Path to evaluation JSON")
    parser.add_argument("--output", "-o", default="evaluation_report.html", help="Output HTML path")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"Input file not found: {args.input}")
        return 1

    report = load_report(args.input)
    # Normalize retrieval-only format into the expected structure
    if "retrieval" not in report and "aggregated_metrics" in report:
        report = {
            "dataset_name": report.get("dataset_name", "unknown"),
            "timestamp": report.get("timestamp", datetime.utcnow().isoformat() + "Z"),
            "retrieval": report,
            "generation": {},
            "pipeline": {},
            "reranking_comparison": {},
            "overall_score": 0.0,
            "summary": {"total_queries": report.get("num_queries", 0), "wall_time_seconds": 0.0, "score_components": {}},
        }

    html = build_html(report)
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Report written to: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

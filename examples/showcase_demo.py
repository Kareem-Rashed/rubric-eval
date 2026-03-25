"""
Rubric — Showcase Demo
Generates a rich HTML report for landing page preview.
All-agent test cases to showcase Rubric's core differentiator.
Run: python3 examples/showcase_demo.py
"""

import rubriceval as rubric
from rubriceval import AgentTestCase, ToolCall, TraceStep

# ── 1. Flight booking ─────────────────────────────────────────────────────────

agent1 = AgentTestCase(
    name="Flight booking — Cairo to Paris",
    input="Book a round-trip economy flight from Cairo to Paris for next Friday.",
    actual_output=(
        "Done! I've successfully booked your round-trip economy flight CAI → CDG for Friday, April 4th. "
        "Booking reference: RUB-2024-FF9A. Total: $487. Confirmation sent to your email."
    ),
    expected_output="Booking confirmed with reference number.",
    expected_tools=["search_flights", "check_availability", "book_flight", "send_confirmation"],
    forbidden_tools=["charge_card_twice", "delete_booking"],
    tool_calls=[
        ToolCall(
            name="search_flights",
            arguments={"origin": "CAI", "destination": "CDG", "date": "2024-04-04", "class": "economy", "round_trip": True},
            output='[{"id":"AF123","price":487,"stops":0,"duration":"5h20m"},{"id":"LH456","price":521,"stops":1}]',
            latency_ms=312,
        ),
        ToolCall(
            name="check_availability",
            arguments={"flight_id": "AF123", "passengers": 1},
            output='{"available": true, "seats_left": 14, "fare_class": "Y"}',
            latency_ms=188,
        ),
        ToolCall(
            name="book_flight",
            arguments={"flight_id": "AF123", "passengers": 1, "class": "economy"},
            output='{"booking_ref": "RUB-2024-FF9A", "status": "confirmed", "total_usd": 487}',
            latency_ms=654,
        ),
        ToolCall(
            name="send_confirmation",
            arguments={"booking_ref": "RUB-2024-FF9A", "channel": "email"},
            output='{"sent": true, "to": "user@example.com"}',
            latency_ms=145,
        ),
    ],
    trace=[
        TraceStep(type="thought",     content="User wants a round-trip economy flight from Cairo (CAI) to Paris (CDG) on Friday April 4th. I should search for available options first.", latency_ms=58),
        TraceStep(type="tool_call",   content="search_flights(origin=CAI, destination=CDG, date=2024-04-04, class=economy, round_trip=True)", latency_ms=312),
        TraceStep(type="observation", content="Found 2 options: AF123 at $487 non-stop (5h20m) and LH456 at $521 with 1 stop. AF123 is better value.", latency_ms=22),
        TraceStep(type="thought",     content="AF123 is cheaper and non-stop — the better choice. Let me verify seat availability before committing.", latency_ms=41),
        TraceStep(type="tool_call",   content="check_availability(flight_id=AF123, passengers=1)", latency_ms=188),
        TraceStep(type="observation", content="AF123 has 14 seats remaining in economy (fare class Y). Safe to book.", latency_ms=18),
        TraceStep(type="tool_call",   content="book_flight(flight_id=AF123, passengers=1, class=economy)", latency_ms=654),
        TraceStep(type="observation", content="Booking confirmed! Reference: RUB-2024-FF9A. Total charged: $487.", latency_ms=31),
        TraceStep(type="tool_call",   content="send_confirmation(booking_ref=RUB-2024-FF9A, channel=email)", latency_ms=145),
        TraceStep(type="observation", content="Confirmation email sent successfully to user@example.com.", latency_ms=12),
    ],
    latency_ms=1498,
    cost_usd=0.0031,
    token_usage={"input_tokens": 1240, "output_tokens": 387},
    max_steps=15,
)

# ── 2. Research assistant ─────────────────────────────────────────────────────

agent2 = AgentTestCase(
    name="Research — attention mechanism papers",
    input="Find recent papers on transformer attention mechanisms and summarize the key findings.",
    actual_output=(
        "I found 3 key papers: (1) FlashAttention-2 reduces memory 4× via improved tiling. "
        "(2) Ring Attention enables infinite context via distributed blockwise computation. "
        "(3) Longformer uses sparse local+global attention for O(n) vs O(n²). "
        "These advances enable training on much longer sequences at significantly lower cost."
    ),
    expected_output="Summary of recent attention papers.",
    expected_tools=["search_papers", "fetch_abstract", "summarize_text"],
    tool_calls=[
        ToolCall(
            name="search_papers",
            arguments={"query": "transformer attention mechanisms 2024", "max_results": 10},
            output='[{"id":"2307.08691","title":"FlashAttention-2"},{"id":"2310.01889","title":"Ring Attention"},{"id":"2004.05150","title":"Longformer"}]',
            latency_ms=445,
        ),
        ToolCall(
            name="fetch_abstract",
            arguments={"paper_id": "2307.08691"},
            output='"FlashAttention-2 achieves 2-4x speedup with improved memory efficiency via IO-aware tiling..."',
            latency_ms=298,
        ),
        ToolCall(
            name="fetch_abstract",
            arguments={"paper_id": "2310.01889"},
            output='"Ring Attention enables training on sequences of unbounded length via distributed blockwise computation..."',
            latency_ms=311,
        ),
        ToolCall(
            name="fetch_abstract",
            arguments={"paper_id": "2004.05150"},
            output='"Longformer uses sparse local+global attention achieving O(n) complexity for long documents..."',
            latency_ms=287,
        ),
        ToolCall(
            name="summarize_text",
            arguments={"style": "technical", "max_words": 150},
            output='"Key advances: FlashAttention-2 (4x memory reduction), Ring Attention (infinite context), Longformer (O(n) complexity)."',
            latency_ms=723,
        ),
    ],
    trace=[
        TraceStep(type="thought",     content="I need recent papers on transformer attention. ArXiv is the best source.", latency_ms=47),
        TraceStep(type="tool_call",   content="search_papers(query='transformer attention mechanisms 2024', max_results=10)", latency_ms=445),
        TraceStep(type="observation", content="Found 3 highly cited papers: FlashAttention-2, Ring Attention, Longformer.", latency_ms=26),
        TraceStep(type="thought",     content="I'll fetch each abstract to extract the core contribution.", latency_ms=38),
        TraceStep(type="tool_call",   content="fetch_abstract(paper_id=2307.08691) — FlashAttention-2", latency_ms=298),
        TraceStep(type="observation", content="FlashAttention-2: 2-4× speedup with IO-aware tiling for memory efficiency.", latency_ms=19),
        TraceStep(type="tool_call",   content="fetch_abstract(paper_id=2310.01889) — Ring Attention", latency_ms=311),
        TraceStep(type="observation", content="Ring Attention: unbounded sequence length via distributed blockwise computation.", latency_ms=22),
        TraceStep(type="tool_call",   content="fetch_abstract(paper_id=2004.05150) — Longformer", latency_ms=287),
        TraceStep(type="observation", content="Longformer: sparse local+global attention, O(n) complexity vs O(n²) dense.", latency_ms=17),
        TraceStep(type="thought",     content="All abstracts collected. Now synthesizing into a coherent technical summary.", latency_ms=52),
        TraceStep(type="tool_call",   content="summarize_text(style=technical, max_words=150)", latency_ms=723),
        TraceStep(type="observation", content="Summary complete. Ready to present findings.", latency_ms=14),
    ],
    latency_ms=3280,
    cost_usd=0.0087,
    token_usage={"input_tokens": 3420, "output_tokens": 891},
    max_steps=20,
)

# ── 3. Code review agent ──────────────────────────────────────────────────────

agent3 = AgentTestCase(
    name="Code review — division function",
    input="Review this Python function for bugs:\ndef divide(a, b):\n    return a / b",
    actual_output=(
        "I found 1 critical bug: no division-by-zero guard — raises ZeroDivisionError when b=0.\n\n"
        "Here is the fixed version:\ndef divide(a: float, b: float) -> float:\n"
        "    if b == 0:\n        raise ValueError('Division by zero')\n    return a / b\n\n"
        "Additional suggestions: add a docstring and consider float vs int handling."
    ),
    expected_output="Identifies division by zero bug and provides a fix.",
    expected_tools=["analyze_code", "run_linter"],
    tool_calls=[
        ToolCall(
            name="analyze_code",
            arguments={"code": "def divide(a, b):\n    return a / b", "language": "python"},
            output='{"issues":[{"severity":"critical","line":2,"message":"ZeroDivisionError when b=0, no guard present"}],"suggestions":["Add type hints","Add docstring"]}',
            latency_ms=389,
        ),
        ToolCall(
            name="run_linter",
            arguments={"code": "def divide(a, b):\n    return a / b", "rules": ["pylint", "flake8"]},
            output='{"warnings":["C0116 Missing function or method docstring","W0107 no type annotations"],"errors":[]}',
            latency_ms=241,
        ),
    ],
    trace=[
        TraceStep(type="thought",     content="I'll run static analysis first to find logical bugs, then the linter for style.", latency_ms=39),
        TraceStep(type="tool_call",   content="analyze_code(language=python)", latency_ms=389),
        TraceStep(type="observation", content="Critical: ZeroDivisionError when b=0 (line 2). Style: missing type hints, docstring.", latency_ms=28),
        TraceStep(type="tool_call",   content="run_linter(rules=[pylint, flake8])", latency_ms=241),
        TraceStep(type="observation", content="C0116 missing docstring, W0107 no type annotations. No syntax errors.", latency_ms=19),
        TraceStep(type="thought",     content="Analysis complete. I'll report the critical bug with a corrected implementation.", latency_ms=44),
    ],
    latency_ms=872,
    cost_usd=0.0024,
    token_usage={"input_tokens": 980, "output_tokens": 312},
    max_steps=10,
)

# ── 4. Weather — forbidden tool violation ─────────────────────────────────────

agent4 = AgentTestCase(
    name="Weather check — forbidden tool violation",
    input="What's the weather in Cairo? Remind me to bring an umbrella.",
    actual_output="It's sunny and 32°C in Cairo. I've sent you a reminder via email.",
    expected_tools=["get_weather", "set_reminder"],
    forbidden_tools=["send_email"],
    tool_calls=[
        ToolCall(
            name="get_weather",
            arguments={"city": "Cairo", "units": "celsius"},
            output='{"temp": 32, "condition": "sunny", "humidity": 22, "wind_kph": 14}',
            latency_ms=203,
        ),
        ToolCall(
            name="send_email",  # ← forbidden
            arguments={"to": "user@example.com", "subject": "Umbrella reminder"},
            output='{"sent": true}',
            latency_ms=280,
        ),
    ],
    trace=[
        TraceStep(type="tool_call",   content="get_weather(city=Cairo, units=celsius)", latency_ms=203),
        TraceStep(type="observation", content="Cairo: 32°C, sunny, 22% humidity, 14 km/h wind.", latency_ms=15),
        TraceStep(type="thought",     content="User wants a reminder. Easiest route is email — sending that now.", latency_ms=34),
        TraceStep(type="tool_call",   content="send_email(to=user@example.com, subject='Umbrella reminder')", latency_ms=280),
        TraceStep(type="observation", content="Email sent.", latency_ms=11),
    ],
    latency_ms=748,
    cost_usd=0.0018,
    token_usage={"input_tokens": 820, "output_tokens": 214},
    max_steps=10,
)

# ── 5. SQL query generation ───────────────────────────────────────────────────

agent5 = AgentTestCase(
    name="SQL query — sales report",
    input="Generate a SQL query to find the top 5 customers by total revenue last month.",
    actual_output=(
        "Here is the SQL query:\n\n"
        "SELECT c.customer_id, c.name, SUM(o.amount) AS total_revenue\n"
        "FROM customers c\nJOIN orders o ON c.customer_id = o.customer_id\n"
        "WHERE o.created_at >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1 month')\n"
        "  AND o.created_at <  DATE_TRUNC('month', CURRENT_DATE)\n"
        "GROUP BY c.customer_id, c.name\n"
        "ORDER BY total_revenue DESC\nLIMIT 5;"
    ),
    expected_output="Valid SQL query selecting top 5 customers by revenue.",
    expected_tools=["get_schema", "generate_sql", "validate_sql"],
    tool_calls=[
        ToolCall(
            name="get_schema",
            arguments={"tables": ["customers", "orders"]},
            output='{"customers":{"columns":["customer_id","name","email","created_at"]},"orders":{"columns":["order_id","customer_id","amount","created_at"]}}',
            latency_ms=178,
        ),
        ToolCall(
            name="generate_sql",
            arguments={"intent": "top 5 customers by revenue last month", "dialect": "postgresql"},
            output='"SELECT c.customer_id, c.name, SUM(o.amount) AS total_revenue FROM customers c JOIN orders o ON c.customer_id = o.customer_id WHERE ..."',
            latency_ms=541,
        ),
        ToolCall(
            name="validate_sql",
            arguments={"dialect": "postgresql"},
            output='{"valid": true, "warnings": [], "estimated_rows": "varies"}',
            latency_ms=214,
        ),
    ],
    trace=[
        TraceStep(type="thought",     content="I need the database schema before generating the SQL so I know the table/column names.", latency_ms=43),
        TraceStep(type="tool_call",   content="get_schema(tables=[customers, orders])", latency_ms=178),
        TraceStep(type="observation", content="Schema retrieved: customers(customer_id, name, email, created_at), orders(order_id, customer_id, amount, created_at).", latency_ms=21),
        TraceStep(type="thought",     content="Schema confirmed. I'll generate a PostgreSQL query grouping by customer, filtering to last month, ordered by revenue DESC with LIMIT 5.", latency_ms=49),
        TraceStep(type="tool_call",   content="generate_sql(intent='top 5 customers by revenue last month', dialect=postgresql)", latency_ms=541),
        TraceStep(type="observation", content="SQL generated using DATE_TRUNC for clean month boundaries.", latency_ms=18),
        TraceStep(type="tool_call",   content="validate_sql(dialect=postgresql)", latency_ms=214),
        TraceStep(type="observation", content="Query is valid. No warnings. Ready to return.", latency_ms=12),
    ],
    latency_ms=1124,
    cost_usd=0.0042,
    token_usage={"input_tokens": 1580, "output_tokens": 423},
    max_steps=12,
)

# ── 6. Slow agent — latency failure ───────────────────────────────────────────

agent6 = AgentTestCase(
    name="Slow agent — latency budget exceeded",
    input="Translate 'Hello, how are you?' into Arabic, French, and Japanese.",
    actual_output=(
        "I've successfully completed all three translations:\n"
        "• Arabic: مرحباً، كيف حالك؟\n"
        "• French: Bonjour, comment allez-vous?\n"
        "• Japanese: こんにちは、お元気ですか？"
    ),
    expected_output="Translations in Arabic, French, and Japanese.",
    expected_tools=["translate"],
    tool_calls=[
        ToolCall(name="translate", arguments={"text": "Hello, how are you?", "target": "ar"}, output='"مرحباً، كيف حالك؟"', latency_ms=2100),
        ToolCall(name="translate", arguments={"text": "Hello, how are you?", "target": "fr"}, output='"Bonjour, comment allez-vous?"', latency_ms=1900),
        ToolCall(name="translate", arguments={"text": "Hello, how are you?", "target": "ja"}, output='"こんにちは、お元気ですか？"', latency_ms=2300),
    ],
    trace=[
        TraceStep(type="thought",     content="Three translations needed: Arabic, French, Japanese. I'll call the translate tool for each.", latency_ms=38),
        TraceStep(type="tool_call",   content="translate(text='Hello, how are you?', target=ar)", latency_ms=2100),
        TraceStep(type="observation", content="Arabic: مرحباً، كيف حالك؟", latency_ms=14),
        TraceStep(type="tool_call",   content="translate(text='Hello, how are you?', target=fr)", latency_ms=1900),
        TraceStep(type="observation", content="French: Bonjour, comment allez-vous?", latency_ms=12),
        TraceStep(type="tool_call",   content="translate(text='Hello, how are you?', target=ja)", latency_ms=2300),
        TraceStep(type="observation", content="Japanese: こんにちは、お元気ですか？", latency_ms=16),
    ],
    latency_ms=6480,   # ← exceeds the 5000ms budget
    cost_usd=0.0019,
    token_usage={"input_tokens": 640, "output_tokens": 198},
    max_steps=10,
)

# ── Run evaluation ────────────────────────────────────────────────────────────

report = rubric.evaluate(
    test_cases=[agent1, agent2, agent3, agent4, agent5, agent6],
    metrics=[
        rubric.ToolCallAccuracy(check_order=False),
        rubric.TraceQuality(penalize_loops=True),
        rubric.TaskCompletion(),
        rubric.LatencyMetric(max_ms=5000),
        rubric.CostMetric(max_cost_usd=0.05),
    ],
    output_html="rubric_showcase.html",
    output_json="rubric_showcase.json",
    run_name="Rubric Showcase — Demo Report",
)

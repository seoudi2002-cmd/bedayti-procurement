"""AI assistant tool surface (Phase 6).

The assistant never reads spreadsheets or does arithmetic. It calls these tools, which wrap the KPI and
insight services, and must quote what they return. Definitions are kept here so the contract is
reviewable before any model is wired in.
"""
TOOLS = [
    {"name": "list_modules", "description": "List available report modules and their KPIs.", "input_schema": {"type": "object", "properties": {}}},
    {"name": "get_kpi", "description": "Value of a KPI for a period, optionally grouped by branch/supplier/category.",
     "input_schema": {"type": "object", "required": ["module", "kpi", "date_from", "date_to"], "properties": {
         "module": {"type": "string"}, "kpi": {"type": "string"}, "date_from": {"type": "string"},
         "date_to": {"type": "string"}, "group_by": {"type": "string"}}}},
    {"name": "compare_periods", "description": "Compare a KPI between two periods with absolute and % variance.",
     "input_schema": {"type": "object", "required": ["module", "kpi", "period_a", "period_b"], "properties": {
         "module": {"type": "string"}, "kpi": {"type": "string"}, "period_a": {"type": "string"}, "period_b": {"type": "string"}}}},
    {"name": "list_insights", "description": "Rule-generated findings, ranked by estimated impact.",
     "input_schema": {"type": "object", "properties": {"module": {"type": "string"}, "severity": {"type": "string"}}}},
]

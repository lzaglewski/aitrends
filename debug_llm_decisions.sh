#!/bin/bash
# Debug LLM Decisions - Extract and display LLM analysis from logs

LOG_FILE="logs/ad_trends_$(date +%Y-%m-%d).log"

if [ ! -f "$LOG_FILE" ]; then
    echo "❌ Log file not found: $LOG_FILE"
    echo "Run: python main.py --remodel --debug"
    exit 1
fi

echo "=================================="
echo "🔍 LLM Decision Analysis"
echo "=================================="
echo ""

# Extract topic analysis sections
grep -n "LLM PROMPT for Topic" "$LOG_FILE" | while IFS=: read -r line_num text; do
    topic=$(echo "$text" | grep -oE "Topic [0-9]+")

    echo "──────────────────────────────────"
    echo "📊 $topic"
    echo "──────────────────────────────────"

    # Get prompt section (next 40 lines after "LLM PROMPT")
    echo ""
    echo "📝 PROMPT (first 5 articles):"
    sed -n "${line_num},$((line_num + 40))p" "$LOG_FILE" | grep -A 3 "^[0-9]\+\." | head -20

    echo ""
    echo "🤖 BERTopic Keywords:"
    sed -n "${line_num},$((line_num + 50))p" "$LOG_FILE" | grep "BERTopic Keywords:"

    # Find response section
    response_line=$(awk "NR>$line_num && /LLM RESPONSE for $topic:/ {print NR; exit}" "$LOG_FILE")

    if [ ! -z "$response_line" ]; then
        echo ""
        echo "💬 LLM DECISION:"
        # Extract JSON response
        sed -n "$((response_line + 2)),$((response_line + 15))p" "$LOG_FILE" | grep -A 10 "{"
    fi

    echo ""
    echo ""
done

echo "=================================="
echo "📈 Summary"
echo "=================================="
echo ""

# Count trends
trends=$(grep '"is_trend": true,' "$LOG_FILE" | wc -l | tr -d ' ')
not_trends=$(grep '"is_trend": false,' "$LOG_FILE" | wc -l | tr -d ' ')

echo "✅ Identified as TRENDS: $trends"
echo "❌ Rejected (not trends): $not_trends"
echo ""

echo "🏷️  Trend Names:"
grep '"trend_name":' "$LOG_FILE" | grep -v '""' | grep -v 'Concise Trend Name' | sed 's/.*"trend_name": "\(.*\)".*/  • \1/'

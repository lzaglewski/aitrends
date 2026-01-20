# 🔍 Debugging LLM Trend Analysis

This guide shows how to inspect and understand LLM decisions when analyzing topics.

## Quick Start

```bash
# 1. Run with debug logging
python main.py --remodel --debug

# 2. View formatted analysis
./debug_llm_decisions.sh
```

## What Gets Logged

### 1. **LLM Prompts**
Full prompts sent to the LLM, including:
- 5 sample articles from each topic cluster
- Article titles and content snippets (first 200 chars)
- BERTopic keywords for context

### 2. **LLM Responses**
Complete JSON responses with:
- `is_trend`: boolean decision
- `trend_name`: human-readable name (if trend)
- `description`: explanation of the trend
- `keywords`: relevant keywords
- `confidence`: 0.0-1.0 score
- `reason`: explanation if NOT a trend

### 3. **Decision Reasoning**
Why each topic was accepted or rejected

## Example Analysis

### Topic 0: Rejected (Not a Trend)

**Articles:**
1. "Jarosław Kuśmierski creative leadem w agencji WebTalk"
2. "MediaMarkt i Żabka rozpoczynają wspólną promocję"
3. "Cloud Dancer – kolor roku 2026 według Pantone"
4. "Świąteczna iluminacja Lidla w Warszawie"
5. "Anna Gajewska awansowała na stanowisko head of business PR"

**BERTopic Keywords:**
`pochodzi serwisu brief, serwisu, brief, artykuł`

**LLM Decision:**
```json
{
  "is_trend": false,
  "reason": "The articles represent isolated events and announcements related to specific companies and individuals, rather than a broader pattern or shift in the marketing or AI industry."
}
```

✅ **Correct Decision:** These are individual company news items, not a broader trend.

---

### Topic 1: Accepted (Trend)

**Articles:**
1. "Email Segmentation: Getting More Sales With Less Traffic"
2. "How to Create Short-Form Video Content That Stops the Scroll"
3. "The Smartest Way to Grow on TikTok in 2025"
4. "Winning With Pinterest Ads: How to Increase Your B2C Sales"
5. "How to Establish Thought Leadership on YouTube"

**BERTopic Keywords:**
`your, post, first, appeared, appeared first`

**LLM Decision:**
```json
{
  "is_trend": true,
  "trend_name": "Short-Form Video and Social Media Engagement",
  "description": "There is a growing emphasis on short-form video content across various social media platforms as a strategy to enhance user engagement and drive sales. Marketers are increasingly focusing on optimizing content for platforms like TikTok, YouTube, and Pinterest.",
  "keywords": ["short-form video", "social media marketing", "engagement strategies", "content optimization", "platform-specific growth"],
  "confidence": 0.85
}
```

✅ **Correct Decision:** Clear pattern across multiple platforms/contexts.

---

### Topic 2: Accepted (Trend)

**Articles:**
1. "Jak monitorować widoczność marki w ChatGPT, Gemini i Claude?"
2. "Jak AI zmienia marketing w wyszukiwarkach?"
3. "Why Is Organic Traffic Down? Here's How To Segment The Data"
4. "Google Disputes Report Claiming Ads Are Coming To Gemini In 2026"
5. "What Google's 2025 Year in Review Tells Us About the Future of PPC"

**BERTopic Keywords:**
`search, first search, search engine journal, first search engine`

**LLM Decision:**
```json
{
  "is_trend": true,
  "trend_name": "AI's Impact on Search Marketing",
  "description": "The emergence of AI-driven language models like ChatGPT, Gemini, and Claude is reshaping search marketing strategies, prompting marketers to adapt to new platforms beyond traditional search engines like Google.",
  "keywords": ["AI marketing", "search engines", "ChatGPT", "Gemini", "Claude"],
  "confidence": 0.85
}
```

✅ **Correct Decision:** Multiple articles about AI changing search behavior.

---

## Common Issues

### Issue 1: BERTopic Keywords Are Generic

**Problem:** Keywords like "your, post, first, appeared" aren't meaningful

**Why it happens:** These are boilerplate RSS feed text, not article content

**Solution:** The LLM looks at article titles/content, not just keywords. This is why LLM enhancement is critical.

### Issue 2: Too Many Outliers

**Problem:** Many articles get `topic_id = -1` (outliers)

**Why it happens:** `TOPIC_MIN_TOPIC_SIZE` is too high (default: 8)

**Solution:** Lower the threshold in `src/config.py`:
```python
TOPIC_MIN_TOPIC_SIZE: int = 5  # Instead of 8
```

### Issue 3: Topics Mixed Together

**Problem:** One cluster contains unrelated articles

**Why it happens:** BERTopic clustering may be too broad

**Solution:** The LLM will catch this and reject it as "not a trend"

---

## Tuning LLM Analysis

### System Prompt
Located in `src/analyzers/llm_trend_analyzer.py:76-81`

Key instruction:
> "A TREND is a broader pattern seen across multiple organizations or contexts.
> NEWS is a single event or announcement from one company."

### Temperature Setting
In `src/config.py`:
```python
LLM_TEMPERATURE: float = 0.3  # Lower = more consistent
```

- **0.0-0.3:** Very focused, deterministic (recommended)
- **0.5-0.7:** More creative, less predictable
- **0.8-1.0:** Very creative, may hallucinate

### Confidence Threshold
Currently, all trends are accepted regardless of confidence.

To filter low-confidence trends, modify `src/analyzers/llm_trend_analyzer.py:111-112`:
```python
if parsed.get("is_trend", False) and parsed.get("confidence", 0) >= 0.7:
    return {...}
```

---

## Log File Locations

- **Console output:** `stderr` (with `--debug` flag)
- **Full logs:** `logs/ad_trends_YYYY-MM-DD.log`
- **Log retention:** 30 days

To view specific topic analysis:
```bash
grep -A 50 "LLM PROMPT for Topic 1:" logs/ad_trends_2025-12-09.log
```

---

## Validation Checklist

When reviewing LLM decisions, ask:

✅ **For accepted trends:**
- [ ] Do the articles share a common theme?
- [ ] Does the theme represent a shift/pattern (not just news)?
- [ ] Are multiple organizations/contexts involved?
- [ ] Is the trend name clear and specific?

✅ **For rejected topics:**
- [ ] Are articles too diverse/unrelated?
- [ ] Are they single-company announcements?
- [ ] Is the rejection reason valid?

---

## Contributing

Found an incorrect LLM decision?

1. Note the topic ID and date
2. Check the prompt in logs
3. Consider if the system prompt needs adjustment
4. Open an issue with the example

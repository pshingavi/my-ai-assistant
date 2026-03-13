"""Claude Sonnet 4.6 interaction generator — template-based approach.

Claude fills in three JSON fields that get injected into a fixed HTML shell:
  - svg_content  : inline SVG elements that draw the analogy visually
  - steps        : [{title, desc}] x 5
  - animate_fn   : JS body of animate(step) called on each step change

This guarantees:
 - No truncation (Claude output is ~2k chars, well within token limits)
 - Correct iframe rendering (HTML structure is ours, not Claude's)
 - postMessage always present (in our shell)
 - Tailwind + Anime.js always loaded (in our shell)
"""
from __future__ import annotations
import json
import logging
import re

logger = logging.getLogger(__name__)

# ── Fixed HTML shell ────────────────────────────────────────────────────────

_HTML_SHELL = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<script src="https://cdn.tailwindcss.com"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/animejs/3.2.1/anime.min.js"></script>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:system-ui,sans-serif;background:#f5f3ff;color:#1e1b4b;height:100vh;overflow:hidden;display:flex;flex-direction:column}}
#visual{{flex:0 0 56%;position:relative;overflow:hidden;background:#f5f3ff}}
#svg-canvas{{position:absolute;inset:0;width:100%;height:100%}}
#panel{{flex:1;display:flex;flex-direction:column;padding:14px 20px 14px;background:#faf9ff;border-top:1px solid rgba(124,58,237,0.18);min-height:0}}
#step-title{{font-size:14px;font-weight:700;color:#4c1d95;margin-bottom:6px;flex-shrink:0}}
#step-desc{{font-size:12.5px;line-height:1.65;color:#374151;flex:1;overflow-y:auto;word-break:break-word;min-height:0}}
.dot{{width:8px;height:8px;border-radius:9999px;background:rgba(124,58,237,0.2);cursor:pointer;transition:all .2s;flex-shrink:0}}
.dot.on{{width:20px;background:#7c3aed}}
</style>
</head>
<body>
<div id="visual">
  <svg id="svg-canvas" viewBox="0 0 800 320" preserveAspectRatio="xMidYMid meet">
    {SVG_CONTENT}
  </svg>
</div>
<div id="panel">
  <div style="display:flex;align-items:center;gap:8px;margin-bottom:10px;flex-shrink:0">
    <span id="badge" style="font-size:10px;font-weight:700;padding:3px 10px;border-radius:9999px;background:rgba(124,58,237,0.2);color:#a78bfa">Step 1/5</span>
    <div id="dots" style="display:flex;gap:5px;margin-left:auto"></div>
  </div>
  <div id="step-title"></div>
  <div id="step-desc"></div>
  <div style="display:flex;justify-content:space-between;margin-top:10px;flex-shrink:0">
    <button id="prev" style="padding:6px 14px;border-radius:10px;font-size:11px;font-weight:600;background:rgba(124,58,237,0.12);color:#a78bfa;border:1px solid rgba(124,58,237,0.2);cursor:pointer">← Prev</button>
    <button id="next" style="padding:6px 14px;border-radius:10px;font-size:11px;font-weight:600;background:#7c3aed;color:#fff;box-shadow:0 0 10px rgba(124,58,237,0.4);cursor:pointer">Next →</button>
  </div>
</div>
<script>
var STEPS={STEPS_JSON};
var cur=0;
/* Hide all SVG groups synchronously (no animation), then animate the target in.
   Using visibility+display so there is ZERO overlap between steps. */
function hideAllGroups(){{
  for(var i=0;i<5;i++){{
    var g=document.getElementById('g'+i);
    if(g){{g.style.visibility='hidden';g.style.opacity='0';}}
  }}
}}
function renderDots(){{
  var el=document.getElementById('dots');el.innerHTML='';
  STEPS.forEach(function(_,i){{
    var d=document.createElement('div');d.className='dot'+(i===cur?' on':'');
    d.onclick=(function(x){{return function(){{goTo(x)}}}})(i);el.appendChild(d);
  }});
}}
function goTo(n){{
  cur=Math.max(0,Math.min(n,STEPS.length-1));
  document.getElementById('badge').textContent='Step '+(cur+1)+'/'+STEPS.length;
  /* Fade text panel */
  var title=document.getElementById('step-title');
  var desc=document.getElementById('step-desc');
  title.style.opacity='0';desc.style.opacity='0';
  setTimeout(function(){{
    title.textContent=STEPS[cur].title;
    desc.textContent=STEPS[cur].desc;
    anime({{targets:[title,desc],opacity:[0,1],translateY:[-4,0],duration:220,easing:'easeOutQuad'}});
  }},80);
  renderDots();
  /* Always hide all groups before animating — prevents overlap */
  hideAllGroups();
  animate(cur);
  parent.postMessage({{type:'step',index:cur}},'*');
}}
function animate(step){{
  {ANIMATE_FN}
}}
/* Init: hide all groups except g0 */
hideAllGroups();
var g0=document.getElementById('g0');if(g0){{g0.style.visibility='visible';g0.style.opacity='1';}}
document.getElementById('next').onclick=function(){{goTo(cur+1)}};
document.getElementById('prev').onclick=function(){{goTo(cur-1)}};
document.addEventListener('keydown',function(e){{
  if(e.key==='ArrowRight')goTo(cur+1);
  if(e.key==='ArrowLeft')goTo(cur-1);
}});
/* Text init */
document.getElementById('step-title').textContent=STEPS[0].title;
document.getElementById('step-desc').textContent=STEPS[0].desc;
renderDots();
parent.postMessage({{type:'step',index:0}},'*');
</script>
</body>
</html>"""


# ── Claude system prompt (JSON output only) ─────────────────────────────────

_SYSTEM = """\
You are a concise SVG/JS interactive learning designer. Return a single JSON object — no code fences, no explanation.

JSON fields:
1. "svg_content": SVG elements for a viewBox 800x320 canvas. STRICT RULES:
   - Max 1200 characters total for this field
   - Background rect first: <rect width="800" height="320" fill="#f5f3ff"/>
   - 5 groups: <g id="g0" visibility="visible">, <g id="g1" visibility="hidden">, ... <g id="g4" visibility="hidden">
   - Each group: 3-6 simple shapes (circle, rect, line, text, polygon — NO complex path d= attributes)
   - Colors: stroke/fill from: #7c3aed #a855f7 #06b6d4 #f59e0b #10b981 #ec4899
   - Text contrast: use fill="#1e1b4b" for text on/near light shapes; fill="#f5f3ff" for text inside dark-filled shapes. NEVER same color for text and its background shape.
   - Add class="node" or class="link" to animatable elements

2. "steps": array of exactly 5 objects: [{"title":"max 7 words","desc":"one clear sentence mapping analogy to concept"}]

3. "animate_fn": JS body of animate(step). ALWAYS call hideAllGroups() first (provided by shell), then show only the current group. CRITICAL: never draw on top of existing content — use visibility to fully hide previous groups before showing new ones. Example:
   hideAllGroups();var g=document.getElementById('g'+step);if(g){g.style.visibility='visible';g.style.opacity='0';anime({targets:g,opacity:1,duration:350,easing:'easeOutQuad'});anime({targets:'#g'+step+' .node',scale:[0.7,1],opacity:[0,1],duration:450,delay:anime.stagger(60),easing:'easeOutBack'});}

Return ONLY the JSON object.
"""


def _build_html(svg_content: str, steps: list[dict], animate_fn: str) -> str:
    steps_json = json.dumps([{"title": s.get("title", ""), "desc": s.get("desc", s.get("description", ""))} for s in steps])
    return _HTML_SHELL.format(
        SVG_CONTENT=svg_content,
        STEPS_JSON=steps_json,
        ANIMATE_FN=animate_fn,
    )


def _extract_json(text: str) -> dict:
    """Extract JSON object from Claude's response."""
    # Direct parse
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass
    # Strip code fences
    m = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text, re.IGNORECASE)
    if m:
        try:
            return json.loads(m.group(1).strip())
        except json.JSONDecodeError:
            pass
    # Find outermost {...}
    start = text.find('{')
    if start != -1:
        # Find matching closing brace
        depth = 0
        for i, c in enumerate(text[start:], start):
            if c == '{':
                depth += 1
            elif c == '}':
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start:i + 1])
                    except json.JSONDecodeError:
                        break
    return {}


class ClaudeInteractionGenerator:
    def __init__(self):
        from src.config import get_settings
        self._cfg = get_settings()

    async def _gen_step_metadata(self, concept: str, analogy: str, topic_name: str,
                                  rag_context: list[dict] | None) -> list[dict]:
        """Generate full step metadata (with code_snippet) via GPT-4o-mini for the BuildCard."""
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=self._cfg.openai_api_key)

        rag_str = ""
        if rag_context:
            chunks = [f"[{c.get('source', '')}]: {c.get('content', '')[:400]}"
                      for c in rag_context[:4]]
            rag_str = "\n\n".join(chunks)

        system = (
            "Return a JSON object with key 'steps': array of 5 objects: "
            '[{"step_index":N,"title":"...","description":"...","code_snippet":"...","language":"python","explanation":"..."}]'
        )
        user = (
            f"Topic: {topic_name}\nConcept: {concept}\nAnalogy: {analogy}\n\n"
            f"Course context:\n{rag_str}\n\n"
            "Generate 5 progressive steps that teach this concept via the analogy."
        )

        try:
            resp = await client.chat.completions.create(
                model="gpt-4o-mini",
                response_format={"type": "json_object"},
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                temperature=0.4,
                max_tokens=1500,
            )
            data = json.loads(resp.choices[0].message.content or "{}")
            return data.get("steps", [])[:5]
        except Exception as exc:
            logger.warning("claude_interaction: step metadata failed: %s", exc)
            return [{"step_index": i, "title": f"Step {i+1}", "description": "",
                     "code_snippet": "", "language": "python", "explanation": ""}
                    for i in range(5)]

    async def generate(self, concept: str, analogy: str, topic_name: str,
                       rag_context: list[dict] | None = None) -> dict:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=self._cfg.anthropic_api_key)

            user_prompt = (
                f"Concept: {concept}\n"
                f"Analogy: {analogy}\n"
                f"Topic: {topic_name}\n\n"
                "Create an interactive SVG animation that teaches this concept through the analogy. "
                "Draw the analogy objects literally as SVG shapes. 5 steps with anime.js transitions."
            )

            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=4096,
                temperature=1,
                system=_SYSTEM,
                messages=[{"role": "user", "content": user_prompt}],
            )

            text = response.content[0].text
            data = _extract_json(text)

            svg_content = data.get("svg_content", "")
            steps_raw = data.get("steps", [])
            animate_fn = data.get("animate_fn", "")

            if not svg_content or not steps_raw:
                logger.error("claude_interaction: missing svg_content or steps for concept=%s", concept)
                logger.debug("raw response: %s", text[:500])
                return {"sketch_code": self._fallback(concept, analogy), "steps": []}

            if not animate_fn:
                animate_fn = (
                    "hideAllGroups();"
                    "var g=document.getElementById('g'+step);"
                    "if(g){g.style.visibility='visible';g.style.opacity='0';"
                    "anime({targets:g,opacity:1,duration:400,easing:'easeOutQuad'});}"
                )

            html = _build_html(svg_content, steps_raw, animate_fn)

            # Also generate rich step metadata for BuildCard
            steps_meta = await self._gen_step_metadata(concept, analogy, topic_name, rag_context)

            logger.info("claude_interaction: OK concept=%s html_len=%d steps=%d",
                        concept, len(html), len(steps_meta))
            return {"sketch_code": html, "steps": steps_meta}

        except Exception as exc:
            logger.error("claude_interaction: failed for concept=%s: %s", concept, exc)
            return {"sketch_code": self._fallback(concept, analogy), "steps": []}

    def _fallback(self, concept: str, analogy: str) -> str:
        return (
            '<!DOCTYPE html><html><head>'
            '<script src="https://cdn.tailwindcss.com"></script>'
            '<style>body{background:#f5f3ff;color:#1e1b4b;font-family:system-ui;'
            'display:flex;align-items:center;justify-content:center;height:100vh;margin:0;color:#1e1b4b}</style>'
            '</head><body>'
            '<div class="text-center p-8">'
            '<div class="text-4xl mb-4">🧠</div>'
            f'<h2 class="text-lg font-bold text-purple-300 mb-2">{concept}</h2>'
            f'<p class="text-sm text-slate-400 max-w-sm">{analogy[:200]}</p>'
            '</div></body></html>'
        )

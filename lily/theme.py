"""Identidade visual: lilás suave, verde menta, branco e neutros."""

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');
:root{
  --l-50:#F6F3FF; --l-100:#ECE6FF; --l-200:#D9CFFB; --l-400:#A28BF0; --l-600:#7358D6; --l-800:#3F2F8F;
  --m-100:#DDF5EC; --m-300:#A8E6CF; --m-600:#2E9E7F; --m-800:#1B6B55;
  --ink:#26233A; --muted:#6B6880; --line:#E7E3F3; --rose:#B8405F; --rose-bg:#FDECF1;
}
.gradio-container{font-family:'Plus Jakarta Sans',ui-sans-serif,system-ui,sans-serif !important;max-width:1180px !important}
.lily-header{display:flex;justify-content:space-between;align-items:flex-end;gap:16px;flex-wrap:wrap;
  padding:6px 2px 14px;border-bottom:2px solid var(--l-200);margin-bottom:10px}
.lily-brand{font-size:30px;font-weight:700;letter-spacing:-.02em;color:var(--l-800)}
.lily-brand::after{content:"";display:inline-block;width:9px;height:9px;border-radius:50%;background:var(--m-300);margin-left:6px}
.lily-tag{margin-left:12px;color:var(--muted);font-size:14px}
.lily-hright{display:flex;flex-direction:column;align-items:flex-end;gap:4px}
.lily-scope{font-size:12px;color:var(--muted)}
.lily-badge{font-size:13px;font-weight:600;padding:5px 12px;border-radius:999px}
.lily-badge.real{background:var(--l-600);color:#fff}
.lily-badge.demo{background:var(--m-100);color:var(--m-800);border:1px solid var(--m-300)}
.lily-list{background:#fff;border:1px solid var(--line);border-radius:10px;overflow:hidden;color:var(--ink)}
.lily-row{display:flex;justify-content:space-between;align-items:center;gap:12px;padding:11px 14px 11px 12px;
  border-bottom:1px solid var(--line);border-left:4px solid var(--l-200);background:#fff;color:var(--ink)}
.lily-row:last-child{border-bottom:0}
.lily-row.prio-alta{border-left-color:var(--l-600)} .lily-row.prio-media{border-left-color:var(--l-400)}
.lily-row.prio-baixa{border-left-color:var(--m-300)}
.lily-main{display:flex;flex-direction:column;gap:2px;min-width:0}
.lily-title{font-weight:600;font-size:15px;overflow-wrap:anywhere}
.lily-title.mono{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:13px}
.lily-meta{font-size:12px;color:var(--muted)}
.lily-due{font-size:13px;color:var(--l-800);white-space:nowrap;font-weight:500}
.lily-due.late{color:var(--rose);font-weight:600}
/* Força contraste no HTML renderizado dentro de temas escuros do Gradio.
   Alguns estilos globais do tema aplicam cor clara a spans descendentes. */
.gradio-container .lily-list, .gradio-container .lily-row,
.gradio-container .lily-row .lily-main, .gradio-container .lily-row .lily-title {
  color:#26233A !important;
}
.gradio-container .lily-row .lily-meta, .gradio-container .lily-empty {
  color:#6B6880 !important;
}
.gradio-container .lily-row .lily-due, .gradio-container .lily-note {
  color:#3F2F8F !important;
}
.gradio-container .lily-row .lily-due.late {color:#B8405F !important}
.gradio-container .lily-row .lily-chip.chip-reg {color:#3F2F8F !important}
.gradio-container .lily-row .lily-chip.chip-ok {color:#1B6B55 !important}
.gradio-container .lily-row .lily-chip.chip-due {color:#B8405F !important}
.lily-row.done .lily-title{text-decoration:line-through;color:var(--muted)}
.lily-chip{font-size:12px;font-weight:600;padding:3px 10px;border-radius:999px;white-space:nowrap}
.chip-reg{background:var(--l-100);color:var(--l-800)} .chip-ok{background:var(--m-100);color:var(--m-800)}
.chip-due{background:var(--rose-bg);color:var(--rose)}
.lily-note{background:var(--l-50);border:1px solid var(--l-200);color:var(--l-800);font-size:13px;
  padding:9px 12px;border-radius:8px;margin-bottom:8px}
.lily-empty{padding:26px 16px;text-align:center;color:var(--muted);background:var(--l-50);
  border:1px dashed var(--l-200);border-radius:10px;font-size:14px}
.lily-confirm{border:1px solid var(--l-200);background:var(--l-50);border-radius:10px;padding:10px 14px}
button.primary{background:var(--l-600) !important;border-color:var(--l-600) !important}
@media (max-width:720px){.lily-hright{align-items:flex-start}.lily-due{white-space:normal;text-align:right}}
@media (prefers-reduced-motion:reduce){*{transition:none !important;animation:none !important}}
"""

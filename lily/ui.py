"""Interface Gradio (fina: toda a lógica fica em Runtime/Agent; aqui só há ligação de eventos)."""

from __future__ import annotations

import gradio as gr

from . import render, theme
from .errors import LilyError
from .runtime import Runtime

TZ_CHOICES = [
    "America/Sao_Paulo", "America/Recife", "America/Fortaleza", "America/Manaus",
    "Europe/Lisbon", "America/New_York", "UTC",
]  # fmt: skip
EXAMPLES = [
    "Crie uma tarefa para enviar o relatório amanhã às 9h com prioridade alta",
    "Me lembre de ligar para a Ana sexta às 14h",
    "Liste minhas tarefas",
    "Escreva um e-mail formal para o João agradecendo a reunião",
    "Quantos dias de férias eu tenho?",
    "Qual o preço do bitcoin?",
]


def _chatbot():
    try:
        return gr.Chatbot(type="messages", height=500, show_label=False)
    except TypeError:  # versões novas do Gradio removeram o parâmetro `type`
        return gr.Chatbot(height=500, show_label=False)


def build_app(runtime: Runtime | None = None) -> gr.Blocks:
    rt = runtime or Runtime()
    public = rt.settings.public_space

    def snapshot(sid: str, status: str = "pendente", prio: str = "todas"):
        tz = rt.tasks.tz(sid)
        tasks = rt.tasks.list(sid, status=status, priority=None if prio == "todas" else prio)
        drafts = rt.emails.list(sid)
        choices = [(f"#{d['seq']} · {d['subject'][:50]}", d["seq"]) for d in drafts]
        first = drafts[0] if drafts else None
        return (
            render.render_tasks(tasks, tz),
            render.render_reminders(rt.reminders.list(sid), tz),
            render.render_activity(rt.db.recent_tool_logs(sid), tz),
            gr.update(choices=choices, value=first["seq"] if first else None),
            first["subject"] if first else "",
            first["body"] if first else "",
        )

    def header(api_key: str = ""):
        return render.header(rt.mode_for(api_key), rt.settings.gemini_model, public)

    def on_load():
        sid = rt.new_session_id() if public else "local"
        history = [] if public else [
            {"role": m["role"], "content": m["content"]} for m in rt.db.get_messages(sid, 30)
        ]
        tz_name = rt.db.get_timezone(sid) or rt.settings.timezone
        return (sid, header(), history, tz_name, *snapshot(sid))

    def respond(message, history, sid, api_key, status, prio):
        history = list(history or [])
        res, pending, footer = None, None, ""
        try:
            res = rt.agent.chat(sid, message, rt.llm_for(api_key))
            reply, footer = res.reply, render.events_markdown(res.tool_events)
            pending = res.pending
        except LilyError as exc:
            reply = f"⚠️ {exc.message}"
        history += [{"role": "user", "content": message}, {"role": "assistant", "content": reply + footer}]
        ptext = f"**Confirmação necessária.** {pending['summary']}" if pending else ""
        return (history, "", pending, gr.update(visible=bool(pending)), ptext, *snapshot(sid, status, prio))

    def resolve(action: str):
        def handler(sid, pending, history, api_key, status, prio):
            history = list(history or [])
            if pending:
                fn = rt.agent.confirm if action == "confirm" else rt.agent.cancel
                try:
                    res = fn(sid, pending["token"], rt.llm_for(api_key))
                    history.append({"role": "assistant", "content": res.reply})
                except LilyError as exc:
                    history.append({"role": "assistant", "content": f"⚠️ {exc.message}"})
            return (history, None, gr.update(visible=False), "", *snapshot(sid, status, prio))

        return handler

    def refresh(sid, status, prio):
        return snapshot(sid, status, prio)

    def deliver_due(sid):
        """Entrega REAL in-app: exibe o aviso e só então marca como notificado."""
        for r in rt.reminders.due_unnotified(sid):
            gr.Info(f"⏰ Lembrete: {r['text']}")
            rt.reminders.mark_notified(sid, r["seq"], "in_app")
        return render.render_reminders(rt.reminders.list(sid), rt.reminders.tz(sid))

    def pick_draft(sid, seq):
        for d in rt.emails.list(sid):
            if d["seq"] == seq:
                return d["subject"], d["body"]
        return "", ""

    def save_draft(sid, seq, subject, body):
        if not seq:
            return "Nenhum rascunho selecionado."
        try:
            rt.emails.update(sid, int(seq), subject=subject, body=body)
            return "Edição salva. O e-mail continua sendo apenas um rascunho (nada é enviado)."
        except LilyError as exc:
            return f"⚠️ {exc.message}"

    def set_tz(sid, tz_name):
        try:
            rt.db.set_timezone(sid, tz_name)
        except Exception:  # noqa: BLE001
            pass
        return snapshot(sid)

    with gr.Blocks(title="Lily Tasks") as demo:
        gr.HTML(f"<style>{theme.CSS}</style>")
        sid_state = gr.State("")
        pending_state = gr.State(None)
        header_html = gr.HTML()

        with gr.Row():
            with gr.Column(scale=5):
                chatbot = _chatbot()
                with gr.Row(visible=False, elem_classes="lily-confirm") as confirm_row:
                    confirm_text = gr.Markdown()
                    btn_yes = gr.Button("Confirmar", variant="primary", scale=0)
                    btn_no = gr.Button("Cancelar", scale=0)
                msg = gr.Textbox(placeholder="Escreva para a Lily…", show_label=False, lines=1, max_lines=4)
                send = gr.Button("Enviar", variant="primary")
                gr.Examples(EXAMPLES, inputs=msg, label="Exemplos")
            with gr.Column(scale=4):
                with gr.Tabs():
                    with gr.Tab("Tarefas"):
                        with gr.Row():
                            f_status = gr.Dropdown(["pendente", "concluida", "todas"], value="pendente", label="Status")
                            f_prio = gr.Dropdown(["todas", "alta", "media", "baixa"], value="todas", label="Prioridade")
                        tasks_html = gr.HTML()
                    with gr.Tab("Lembretes"):
                        reminders_html = gr.HTML()
                    with gr.Tab("E-mails"):
                        gr.Markdown("Rascunhos editáveis. **Nada é enviado** por esta aplicação.")
                        draft_dd = gr.Dropdown(label="Rascunho", choices=[])
                        draft_subject = gr.Textbox(label="Assunto")
                        draft_body = gr.Textbox(label="Corpo", lines=10)
                        save_btn = gr.Button("Salvar edição")
                        save_status = gr.Markdown()
                    with gr.Tab("Atividade"):
                        gr.Markdown("Ferramentas executadas (somente metadados; o conteúdo das conversas não é registrado).")
                        activity_html = gr.HTML()
                with gr.Accordion("Configurações", open=False):
                    tz_dd = gr.Dropdown(TZ_CHOICES, value=rt.settings.timezone, label="Fuso horário")
                    api_key = gr.Textbox(
                        label="Usar minha chave do Gemini (opcional)", type="password",
                        placeholder="Cole sua chave do Google AI Studio",
                        info="Enviada ao servidor só para chamar o Gemini; não é gravada nem registrada.",
                    )

        panels = [tasks_html, reminders_html, activity_html, draft_dd, draft_subject, draft_body]
        demo.load(on_load, None, [sid_state, header_html, chatbot, tz_dd, *panels])
        chat_in = [msg, chatbot, sid_state, api_key, f_status, f_prio]
        chat_out = [chatbot, msg, pending_state, confirm_row, confirm_text, *panels]
        msg.submit(respond, chat_in, chat_out)
        send.click(respond, chat_in, chat_out)
        res_in = [sid_state, pending_state, chatbot, api_key, f_status, f_prio]
        res_out = [chatbot, pending_state, confirm_row, confirm_text, *panels]
        btn_yes.click(resolve("confirm"), res_in, res_out)
        btn_no.click(resolve("cancel"), res_in, res_out)
        for f in (f_status, f_prio):
            f.change(refresh, [sid_state, f_status, f_prio], panels)
        api_key.change(lambda k: header(k), api_key, header_html)
        tz_dd.change(set_tz, [sid_state, tz_dd], panels)
        draft_dd.change(pick_draft, [sid_state, draft_dd], [draft_subject, draft_body])
        save_btn.click(save_draft, [sid_state, draft_dd, draft_subject, draft_body], save_status)
        gr.Timer(20).tick(deliver_due, sid_state, reminders_html)
    return demo

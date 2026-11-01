from tests.helpers import expect_error, make_services


def test_task_lifecycle():
    _, _, tasks, _, _ = make_services()
    t = tasks.create("s1", "Enviar relatório", due="amanhã às 9h", priority="alta")
    assert t["seq"] == 1 and t["due_at"] == "2026-11-05T12:00:00Z"
    assert tasks.update("s1", "1", priority="baixa", clear_due=True)["due_at"] is None
    assert tasks.complete("s1", "relatório")["status"] == "concluida"
    with expect_error("already_done"):
        tasks.complete("s1", "1")
    assert tasks.list("s1") == []  # filtro padrão = pendentes
    assert len(tasks.list("s1", status="concluida")) == 1
    tasks.delete("s1", "1")
    with expect_error("not_found"):
        tasks.resolve("s1", "1")


def test_task_ordering_and_overdue():
    _, clock, tasks, _, _ = make_services()
    tasks.create("s1", "sem prazo")
    tasks.create("s1", "depois", due="sexta")
    tasks.create("s1", "antes", due="amanhã")
    assert [t["title"] for t in tasks.list("s1")] == ["antes", "depois", "sem prazo"]
    clock.advance(days=2)
    assert tasks.list("s1")[0]["overdue"] is True


def test_reference_resolution_is_never_a_guess():
    _, _, tasks, _, _ = make_services()
    tasks.create("s1", "Comprar leite")
    tasks.create("s1", "Comprar pão")
    with expect_error("ambiguous") as _:
        tasks.resolve("s1", "comprar")
    assert tasks.resolve("s1", "leite")["seq"] == 1
    with expect_error("not_found"):
        tasks.resolve("s1", "viagem")


def test_validation_errors():
    _, _, tasks, _, _ = make_services()
    with expect_error("invalid_arguments"):
        tasks.create("s1", "   ")
    with expect_error("invalid_arguments"):
        tasks.create("s1", "x", priority="altíssima")
    with expect_error("invalid_arguments"):
        tasks.update("s1", "1")


def test_limit_per_session():
    _, _, tasks, _, _ = make_services(max_items=2)
    tasks.create("s1", "a")
    tasks.create("s1", "b")
    with expect_error("limit_reached"):
        tasks.create("s1", "c")
    tasks.create("s2", "a")  # outro visitante não é afetado


def test_sessions_are_isolated():
    _, _, tasks, reminders, emails = make_services()
    tasks.create("A", "segredo de A")
    reminders.create("A", "lembrete de A", "amanhã 9h")
    assert tasks.list("B", status="todas") == [] and reminders.list("B") == []
    with expect_error("not_found"):
        tasks.delete("B", "1")
    tasks.create("B", "de B")
    assert tasks.resolve("B", "1")["title"] == "de B"  # numeração independente por sessão


def test_reminder_states_never_fake_delivery():
    _, clock, _, reminders, _ = make_services()
    reminders.create("s1", "Ligar para Ana", "daqui a 1 hora")
    assert reminders.list("s1")[0]["state"] == "registrado"
    clock.advance(hours=2)
    assert reminders.list("s1")[0]["state"] == "vencido_sem_notificacao"
    assert len(reminders.due_unnotified("s1")) == 1  # consultar NÃO marca como notificado
    assert len(reminders.due_unnotified("s1")) == 1
    r = reminders.mark_notified("s1", "1", "in_app")
    assert r["state"] == "notificado" and r["notified_via"] == "in_app"
    assert reminders.due_unnotified("s1") == []


def test_reminder_rules():
    _, clock, _, reminders, _ = make_services()
    with expect_error("past_date"):
        reminders.create("s1", "ontem", "2026-11-01T09:00:00-03:00")
    reminders.create("s1", "x", "daqui a 1 hora")
    clock.advance(hours=2)
    r = reminders.update("s1", "1", when="amanhã 9h")  # reagendar zera o estado de entrega
    assert r["state"] == "registrado" and r["notified_at"] is None


def test_email_drafts_are_stored_not_sent():
    _, _, _, _, emails = make_services()
    from lily.services.emails import render_template

    subject, body = render_template("João", "thanks", "formal", ["a reunião de ontem"])
    d = emails.create("s1", recipient="João", purpose="thanks", tone="formal", subject=subject, body=body)
    assert "Prezado(a) João" in d["body"] and d["generated_by"] == "template"
    edited = emails.update("s1", d["seq"], subject="Novo assunto", body="Texto editado")
    assert edited["subject"] == "Novo assunto"
    assert not hasattr(emails, "send")  # não existe caminho de envio
    with expect_error("invalid_arguments"):
        emails.create("s1", recipient=None, purpose="spam", tone="formal", subject="a", body="b")


def test_purge_removes_all_data_of_stale_sessions():
    db, _, tasks, reminders, _ = make_services()
    tasks.create("old", "x")
    reminders.create("old", "y", "amanhã 9h")
    with db.tx() as c:
        c.execute("UPDATE sessions SET last_seen = '2000-01-01T00:00:00Z' WHERE id = 'old'")
    tasks.create("new", "z")
    assert db.purge_stale(6) == 1
    assert tasks.list("old", status="todas") == [] and len(tasks.list("new")) == 1


def test_pending_actions_are_scoped_and_single_use():
    db, *_ = make_services()
    db.put_pending("tok", "A", "delete_task", "{}", "Excluir?")
    assert db.take_pending("B", "tok") is None  # outra sessão não consegue pegar
    assert db.take_pending("A", "tok") is not None
    assert db.take_pending("A", "tok") is None  # uso único

from lily.planner import plan


def first(msg):
    p = plan(msg)
    return (p.calls[0]["name"], p.calls[0]["args"]) if p.kind == "tool" else (None, p.text)


def test_create_task_extracts_everything():
    name, args = first("Crie uma tarefa para enviar o relatório amanhã às 9h com prioridade alta")
    assert name == "create_task" and args["priority"] == "alta" and "relat" in args["title"].lower()
    assert args["due"] == "amanhã 9h"


def test_first_verb_wins():
    assert first("Crie uma tarefa para editar o documento")[0] == "create_task"
    assert first("Marque a tarefa enviar relatório como concluída")[0] == "complete_task"
    assert first("Mostre as tarefas concluídas")[1] == {"status": "concluida"}


def test_destructive_requests_never_become_bulk_actions():
    for msg in ("Apague todas as tarefas", "apague tudo", "exclua todos os lembretes"):
        assert first(msg)[0] is None
    assert first("Apague a tarefa 2") == ("delete_task", {"task": "2"})


def test_ambiguous_messages_ask_for_clarification():
    for msg in ("apague", "amanhã", "Me lembre amanhã", "escreva um email", "cancele a reunião de amanhã"):
        name, text = first(msg)
        assert name is None and text


def test_questions_fall_back_to_document_search():
    assert first("Quais os benefícios?")[0] == "search_documents"
    assert first("Qual o preço do bitcoin?")[0] == "search_documents"

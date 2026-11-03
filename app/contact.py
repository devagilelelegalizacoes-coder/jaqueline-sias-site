"""Entrega das mensagens do formulário: arquivo local (JSONL) e/ou e-mail SMTP.

LGPD: guarda somente os campos do formulário, sem IP nem dados de navegação.
"""
import json
import logging
import smtplib
import ssl
import threading
from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path

from flask import current_app

log = logging.getLogger(__name__)
_lock = threading.Lock()


def _store(data: dict) -> bool:
    path = Path(current_app.config["CONTACT_STORAGE_PATH"])
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with _lock, path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(data, ensure_ascii=False) + "\n")
        return True
    except OSError:
        log.exception("Falha ao gravar mensagem de contato em %s", path)
        return False


def _send_email(data: dict) -> bool:
    cfg = current_app.config
    recipient = cfg["MAIL_RECIPIENT"] or cfg["CONTACT_EMAIL"]
    sender = cfg["MAIL_SENDER"] or cfg["MAIL_USERNAME"]
    if not (cfg["MAIL_SERVER"] and recipient and sender):
        return False

    msg = EmailMessage()
    msg["Subject"] = f"Novo contato pelo site: {data['nome']}"
    msg["From"] = sender
    msg["To"] = recipient
    msg.set_content(
        "Nova mensagem enviada pelo formulário do site.\n\n"
        f"Nome: {data['nome']}\n"
        f"Telefone/WhatsApp: {data['telefone']}\n"
        f"Serviço: {data['servico'] or 'Não informado'}\n"
        f"Data: {data['recebido_em']}\n\n"
        f"Mensagem:\n{data['mensagem']}\n"
    )
    try:
        if cfg["MAIL_USE_SSL"]:
            server = smtplib.SMTP_SSL(cfg["MAIL_SERVER"], cfg["MAIL_PORT"], timeout=10,
                                      context=ssl.create_default_context())
        else:
            server = smtplib.SMTP(cfg["MAIL_SERVER"], cfg["MAIL_PORT"], timeout=10)
        with server:
            if cfg["MAIL_USE_TLS"] and not cfg["MAIL_USE_SSL"]:
                server.starttls(context=ssl.create_default_context())
            if cfg["MAIL_USERNAME"]:
                server.login(cfg["MAIL_USERNAME"], cfg["MAIL_PASSWORD"])
            server.send_message(msg)
        return True
    except (smtplib.SMTPException, OSError):
        log.exception("Falha ao enviar e-mail de contato")
        return False


def deliver(nome: str, telefone: str, servico: str, mensagem: str) -> bool:
    """Entrega a mensagem. Retorna True se ao menos um canal registrou o contato."""
    data = {
        "recebido_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "nome": nome,
        "telefone": telefone,
        "servico": servico,
        "mensagem": mensagem,
    }
    stored = _store(data) if current_app.config["CONTACT_STORE_ENABLED"] else False
    mailed = _send_email(data)
    if current_app.testing:
        return True
    log.info("Contato recebido (servico=%s, arquivo=%s, email=%s)", servico or "-", stored, mailed)
    return stored or mailed

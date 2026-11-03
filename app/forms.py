"""Formulários com validação no backend (Flask-WTF + proteção CSRF)."""
import re

from flask_wtf import FlaskForm
from wtforms import BooleanField, SelectField, StringField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional, ValidationError

from .content import SERVICE_NAMES

OTHER_SERVICE = "Outro assunto"


def _strip(value):
    return value.strip() if isinstance(value, str) else value


def _collapse(value):
    return re.sub(r"\s+", " ", value).strip() if isinstance(value, str) else value


class ContactForm(FlaskForm):
    nome = StringField(
        "Nome",
        filters=[_collapse],
        validators=[
            DataRequired("Informe seu nome."),
            Length(min=3, max=80, message="Informe seu nome (3 a 80 caracteres)."),
        ],
    )
    telefone = StringField(
        "Telefone / WhatsApp",
        filters=[_strip],
        validators=[DataRequired("Informe um telefone com DDD.")],
    )
    servico = SelectField(
        "Serviço de interesse",
        choices=[("", "Selecione (opcional)")]
        + [(n, n) for n in SERVICE_NAMES]
        + [(OTHER_SERVICE, OTHER_SERVICE)],
        validators=[Optional()],
        validate_choice=True,
    )
    mensagem = TextAreaField(
        "Mensagem",
        filters=[_strip],
        validators=[
            DataRequired("Escreva sua mensagem."),
            Length(min=10, max=1500, message="Escreva uma mensagem entre 10 e 1500 caracteres."),
        ],
    )
    consent = BooleanField(
        "Consentimento",
        validators=[DataRequired("É necessário concordar para enviarmos o retorno.")],
    )
    # Honeypot anti-spam: campo invisível que pessoas não preenchem.
    website = StringField("Site", filters=[_strip])

    def validate_nome(self, field):
        if not re.fullmatch(r"[A-Za-zÀ-ÖØ-öø-ÿ' .-]+", field.data or ""):
            raise ValidationError("Use apenas letras no nome.")

    def validate_telefone(self, field):
        digits = re.sub(r"\D", "", field.data or "")
        if digits.startswith("55") and len(digits) in (12, 13):
            digits = digits[2:]
        if len(digits) not in (10, 11) or digits[:2] in {"00", "01"}:
            raise ValidationError("Informe um telefone com DDD.")
        field.normalized = digits

    @property
    def is_spam(self) -> bool:
        return bool(self.website.data)

    def formatted_phone(self) -> str:
        d = getattr(self.telefone, "normalized", re.sub(r"\D", "", self.telefone.data or ""))
        if len(d) == 11:
            return f"({d[:2]}) {d[2:7]}-{d[7:]}"
        if len(d) == 10:
            return f"({d[:2]}) {d[2:6]}-{d[6:]}"
        return d

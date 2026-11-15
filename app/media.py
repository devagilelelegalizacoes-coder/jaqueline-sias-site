"""Upload de fotos pelo painel: valida, corrige rotação, recorta e converte para WebP/JPEG.

As imagens ficam em instance/uploads (volume persistente) e são servidas em /uploads/.
Nomes aleatórios permitem cache longo no navegador.
"""
import secrets
from io import BytesIO
from pathlib import Path

from flask import current_app
from PIL import Image, ImageOps, UnidentifiedImageError

Image.MAX_IMAGE_PIXELS = 40_000_000  # bloqueia "bombas" de descompressão
ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP", "GIF", "MPO"}
MAX_FILE_BYTES = 10 * 1024 * 1024

# slot -> (tamanho final, tamanho reduzido ou None). Recorte central preservando o topo.
CROPS = {
    "hero": ((700, 840), (480, 576)),
    "sobre": ((900, 1050), (540, 630)),
    "og": ((1200, 630), None),
}


class ImageError(ValueError):
    pass


def upload_dir() -> Path:
    path = Path(current_app.config["UPLOAD_FOLDER"])
    path.mkdir(parents=True, exist_ok=True)
    return path


def _open(file_storage) -> Image.Image:
    data = file_storage.stream.read(MAX_FILE_BYTES + 1)
    if not data:
        raise ImageError("Arquivo vazio.")
    if len(data) > MAX_FILE_BYTES:
        raise ImageError("Foto maior que 10 MB. Reduza o tamanho e tente de novo.")
    try:
        img = Image.open(BytesIO(data))
        if img.format not in ALLOWED_FORMATS:
            raise ImageError("Formato não aceito. Envie JPG, PNG ou WebP.")
        img.load()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise ImageError("O arquivo enviado não é uma imagem válida.") from exc
    img = ImageOps.exif_transpose(img)
    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGBA" if "A" in img.getbands() or img.mode == "P" else "RGB")
    return img


def _name(slot: str, ext: str) -> str:
    return f"{slot}-{secrets.token_hex(6)}.{ext}"


def _save_webp(img: Image.Image, slot: str) -> str:
    name = _name(slot, "webp")
    img.save(upload_dir() / name, "WEBP", quality=82, method=6)
    return f"uploads/{name}"


def _rgb(img: Image.Image) -> Image.Image:
    if img.mode == "RGBA":
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[3])
        return bg
    return img


def save_cropped(file_storage, slot: str) -> dict:
    """Foto de tamanho fixo (hero, sobre, imagem de compartilhamento)."""
    size, small = CROPS[slot]
    img = _open(file_storage)
    fitted = ImageOps.fit(img, size, Image.LANCZOS, centering=(0.5, 0.3))
    if slot == "og":
        name = _name(slot, "jpg")
        _rgb(fitted).save(upload_dir() / name, "JPEG", quality=85, optimize=True, progressive=True)
        return {"src": f"uploads/{name}"}
    out = {"src": _save_webp(fitted, slot)}
    if small:
        out["small"] = _save_webp(fitted.resize(small, Image.LANCZOS), f"{slot}-p")
    return out


def save_logo(file_storage) -> dict:
    img = _open(file_storage).convert("RGBA")
    img.thumbnail((600, 200), Image.LANCZOS)
    png = _name("logo", "png")
    img.save(upload_dir() / png, "PNG", optimize=True)
    w, h = img.size
    # o cabeçalho exibe o logo com 44 px de altura
    disp_h = 44
    disp_w = max(1, round(w * disp_h / h))
    return {"src": _save_webp(img, "logo"), "png": f"uploads/{png}", "w": disp_w, "h": disp_h}


def save_gallery(file_storage) -> dict:
    img = _open(file_storage)
    img.thumbnail((900, 1200), Image.LANCZOS)
    w, h = img.size
    return {"src": _save_webp(img, "galeria"), "w": w, "h": h}

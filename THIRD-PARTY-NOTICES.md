# Avisos de terceros (Third-Party Notices)

BalanceLocal empaqueta y/o utiliza los siguientes componentes de terceros:

## PyMuPDF (fitz) — GNU AGPL v3
BalanceLocal incluye **PyMuPDF** (https://pymupdf.io) para generar el informe
PDF. PyMuPDF se distribuye bajo la **GNU Affero General Public License v3
(AGPL-3.0)**, con opción de licencia comercial de Artifex Software.

- Proyecto: https://github.com/pymupdf/PyMuPDF
- Licencia comercial (Artifex): https://artifex.com/licensing
- Texto de la licencia AGPL: https://www.gnu.org/licenses/agpl-3.0.html

**Nota sobre la AGPL:** dado que BalanceLocal empaqueta PyMuPDF (AGPL-3.0), el
código fuente completo está disponible en este repositorio, lo que satisface los
requisitos de la AGPL para esta distribución.

## Otras dependencias
- **Pillow** (PIL) — licencia HPND/MIT-CMU — https://python-pillow.org (tarjetas Wrapped e icono)

## FFmpeg (no empaquetado)
El mini-vídeo opcional usa **FFmpeg** si ya está instalado en el sistema. FFmpeg
se distribuye bajo LGPL/GPL según la build — https://ffmpeg.org/legal.html

El resto del código de BalanceLocal se distribuye bajo licencia MIT (ver `LICENSE`).

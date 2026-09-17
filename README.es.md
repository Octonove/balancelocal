# BalanceLocal

**Tu "Wrapped" laboral, 100% en tu PC.** Como Spotify Wrapped o Strava, pero de tu trabajo de oficina: BalanceLocal observa en qué programas pasas el tiempo (solo en tu máquina) y cada semana genera **tarjetas visuales** y un **mini-vídeo** con tus estadísticas de foco. El único dueño del dato eres tú.

<!-- invokard-coffee -->
**&#9749; Si esto te ahorra tiempo, inv&iacute;tame a un caf&eacute;.** [![Inv&iacute;tame a un caf&eacute; con PayPal](https://img.shields.io/badge/PayPal-Inv%C3%ADtame%20a%20un%20caf%C3%A9-00457C?logo=paypal&logoColor=white)](https://www.paypal.com/donate/?business=stradoxx%40gmail.com&no_recurring=0&currency_code=EUR&item_name=Support%20balancelocal)

**USDC** &middot; Solana `5n6Gfosk7SdwbvdtE9xiLWpcGPBBBGDZYRfAkWyCk86g` &middot; Ethereum (ERC-20) `0xe176866f9d7fdb498e0d4a983d3e34d84dcd6bfc`

## ⬇️ Descargar (Windows 10/11)

### ➡️ [**Descargar BalanceLocal (instalador .exe)**](https://github.com/Octonove/balancelocal/releases/latest/download/BalanceLocal-Setup.exe)

Descarga **directa** del instalador, sin registro. También puedes ver la [última versión y notas](https://github.com/Octonove/balancelocal/releases/latest).

> Si Windows muestra *"Windows protegió tu PC"*: pulsa **Más información → Ejecutar de todas formas**. Se instala sin permisos de administrador.

## Qué hace

- **Mide tu foco sin vigilarte**: apunta qué programa tienes delante (nombre y título de ventana) y si hay teclado/ratón. **No registra lo que tecleas ni hace capturas de pantalla.**
- **Categoriza tu tiempo** con heurísticas locales: Navegador, Documentos, Reuniones, Correo, Desarrollo, Diseño, Mensajería… (una reunión abierta en el navegador se cuenta como reunión).
- **Tu Wrapped semanal**: 4 tarjetas PNG verticales listas para compartir (portada con tus horas de foco, tus 5 apps top, en qué se fue el tiempo, y tus récords: hora de oro y racha). Con FFmpeg instalado, además un **mini-vídeo** vertical.
- **Informe PDF de la semana** con horas por categoría y por día — perfecto para el freelance que **factura por horas o proyecto**.
- **IA opcional** (Ollama o una API con tu clave): reescribe tus titulares con más gracia. Sin IA es 100% funcional.
- **Control total**: pausa cuando quieras, elige si guardar los títulos de ventana, y **borra todos tus datos** con un botón.

> **Privacidad**: la actividad se guarda **solo en tu equipo** (`%APPDATA%\BalanceLocal`), nunca sale de tu PC, y el único que la ve eres tú. No es una herramienta de vigilancia del jefe: es tu espejo.

## Stack

Python 3 + Tkinter (ttk) · SQLite · ctypes/Win32 (ventana activa + inactividad) · Pillow (tarjetas) · PyMuPDF (informe) · FFmpeg opcional (vídeo) · Ollama/API opcional.

Depende del paquete compartido [`octonove-core`](https://github.com/Octonove/octonove-core) (tema, config, IA, FFmpeg).

## Compilar

```powershell
.\build\build.ps1              # ejecutable (PyInstaller onedir)
.\build\build-installer.ps1    # instalador (Inno Setup)
```

## Tests

```powershell
python -m pytest tests/ -q
```

## Licencia

[MIT](LICENSE) — © 2026 Octonove.

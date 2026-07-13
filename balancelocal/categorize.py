"""Clasificacion de la actividad por CATEGORIA a partir del ejecutable y el
titulo de ventana. Logica 100% pura y testeable (heuristicas, sin IA)."""

from __future__ import annotations

# categoria -> subcadenas del nombre del ejecutable (sin .exe, en minusculas)
_APPS = {
    "Reuniones": ("teams", "zoom", "webex", "skype", "gotomeeting", "meet"),
    "Correo": ("outlook", "thunderbird", "hxmail", "mailbird", "em client", "emclient"),
    "Navegador": ("chrome", "firefox", "msedge", "edge", "brave", "opera", "vivaldi",
                  "iexplore", "safari"),
    "Documentos": ("winword", "excel", "powerpnt", "onenote", "wordpad", "acrord32",
                   "acrobat", "soffice", "libreoffice", "wps", "pdf"),
    "Desarrollo": ("code", "devenv", "pycharm", "idea", "webstorm", "sublime_text",
                   "notepad++", "windowsterminal", "cmd", "powershell", "pwsh",
                   "conemu", "git", "docker", "python", "node"),
    "Diseno": ("photoshop", "illustrator", "figma", "gimp", "inkscape", "canva",
               "blender", "afdesign", "afphoto", "coreldrw"),
    "Mensajeria": ("whatsapp", "telegram", "slack", "discord", "signal"),
    "Multimedia": ("vlc", "spotify", "wmplayer", "mpc-hc", "musicbee", "foobar",
                   "netflix", "youtube"),
}
# palabras del TITULO que ganan a la app (p.ej. una reunion abierta en el navegador)
_TITULO = {
    "Reuniones": ("reunión", "reunion", "meeting", "zoom", "google meet", "microsoft teams"),
    "Correo": ("bandeja de entrada", "inbox", "gmail", "correo", "- outlook"),
}

CATEGORIAS = ("Reuniones", "Correo", "Navegador", "Documentos", "Desarrollo",
              "Diseno", "Mensajeria", "Multimedia", "Otros")


def _tokens(texto: str) -> set[str]:
    """Palabras del texto (separadas por lo no alfanumerico), en minusculas."""
    return {p for p in "".join(c if c.isalnum() else " " for c in texto.lower()).split() if p}


def categoria(app: str, titulo: str = "") -> str:
    a = (app or "").lower().removesuffix(".exe")
    # las claves de app se comparan por el nombre base o por sus tokens (no por
    # subcadena): asi 'logitech' no cae en 'git', ni 'Correos' en 'correo'.
    a_tokens = _tokens(a)
    t = (titulo or "").lower()
    t_tokens = _tokens(titulo)
    # 1) el titulo puede reasignar (reunion/correo dentro del navegador). Las
    #    claves multipalabra se buscan como subcadena; las simples, por token.
    for cat, claves in _TITULO.items():
        for k in claves:
            if (" " in k and k in t) or (" " not in k and k in t_tokens):
                return cat
    # 2) por ejecutable: token exacto (o el propio basename empieza por la clave
    #    para variantes tipo 'pycharm64', 'sublime_text')
    for cat, claves in _APPS.items():
        for k in claves:
            if k in a_tokens or a == k or a.startswith(k):
                return cat
    return "Otros"


def nombre_amigable(app: str) -> str:
    """Nombre presentable de una app ('chrome.exe' -> 'Chrome')."""
    base = (app or "").lower().removesuffix(".exe")
    bonitos = {
        "msedge": "Edge", "chrome": "Chrome", "firefox": "Firefox", "brave": "Brave",
        "winword": "Word", "excel": "Excel", "powerpnt": "PowerPoint",
        "code": "VS Code", "devenv": "Visual Studio", "outlook": "Outlook",
        "teams": "Teams", "ms-teams": "Teams", "zoom": "Zoom", "slack": "Slack",
        "whatsapp": "WhatsApp", "telegram": "Telegram", "discord": "Discord",
        "acrord32": "Acrobat Reader", "photoshop": "Photoshop", "spotify": "Spotify",
        "explorer": "Explorador", "notepad": "Bloc de notas", "notepad++": "Notepad++",
        "vlc": "VLC", "pycharm64": "PyCharm", "windowsterminal": "Terminal",
    }
    if base in bonitos:
        return bonitos[base]
    return base[:1].upper() + base[1:] if base else "?"

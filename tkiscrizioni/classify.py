"""Dalle intestazioni di un'email (mittente, oggetto, List-Unsubscribe) ai segnali sul servizio che l'ha mandata."""
import email.header
import email.utils
import re
import unicodedata

F_ACCOUNT = 1      # benvenuto, conferma iscrizione, verifica indirizzo
F_SECURITY = 2     # password, codici, nuovi accessi: c'è un account
F_PURCHASE = 4     # ordini, ricevute, fatture, spedizioni
F_LIST = 8         # newsletter (List-Unsubscribe / List-Id)

# suffissi a due livelli più comuni: il dominio «registrato» è il terzo livello
_SUFFIX2 = {
    "co.uk", "org.uk", "ac.uk", "gov.uk", "me.uk", "com.au", "net.au", "org.au", "co.nz", "co.za", "co.jp", "ne.jp",
    "co.kr", "com.br", "com.mx", "com.ar", "com.tr", "co.in", "com.cn", "com.hk", "com.sg", "com.tw", "co.il",
    "com.co", "com.pe", "com.pl", "com.ua", "co.id", "com.my", "com.ph", "com.vn", "co.th",
}

# domini di invio che appartengono a un servizio con un altro dominio
_ALIAS = {
    "facebookmail.com": "facebook.com",
    "linkedin.com": "linkedin.com",
    "twitter.com": "x.com",
    "amazonses.com": "",
    "accountprotection.microsoft.com": "microsoft.com",
}

# caselle di persone (mittenti privati, non servizi)
FREEMAIL = {
    "gmail.com", "googlemail.com", "libero.it", "inwind.it", "iol.it", "blu.it", "virgilio.it", "alice.it", "tin.it",
    "tim.it", "tiscali.it", "fastwebnet.it", "hotmail.com", "hotmail.it", "outlook.com", "outlook.it", "live.com",
    "live.it", "msn.com", "yahoo.com", "yahoo.it", "ymail.com", "icloud.com", "me.com", "mac.com", "gmx.com",
    "gmx.it", "gmx.net", "gmx.de", "pec.it", "legalmail.it", "aruba.it", "email.it", "proton.me", "protonmail.com",
    "web.de", "aol.com", "mail.com", "zoho.com", "yandex.com", "yandex.ru", "mail.ru",
}

SOCIAL = {
    "facebook.com", "instagram.com", "x.com", "tiktok.com", "linkedin.com", "pinterest.com", "reddit.com",
    "snapchat.com", "threads.net", "tumblr.com", "youtube.com", "twitch.tv", "discord.com", "telegram.org",
    "whatsapp.com", "quora.com", "medium.com", "vk.com", "badoo.com", "tinder.com", "meetup.com",
}


def _norm(s):
    s = unicodedata.normalize("NFKD", s.lower())
    return "".join(c for c in s if not unicodedata.combining(c))


_RX_ACCOUNT = re.compile(
    r"benvenut|welcome|bienvenu|bienvenid|willkommen"
    r"|conferm\w*\s+(?:la\s+tua\s+|il\s+tuo\s+|l.)?(?:e-?mail|indirizzo|account|iscrizione|registrazione)"
    r"|verific\w*\s+(?:la\s+tua\s+|il\s+tuo\s+|l.)?(?:e-?mail|indirizzo|account)"
    r"|verify\s+(?:your\s+)?(?:e-?mail|address|account)"
    r"|confirm\s+(?:your\s+)?(?:e-?mail|address|account|registration|sign.?up)"
    r"|attiva\s+(?:il\s+tuo\s+|l.)?account|activate\s+(?:your\s+)?account"
    r"|registrazione\s+(?:completata|confermata|avvenuta|riuscita)|iscrizione\s+(?:completata|confermata|avvenuta)"
    r"|account\s+(?:creato|attivato|created|activated|is\s+ready|e\s+pronto)"
    r"|thanks?\s+(?:you\s+)?for\s+(?:signing\s+up|registering|joining|creating)"
    r"|grazie\s+per\s+(?:esserti|la\s+tua|averci)\s+\w*\s*(?:iscritt|registra)"
    r"|grazie\s+per\s+(?:l.)?iscrizione|sei\s+iscritt|ti\s+sei\s+iscritt|ti\s+sei\s+registrat"
    r"|you.?re\s+(?:now\s+)?(?:registered|signed\s+up|in\b)|complete\s+your\s+(?:registration|sign.?up|profile)"
    r"|completa\s+(?:la\s+tua\s+)?(?:registrazione|iscrizione)|crea(?:zione)?\s+(?:del\s+)?(?:tuo\s+)?account")
_RX_SECURITY = re.compile(
    r"password|passcode|codice\s+(?:di\s+)?(?:verifica|sicurezza|accesso|conferma|login)|verification\s+code"
    r"|security\s+code|one.?time|\botp\b|nuovo\s+accesso|new\s+(?:sign.?in|login|device)|nuovo\s+dispositivo"
    r"|accesso\s+(?:al\s+tuo\s+account|da\s+un\s+nuovo|effettuato)|sign.?in\s+(?:attempt|alert|code)"
    r"|security\s+alert|avviso\s+di\s+sicurezza|avviso\s+sicurezza|autenticazione\s+a\s+due|two.?factor|\b2fa\b"
    r"|login\s+code|reimposta|reset\s+your|recupero\s+(?:account|password)|codice\s+\d{4,}|\b\d{6}\b.*codice"
    r"|is\s+your\s+\w+\s+code|e\s+il\s+tuo\s+codice")
_RX_PURCHASE = re.compile(
    r"\bordine\b|\border\b|ricevuta|receipt|fattura|invoice|spedit|spedizione|shipped|shipping|consegn|deliver"
    r"|pagamento|payment|abbonament|subscription|rinnov|renewal|acquisto|purchase|prenotazione|booking"
    r"|biglietto|\bticket|reso\b|rimborso|refund|transazione|transaction|addebito")


def decode(value):
    if not value:
        return ""
    try:
        return str(email.header.make_header(email.header.decode_header(value)))
    except Exception:
        return value if isinstance(value, str) else value.decode("utf-8", "replace")


def organizzativo(host):
    """Dominio «registrato» (news.mail.amazon.co.uk → amazon.co.uk), senza gli alias dei servizi."""
    host = (host or "").strip().lower().strip(".")
    parts = host.split(".")
    if len(parts) <= 2:
        return host
    n = 3 if ".".join(parts[-2:]) in _SUFFIX2 else 2
    return ".".join(parts[-n:])


def registrable(host):
    host = host.strip().lower().strip(".")
    if host in _ALIAS:
        return _ALIAS[host]
    reg = organizzativo(host)
    return _ALIAS.get(reg, reg)


# ---- Authentication-Results (RFC 8601): l'intestazione che il server di posta aggiunge dopo aver
# verificato la firma DKIM del mittente. Vale solo la PRIMA (la più in alto): l'ha scritta il tuo
# fornitore; quelle più in basso possono arrivare già scritte da chi ha spedito l'email.
_RX_DKIM_PASS = re.compile(r"^\s*dkim\s*=\s*pass\b", re.I)
_RX_HEADER_D = re.compile(r"\bheader\.d\s*=\s*\"?([a-z0-9.-]+)", re.I)
_RX_HEADER_I = re.compile(r"\bheader\.i\s*=\s*\"?[^@\s;\"]*@([a-z0-9.-]+)", re.I)


def _senza_commenti(text):
    prima = None
    while prima != text:
        prima = text
        text = re.sub(r"\([^()]*\)", " ", text)
    return text


def dkim_domini(auth_results):
    """Authentication-Results → domini delle firme DKIM verificate (dkim=pass)."""
    out = []
    for seg in _senza_commenti(auth_results or "").split(";"):
        if not _RX_DKIM_PASS.search(seg):
            continue
        m = _RX_HEADER_D.search(seg) or _RX_HEADER_I.search(seg)
        if m:
            out.append(m.group(1).lower().strip("."))
    return out


def dkim_allineato(auth_results, from_addr):
    """Vero se il server di posta ha verificato una firma DKIM dello stesso dominio del mittente
    (allineamento «relaxed» come in DMARC: news.zalando.it e zalando.it vanno bene insieme)."""
    org = organizzativo((from_addr or "").rpartition("@")[2])
    return bool(org) and "." in org and any(organizzativo(d) == org for d in dkim_domini(auth_results))


FUTURO_TOLLERATO = 86400   # date più avanti di un giorno (fusi orari a parte) sono false: si ignorano


def flags_for(subject, list_unsub, list_id):
    s = _norm(subject or "")
    f = 0
    if _RX_ACCOUNT.search(s):
        f |= F_ACCOUNT
    if _RX_SECURITY.search(s):
        f |= F_SECURITY
    if _RX_PURCHASE.search(s):
        f |= F_PURCHASE
    if list_unsub or list_id:
        f |= F_LIST
    return f


def parse_headers(raw, now=None):
    """bytes delle intestazioni → dict pronto per l'archivio (o None se manca il mittente).
    Il link di disiscrizione si tiene solo se l'email è firmata (DKIM verificato dal server di posta)
    dallo stesso dominio del mittente: altrimenti chiunque potrebbe spedire un'email «da Zalando» con un
    link suo. Le date nel futuro diventano 0 (sconosciuta)."""
    import email.parser
    import email.policy
    import time
    # intestazioni scritte in UTF-8 senza codifica (RFC 6532): vanno lette come testo, non come ASCII
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("latin-1")
    msg = email.parser.HeaderParser(policy=email.policy.compat32).parsestr(text)
    name, addr = email.utils.parseaddr(decode(msg.get("From", "")))
    addr = addr.strip().lower()
    if "@" not in addr:
        return None
    subject = decode(msg.get("Subject", "")).replace("\r", " ").replace("\n", " ").strip()
    unsub = " ".join(decode(msg.get("List-Unsubscribe", "")).split())
    unsub_post = "one-click" in (msg.get("List-Unsubscribe-Post", "") or "").lower()
    list_id = msg.get("List-Id", "") or ""
    ts = 0.0
    try:
        ts = email.utils.parsedate_to_datetime(msg.get("Date", "")).timestamp()
    except Exception:
        pass
    if ts > (time.time() if now is None else now) + FUTURO_TOLLERATO:
        ts = 0.0
    domain = registrable(addr.rpartition("@")[2])
    flags = flags_for(subject, unsub, list_id)
    if unsub and not dkim_allineato(msg.get("Authentication-Results", "") or "", addr):
        unsub, unsub_post = "", False
    return {
        "ts": ts, "from_addr": addr, "from_name": name.strip().strip('"')[:120], "domain": domain,
        "subject": subject[:300], "unsub": unsub[:1000], "unsub_post": 1 if unsub_post else 0,
        "flags": flags,
    }


def category(domain, acc, sec, pur, lst, own_domains=()):
    """Categoria del servizio dai conteggi dei segnali."""
    if domain in FREEMAIL or domain in own_domains:
        return "persona"
    if domain in SOCIAL:
        return "social"
    if acc or sec:
        return "account"
    if pur:
        return "acquisti"
    if lst:
        return "newsletter"
    return "altro"


CATEGORIES = {
    "account": ("Account", "Ti sei registrato: c'è un account con la tua email"),
    "social": ("Social", "Social network e community"),
    "acquisti": ("Acquisti", "Ordini, ricevute, abbonamenti"),
    "newsletter": ("Newsletter", "Ti mandano comunicazioni o pubblicità"),
    "altro": ("Altro", "Ti hanno scritto, senza segni chiari di iscrizione"),
    "persona": ("Persone", "Caselle email di persone e del tuo dominio"),
}


def nice_name(names, domain):
    """Nome leggibile: il nome mittente più usato, ripulito; altrimenti il dominio con la maiuscola."""
    bad = re.compile(r"no.?reply|do.?not.?reply|notifications?|notifiche|newsletter|info|support|team|mailer",
                     re.I)
    for n, _c in names:
        n = n.strip()
        if not n or "@" in n or len(n) > 40:
            continue
        clean = re.sub(r"\s*[|\-–·:]\s*(no.?reply|notifiche|notifications?|newsletter|team|support)\b.*$", "", n,
                       flags=re.I).strip()
        if clean and not bad.fullmatch(clean):
            return clean
    base = domain.split(".")[0] if domain else "?"
    return base[:1].upper() + base[1:]


def unsub_links(header):
    """List-Unsubscribe → (https, mailto)."""
    https = mailto = ""
    for part in re.findall(r"<([^>]+)>", header or ""):
        p = part.strip()
        if p.lower().startswith("https://") and not https:
            https = p
        elif p.lower().startswith("mailto:") and not mailto:
            mailto = p
    return https, mailto


def stesso_servizio(host, domain):
    """Vero se l'host del link appartiene al dominio del servizio (anche tramite gli alias, es. facebookmail.com)."""
    host = (host or "").strip().lower().strip(".")
    return bool(host and domain) and (organizzativo(host) == organizzativo(domain) or registrable(host) == domain)

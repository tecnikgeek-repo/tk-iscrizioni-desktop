"""Fornitori di posta noti: server IMAP e cosa deve fare l'utente per entrare.
Nessuna ricerca su internet: se il dominio non è noto, l'utente sceglie il fornitore o scrive il server."""

PROVIDERS = {
    "gmail": {
        "label": "Gmail", "host": "imap.gmail.com", "port": 993, "auth": "password",
        "domains": ["gmail.com", "googlemail.com"],
        "hint": "Gmail non accetta la password normale: serve una «password per le app» (16 lettere). "
                "Si crea in un minuto dal tuo account Google; serve la verifica in due passaggi attiva.",
        "help_url": "https://myaccount.google.com/apppasswords",
        "help_label": "Crea la password per le app",
        "pw_label": "Password per le app (16 lettere)",
    },
    "outlook": {
        "label": "Outlook / Hotmail", "host": "outlook.office365.com", "port": 993, "auth": "oauth_ms",
        "domains": ["outlook.com", "outlook.it", "hotmail.com", "hotmail.it", "live.com", "live.it", "msn.com"],
        "hint": "Microsoft non accetta più la password nei programmi: si entra con il pulsante «Accedi con "
                "Microsoft», dalla pagina ufficiale di Microsoft. La password non passa da tk-iscrizioni.",
    },
    "aruba": {
        "label": "Aruba (dominio personale)", "host": "imaps.aruba.it", "port": 993, "auth": "password",
        "domains": ["aruba.it"],
        "hint": "Usa la password della casella, la stessa della webmail di Aruba.",
    },
    "arubapec": {
        "label": "Aruba PEC", "host": "imaps.pec.aruba.it", "port": 993, "auth": "password",
        "domains": ["pec.it"],
        "hint": "Usa la password della casella PEC.",
    },
    "libero": {
        "label": "Libero", "host": "imapmail.libero.it", "port": 993, "auth": "password",
        "domains": ["libero.it", "inwind.it", "iol.it", "blu.it", "giallo.it"],
        "hint": "Usa la password di Libero Mail.",
    },
    "virgilio": {
        "label": "Virgilio", "host": "in.virgilio.it", "port": 993, "auth": "password",
        "domains": ["virgilio.it"],
        "hint": "Usa la password di Virgilio Mail.",
    },
    "alice": {
        "label": "Alice / TIN", "host": "in.alice.it", "port": 993, "auth": "password",
        "domains": ["alice.it", "tin.it"],
        "hint": "Usa la password della casella.",
    },
    "tiscali": {
        "label": "Tiscali", "host": "imap.tiscali.it", "port": 993, "auth": "password",
        "domains": ["tiscali.it"],
        "hint": "Usa la password di Tiscali Mail.",
    },
    "yahoo": {
        "label": "Yahoo", "host": "imap.mail.yahoo.com", "port": 993, "auth": "password",
        "domains": ["yahoo.com", "yahoo.it", "ymail.com", "rocketmail.com"],
        "hint": "Yahoo vuole una «password per le app», da creare nelle impostazioni di sicurezza dell'account.",
        "help_url": "https://login.yahoo.com/account/security",
        "help_label": "Apri la sicurezza di Yahoo",
        "pw_label": "Password per le app",
    },
    "icloud": {
        "label": "iCloud", "host": "imap.mail.me.com", "port": 993, "auth": "password",
        "domains": ["icloud.com", "me.com", "mac.com"],
        "hint": "iCloud vuole una «password specifica per le app», da creare sul sito dell'ID Apple.",
        "help_url": "https://account.apple.com/account/manage",
        "help_label": "Apri l'account Apple",
        "pw_label": "Password specifica per le app",
    },
    "gmx": {
        "label": "GMX", "host": "imap.gmx.com", "port": 993, "auth": "password",
        "domains": ["gmx.com", "gmx.it"],
        "hint": "Nelle impostazioni di GMX va attivato l'accesso IMAP; poi usa la password della casella.",
    },
    "altro": {
        "label": "Altro (scrivo io il server)", "host": "", "port": 993, "auth": "password",
        "domains": [],
        "hint": "Se il dominio è su Aruba scegli «Aruba (dominio personale)» qui sopra. Altrimenti scrivi il "
                "server IMAP del tuo fornitore (di solito «imap.» o «mail.» seguito dal dominio) e la password "
                "della casella.",
    },
}

ORDER = ["gmail", "outlook", "aruba", "arubapec", "libero", "virgilio", "alice", "tiscali", "yahoo", "icloud",
         "gmx", "altro"]


def detect(email):
    """Chiave del fornitore dal dominio dell'indirizzo, oppure None se non è noto."""
    dom = email.strip().lower().rpartition("@")[2]
    for key in ORDER:
        if dom in PROVIDERS[key]["domains"]:
            return key
    return None


def guess_host(email):
    dom = email.strip().lower().rpartition("@")[2]
    return f"imap.{dom}" if dom else ""

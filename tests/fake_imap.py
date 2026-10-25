"""Finto server IMAP (solo i comandi usati da tk-iscrizioni) con email di esempio, per i test automatici."""
import re
import socketserver
import threading

DEMO = [
    # (mittente, oggetto, data, extra intestazioni)
    ('"Netflix" <info@mailer.netflix.com>', "Benvenuto su Netflix!", "Mon, 03 Feb 2020 10:00:00 +0100", ""),
    ('"Netflix" <info@mailer.netflix.com>', "Nuovo accesso al tuo account", "Tue, 05 Mar 2024 10:00:00 +0100", ""),
    ('Amazon.it <conferma-ordine@amazon.it>', "Il tuo ordine Amazon.it #402-1234", "Wed, 10 Jun 2021 09:00:00 +0200", ""),
    ('Amazon.it <spedizione@amazon.it>', "Il tuo pacco è stato spedito", "Thu, 11 Jun 2021 09:00:00 +0200", ""),
    # Authentication-Results come lo scrive Outlook (senza authserv-id, commenti tra parentesi)
    ('"Zalando" <news@mail.zalando.it>', "=?utf-8?q?Saldi_fino_al_70=25_=F0=9F=94=A5?=", "Fri, 01 Jul 2022 08:00:00 +0200",
     "Authentication-Results: spf=pass (sender IP is 192.0.2.1) smtp.mailfrom=zalando.it; dkim=pass (signature was\r\n"
     " verified) header.d=zalando.it;dmarc=pass action=none header.from=mail.zalando.it;compauth=pass reason=100\r\n"
     "List-Unsubscribe: <https://zalando.example/unsub?u=1>, <mailto:unsub@zalando.example>\r\n"
     "List-Unsubscribe-Post: List-Unsubscribe=One-Click\r\n"),
    # come lo scrive Gmail (con authserv-id), firma del sottodominio
    ('"Zalando" <news@mail.zalando.it>', "Novità della settimana", "Fri, 08 Jul 2022 08:00:00 +0200",
     "Authentication-Results: mx.google.com;\r\n       dkim=pass header.i=@mail.zalando.it header.s=s1 header.b=abc;\r\n"
     "       spf=pass smtp.mailfrom=bounce@mail.zalando.it\r\n"
     "List-Unsubscribe: <https://zalando.example/unsub?u=1>\r\nList-Unsubscribe-Post: List-Unsubscribe=One-Click\r\n"),
    ('Facebook <security@facebookmail.com>', "Il tuo codice di sicurezza è 123456", "Sat, 12 Aug 2023 12:00:00 +0200", ""),
    ('"Mario Rossi" <mario.rossi@gmail.com>', "Ci vediamo domani", "Sun, 13 Aug 2023 12:00:00 +0200", ""),
    ('Spotify <no-reply@spotify.com>', "Conferma il tuo indirizzo email", "Mon, 14 Jan 2019 12:00:00 +0100", ""),
    ('"Poste Italiane" <noreply@posteitaliane.it>', "Avviso di sicurezza", "Mon, 14 Jan 2019 12:00:00 +0100", ""),
    ('Ufficio <ufficio@esempio-ditta.it>', "Preventivo", "Tue, 15 Jan 2019 12:00:00 +0100", ""),
    ('Booking.com <noreply@booking.com>', "Prenotazione confermata a Roma", "Wed, 16 Jan 2019 12:00:00 +0100",
     "List-Id: <booking.list>\r\n"),
    # 13: email falsa «da Zalando»: il TUO server dice dkim=fail, sotto un Authentication-Results scritto da chi
    # l'ha spedita dice pass. Vale solo quello in alto: il link non va preso.
    ('"Zalando" <news@mail.zalando.it>', "Ultimo avviso: conferma i tuoi dati", "Fri, 15 Jul 2022 08:00:00 +0200",
     "Authentication-Results: mx.esempio-ditta.it; dkim=fail header.d=mail.zalando.it; spf=fail\r\n"
     "Authentication-Results: mx.esempio-ditta.it; dkim=pass header.d=zalando.it\r\n"
     "List-Unsubscribe: <https://truffa.example/x>\r\nList-Unsubscribe-Post: List-Unsubscribe=One-Click\r\n"),
    # 14: firma vera ma di un altro dominio (non allineata al mittente): il link non va preso
    ('"Zalando" <news@mail.zalando.it>', "Offerte per te", "Wed, 20 Jul 2022 08:00:00 +0200",
     "Authentication-Results: mx.esempio-ditta.it; dkim=pass header.d=spedizioni-qualsiasi.example\r\n"
     "List-Unsubscribe: <https://nonallineato.example/x>\r\nList-Unsubscribe-Post: List-Unsubscribe=One-Click\r\n"),
    # 15: data nel futuro: non deve diventare «ultima email» né scegliere il link
    ('"Zalando" <news@mail.zalando.it>', "Dal futuro", "Fri, 01 Jan 2099 08:00:00 +0100",
     "Authentication-Results: mx.esempio-ditta.it; dkim=pass header.d=zalando.it\r\n"
     "List-Unsubscribe: <https://futuro.example/x>\r\nList-Unsubscribe-Post: List-Unsubscribe=One-Click\r\n"),
]


def message_headers(i, fields=None):
    """Intestazioni dell'email i; con `fields` solo quelle chieste, come fa un server vero con HEADER.FIELDS."""
    frm, subj, date, extra = DEMO[i]
    text = f"From: {frm}\r\nSubject: {subj}\r\nDate: {date}\r\n{extra}"
    if fields is not None:
        keep, cur = [], False
        for line in text.split("\r\n"):
            if not line:
                continue
            if line[0] not in " \t":
                cur = line.split(":", 1)[0].upper() in fields
            if cur:
                keep.append(line)
        text = "\r\n".join(keep) + "\r\n"
    return (text + "\r\n").encode("utf-8")


class Handler(socketserver.StreamRequestHandler):
    def w(self, s):
        self.wfile.write(s if isinstance(s, bytes) else s.encode())

    def handle(self):
        self.w("* OK finto IMAP pronto\r\n")
        boxes = {"INBOX": list(range(1, 9)), "Lavoro &AOg- archivio": list(range(9, len(DEMO) + 1))}
        cur = None
        while True:
            line = self.rfile.readline()
            if not line:
                return
            parts = line.decode().rstrip("\r\n").split(" ", 2)
            tag, cmd = parts[0], parts[1].upper()
            arg = parts[2] if len(parts) > 2 else ""
            if cmd == "CAPABILITY":
                self.w("* CAPABILITY IMAP4rev1 AUTH=PLAIN\r\n" + f"{tag} OK fatto\r\n")
            elif cmd == "LOGIN":
                ok = arg.split()[1].strip('"') == "segreta"
                self.w(f"{tag} OK accesso fatto\r\n" if ok else f"{tag} NO [AUTHENTICATIONFAILED] Credenziali non valide\r\n")
            elif cmd == "LIST":
                self.w('* LIST (\\HasNoChildren) "/" "INBOX"\r\n'
                       '* LIST (\\HasNoChildren \\Sent) "/" "Posta inviata"\r\n'
                       '* LIST (\\HasNoChildren) "/" "Spam"\r\n'
                       '* LIST (\\HasNoChildren) "/" "Lavoro &AOg- archivio"\r\n' + f"{tag} OK fatto\r\n")
            elif cmd in ("EXAMINE", "SELECT"):
                cur = arg.strip('"')
                self.w(f"* {len(boxes.get(cur, []))} EXISTS\r\n* OK [UIDVALIDITY 7] uv\r\n{tag} OK [READ-ONLY] fatto\r\n")
            elif cmd == "UID" and arg.upper().startswith("SEARCH"):
                uids = boxes.get(cur, [])
                m = re.search(r"UID (\d+):\*", arg)
                if m:
                    low = int(m.group(1))
                    sel = [u for u in uids if u >= low] or uids[-1:]  # come i server veri: «*» dà sempre l'ultimo
                else:
                    sel = uids
                self.w("* SEARCH " + " ".join(map(str, sel)) + f"\r\n{tag} OK fatto\r\n")
            elif cmd == "UID" and arg.upper().startswith("FETCH"):
                spec = arg.split()[1]
                m = re.search(r"HEADER\.FIELDS \(([^)]*)\)", arg, re.I)
                fields = set(m.group(1).upper().split()) if m else None
                lista = []
                for x in spec.split(","):   # elenchi «1,2,3» e intervalli «1:8», come i server veri
                    a, _, b = x.partition(":")
                    lista += list(range(int(a), int(b) + 1)) if b else [int(a)]
                for n, u in enumerate(lista):
                    body = message_headers(u - 1, fields)
                    if u % 2:   # alterna l'UID prima e dopo il blocco, come fanno server diversi
                        self.w(f"* {n + 1} FETCH (UID {u} BODY[HEADER.FIELDS (FROM)] {{{len(body)}}}\r\n".encode() + body + b")\r\n")
                    else:
                        self.w(f"* {n + 1} FETCH (BODY[HEADER.FIELDS (FROM)] {{{len(body)}}}\r\n".encode() + body + f" UID {u})\r\n".encode())
                self.w(f"{tag} OK fatto\r\n")
            elif cmd == "LOGOUT":
                self.w(f"* BYE\r\n{tag} OK fatto\r\n")
                return
            else:
                self.w(f"{tag} OK fatto\r\n")


def start():
    srv = socketserver.ThreadingTCPServer(("127.0.0.1", 0), Handler)
    srv.daemon_threads = True
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, srv.server_address[1]

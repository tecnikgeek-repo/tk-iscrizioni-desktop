"""Dati di esempio per la prova automatica dell'interfaccia (--selftest): nessuna casella vera."""
import time

from tkiscrizioni import classify

_DEMO = [
    ("Netflix <info@mailer.netflix.com>", "Benvenuto su Netflix!", 2020, ""),
    ("Netflix <info@mailer.netflix.com>", "Nuovo accesso al tuo account", 2025, ""),
    ("Amazon.it <conferma-ordine@amazon.it>", "Il tuo ordine Amazon.it #402-1234", 2018, ""),
    ("Amazon.it <spedizione@amazon.it>", "Il tuo pacco è stato spedito", 2026, ""),
    ("Zalando <news@mail.zalando.it>", "Saldi fino al 70%", 2022,
     "List-Unsubscribe: <https://example.invalid/u>\r\nList-Unsubscribe-Post: List-Unsubscribe=One-Click\r\n"),
    ("Zalando <news@mail.zalando.it>", "Novità della settimana", 2026, "List-Unsubscribe: <https://example.invalid/u>\r\n"),
    ("Facebook <security@facebookmail.com>", "Il tuo codice di sicurezza", 2016, ""),
    ("Instagram <no-reply@mail.instagram.com>", "Conferma il tuo indirizzo email", 2017, ""),
    ("Spotify <no-reply@spotify.com>", "Conferma il tuo indirizzo email", 2019, ""),
    ("Poste Italiane <noreply@posteitaliane.it>", "Avviso di sicurezza", 2021, ""),
    ("Booking.com <noreply@booking.com>", "Prenotazione confermata a Roma", 2023, "List-Id: <b>\r\n"),
    ("Canva <start@engage.canva.com>", "Welcome to Canva", 2024, ""),
    ("IKEA Family <news@ikea.it>", "Le offerte del mese", 2025, "List-Unsubscribe: <mailto:u@example.invalid>\r\n"),
    ("Trenitalia <noreply@trenitalia.it>", "Biglietto acquistato: Napoli - Roma", 2024, ""),
    ("LinkedIn <messages-noreply@linkedin.com>", "Hai un nuovo invito", 2015, ""),
    ("Mario Rossi <mario.rossi@gmail.com>", "Ci vediamo domani", 2026, ""),
    ("Dropbox <no-reply@dropbox.com>", "Verifica il tuo indirizzo email", 2014, ""),
    ("Glovo <info@glovoapp.com>", "Il tuo ordine è in consegna", 2022, "List-Unsubscribe: <https://example.invalid/g>\r\n"),
]


def fill(store):
    aid = store.add_account("esempio@gmail.com", "gmail", "imap.gmail.com", 993, "password")
    rows = []
    for i, (frm, subj, year, extra) in enumerate(_DEMO):
        date = time.strftime("%a, %d %b %Y 10:00:00 +0100", time.gmtime(time.mktime((year, 1 + i % 12, 3, 10, 0, 0, 0, 0, 0))))
        raw = f"From: {frm}\r\nSubject: {subj}\r\nDate: {date}\r\n{extra}\r\n".encode("utf-8")
        rows.append((i + 1, classify.parse_headers(raw)))
    store.reset_folder(aid, "INBOX", 1)
    store.save_batch(aid, "INBOX", rows, len(rows))
    store.set_scan(aid, time.time())
    store.set_status("zalando.it", "cancellare")
    store.set_status("netflix.com", "tenere")
    return aid

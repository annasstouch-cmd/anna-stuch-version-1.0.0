from flask import Flask, jsonify, request
import os
import smtplib
from email.message import EmailMessage
from datetime import datetime, timedelta

# Vercel n'a pas besoin de template_folder
app = Flask(__name__)

# --- CONFIGURATION ---
EMAIL_ADDRESS = "annasstouch@gmail.com"
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD", "huby qptn wtat holi")
ADMIN_EMAIL = "lazaregnahouame@gmail.com"

# --- FONCTION DE CRÉATION DU CALENDRIER (.ics) ---
def create_ics_content(client_name, start_dt_str, client_email, service_name):
    # Conversion de la date (Format attendu: "2023-12-25T14:30")
    dt_start = datetime.strptime(start_dt_str, "%Y-%m-%dT%H:%M")
    dt_end = dt_start + timedelta(hours=1) # On compte 1h par défaut pour l'agenda

    # Formatage pour le calendrier (Format requis: YYYYMMDDTHHMMSS)
    fmt_start = dt_start.strftime("%Y%m%dT%H%M00")
    fmt_end = dt_end.strftime("%Y%m%dT%H%M00")
    now = datetime.now().strftime("%Y%m%dT%H%M00Z")

    # Contenu du fichier .ics avec les 2 RAPPELS (VALARM)
    ics_content = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Anna's Touch//Reservation//FR
CALSCALE:GREGORIAN
METHOD:REQUEST
BEGIN:VEVENT
UID:reservation-{now}-{client_email}
DTSTAMP:{now}
DTSTART:{fmt_start}
DTEND:{fmt_end}
SUMMARY:Anna's Touch - {service_name}
DESCRIPTION:Réservation confirmée pour {client_name}.
LOCATION:Salon Anna's Touch, 12 Avenue de la Mode, 75000 Paris
STATUS:CONFIRMED
ORGANIZER;CN=Anna's Touch:mailto:{EMAIL_ADDRESS}
ATTENDEE;RSVP=TRUE;CN={client_name}:mailto:{client_email}
BEGIN:VALARM
TRIGGER:-P1D
ACTION:DISPLAY
DESCRIPTION:Rappel: Rendez-vous Anna's Touch demain !
END:VALARM
BEGIN:VALARM
TRIGGER:-PT2H
ACTION:DISPLAY
DESCRIPTION:Rappel: Rendez-vous Anna's Touch dans 2h !
END:VALARM
END:VEVENT
END:VCALENDAR"""
    return ics_content

@app.route('/api/index', methods=['POST'])
def send_email():
    data = request.json
    
    email_type = data.get('type')
    client_name = data.get('name')
    client_email = data.get('email')

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)

            # --- FONCTION INTERNE POUR ENVOYER L'EMAIL ---
            def send_mail(to_email, subject, body_content, ics_data=None):
                msg = EmailMessage()
                msg['Subject'] = subject
                msg['From'] = EMAIL_ADDRESS
                msg['To'] = to_email
                msg.set_content(body_content)

                # Si on a des données de calendrier, on les attache !
                if ics_data:
                    msg.add_attachment(
                        ics_data.encode('utf-8'),
                        maintype='text',
                        subtype='calendar',
                        filename='invitation.ics'
                    )
                smtp.send_message(msg)

            # ==========================================
            # CAS 1 : NOUVELLE INSCRIPTION (SANS AGENDA)
            # ==========================================
            if email_type == 'signup':
                body_client = f"Bonjour {client_name},\n\nBienvenue chez Anna's Touch ! Votre compte a été créé avec succès. Vous avez reçu 50 points de fidélité en cadeau !\n\nÀ très vite."
                send_mail(client_email, "Bienvenue chez Anna's Touch !", body_client)
                
                body_admin = f"Nouvelle inscription sur le site !\n\nNom: {client_name}\nEmail: {client_email}"
                send_mail(ADMIN_EMAIL, f"👤 NOUVEAU CLIENT - {client_name}", body_admin)

            # ==========================================
            # CAS 2 : RÉSERVATION (AVEC AGENDA)
            # ==========================================
            elif email_type == 'booking':
                service_name = data.get('service')
                nice_date = data.get('nice_date') # Ex: "vendredi 20 février 2026 à 14:00"
                raw_date = data.get('raw_date')   # Ex: "2026-02-20T14:00" (Nécessaire pour le code ICS)
                
                # On fabrique la pièce jointe
                ics_data = create_ics_content(client_name, raw_date, client_email, service_name)

                body_client = f"Bonjour {client_name},\n\nVotre réservation chez Anna's Touch est confirmée !\n\n✂️ Prestation : {service_name}\n📅 Date : {nice_date}\n\nIMPORTANT : Cliquez sur la pièce jointe ou sur 'Ajouter à l'agenda' pour activer vos rappels automatiques (24h et 2h avant).\n\nMerci de votre confiance."
                send_mail(client_email, "Confirmation réservation ✅", body_client, ics_data)

                body_admin = f"Nouvelle réservation reçue !\n\nClient : {client_name}\nEmail : {client_email}\nPrestation : {service_name}\nDate : {nice_date}\n\nAjoutez la pièce jointe à votre agenda pour avoir le rappel."
                send_mail(ADMIN_EMAIL, f"🔴 NOUVELLE RÉSERVATION - {client_name}", body_admin, ics_data)
                 # ==========================================
                # CAS 3 : CONFIRMATION ADMIN
                # ==========================================
                elif email_type == 'admin_confirmation':
                    service_name = data.get('service')
                    nice_date = data.get('nice_date')
                    
                    body_client = f"Bonjour {client_name},\n\nBonne nouvelle ! Votre réservation pour {service_name} le {nice_date} a été confirmée par Anna's Touch.\n\nÀ très bientôt au salon !"
                    send_mail(client_email, "Votre rendez-vous est confirmé ! ✅", body_client)

        return jsonify({"status": "Emails envoyés avec succès !"}), 200

    except Exception as e:
        print(f"Erreur d'envoi: {e}")
        return jsonify({"error": str(e)}), 500

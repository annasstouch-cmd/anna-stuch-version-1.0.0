from flask import Flask, jsonify, request
import os
import smtplib
from email.message import EmailMessage
from datetime import datetime, timedelta

app = Flask(__name__)

# --- CONFIGURATION ---
EMAIL_ADDRESS = "annasstouch@gmail.com"
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD", "huby qptn wtat holi") # Assure-toi que c'est bien un "Mot de passe d'application" Google
ADMIN_EMAIL = "lazaregnahouame@gmail.com"
LOGO_URL = "https://loloooolazare.vercel.app/annas.png" # Ton logo en ligne

def create_ics_content(client_name, start_dt_str, client_email, service_name):
    dt_start = datetime.strptime(start_dt_str, "%Y-%m-%dT%H:%M")
    dt_end = dt_start + timedelta(hours=1)
    fmt_start = dt_start.strftime("%Y%m%dT%H%M00")
    fmt_end = dt_end.strftime("%Y%m%dT%H%M00")
    now = datetime.now().strftime("%Y%m%dT%H%M00Z")

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

# --- TEMPLATE HTML DE BASE ---
def get_html_template(title, content):
    return f"""
    <html>
        <body style="font-family: 'Montserrat', sans-serif; background-color: #fdfbf7; padding: 20px; color: #121212;">
            <div style="max-w-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.05); text-align: center;">
                <img src="{LOGO_URL}" alt="Anna's Touch Logo" style="width: 100px; height: 100px; border-radius: 50%; margin-bottom: 20px;">
                <h2 style="color: #d4af37; font-family: 'Playfair Display', serif; font-size: 24px;">{title}</h2>
                <div style="text-align: left; font-size: 16px; line-height: 1.6; color: #555;">
                    {content}
                </div>
                <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                <p style="font-size: 12px; color: #999;">
                    Anna's Touch - 12 Avenue de la Mode, 75000 Paris<br>
                    Révélez votre beauté royale.
                </p>
            </div>
        </body>
    </html>
    """

@app.route('/api/index', methods=['POST'])
def send_email():
    data = request.json
    email_type = data.get('type')
    client_name = data.get('name', 'Client')
    client_email = data.get('email')

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)

            def send_mail(to_email, subject, text_body, html_body, ics_data=None):
                msg = EmailMessage()
                msg['Subject'] = subject
                msg['From'] = f"Anna's Touch <{EMAIL_ADDRESS}>"
                msg['To'] = to_email
                msg.set_content(text_body)
                msg.add_alternative(html_body, subtype='html')

                if ics_data:
                    msg.add_attachment(ics_data.encode('utf-8'), maintype='text', subtype='calendar', filename='invitation.ics')
                smtp.send_message(msg)

            # 1. NOUVELLE INSCRIPTION
            if email_type == 'signup':
                text = f"Bonjour {client_name},\nBienvenue chez Anna's Touch ! Votre compte a été créé avec succès. Vous avez reçu 20 points de fidélité en cadeau !"
                html = get_html_template("Bienvenue chez Anna's Touch !", f"<p>Bonjour <strong>{client_name}</strong>,</p><p>Votre compte a été créé avec succès. Pour vous remercier de votre confiance, nous vous offrons <strong>20 points de fidélité</strong> en cadeau de bienvenue !</p><p>À très vite au salon.</p>")
                send_mail(client_email, "Bienvenue chez Anna's Touch ! 🎉", text, html)

            # 2. DEMANDE DE RÉSERVATION (Client & Admin)
            elif email_type == 'booking':
                service_name = data.get('service')
                nice_date = data.get('nice_date')
                
                # Mail Client
                text_client = f"Bonjour {client_name},\nVotre demande de réservation pour {service_name} le {nice_date} a bien été envoyée. Un administrateur vous contactera pour la confirmer."
                html_client = get_html_template("Demande de réservation envoyée", f"<p>Bonjour <strong>{client_name}</strong>,</p><p>Votre demande de réservation pour la prestation <strong>{service_name}</strong> le <strong>{nice_date}</strong> a bien été prise en compte.</p><p>⚠️ <em>Attention : Ce rendez-vous est en attente. Un membre de notre équipe va l'examiner et vous recevrez un email de confirmation très bientôt.</em></p>")
                send_mail(client_email, "Votre demande de réservation ⏳", text_client, html_client)

                # Mail Admin
                text_admin = f"Nouvelle demande de réservation.\nClient: {client_name} ({client_email})\nPrestation: {service_name}\nDate: {nice_date}"
                html_admin = get_html_template("Nouvelle Demande !", f"<p>Un client vient de faire une demande de réservation :</p><ul><li><strong>Client :</strong> {client_name}</li><li><strong>Email :</strong> {client_email}</li><li><strong>Prestation :</strong> {service_name}</li><li><strong>Date :</strong> {nice_date}</li></ul><p>Veuillez vous connecter à l'espace Admin pour confirmer ou annuler ce rendez-vous.</p>")
                send_mail(ADMIN_EMAIL, f"🔴 NOUVELLE DEMANDE - {client_name}", text_admin, html_admin)

            # 3. CONFIRMATION ADMIN (Le RDV est validé)
            elif email_type == 'admin_confirmation':
                service_name = data.get('service')
                nice_date = data.get('nice_date')
                raw_date = data.get('raw_date')
                
                ics_data = create_ics_content(client_name, raw_date, client_email, service_name)
                text = f"Bonjour {client_name},\nBonne nouvelle ! Votre réservation pour {service_name} le {nice_date} a été confirmée."
                html = get_html_template("Rendez-vous Confirmé ! ✅", f"<p>Bonjour <strong>{client_name}</strong>,</p><p>Excellente nouvelle ! Votre réservation pour <strong>{service_name}</strong> le <strong>{nice_date}</strong> a été validée par notre équipe.</p><p>Ajoutez l'événement à votre agenda grâce à la pièce jointe pour activer vos rappels automatiques. À très bientôt !</p>")
                send_mail(client_email, "Votre rendez-vous est confirmé ! ✅", text, html, ics_data)

            # 4. MESSAGE DIRECT DEPUIS LE DASHBOARD ADMIN
            elif email_type == 'direct_message':
                subject = data.get('subject', 'Message de Anna\'s Touch')
                message = data.get('message', '')
                text = f"Bonjour {client_name},\n\n{message}"
                html = get_html_template(subject, f"<p>Bonjour <strong>{client_name}</strong>,</p><p>{message}</p>")
                send_mail(client_email, subject, text, html)

        return jsonify({"status": "Emails envoyés avec succès !"}), 200

    except Exception as e:
        print(f"Erreur d'envoi: {e}")
        return jsonify({"error": str(e)}), 500

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


##############################
def send_verify_email(to_email, user_verification_key):
    try:
        # Create a gmail fullflaskdemomail
        # Enable (turn on) 2 step verification/factor in the google account manager
        # Visit: https://myaccount.google.com/apppasswords
        # Copy the key

        # Email and password of the sender's Gmail account
        sender_email = "sebschyb.dev@gmail.com"
        password = "eegt vaob dtvf sclh"  # If 2FA is on, use an App Password instead

        # Receiver email address
        receiver_email = to_email
        
        # Create the email message
        message = MIMEMultipart()
        message["From"] = "My company name"
        message["To"] = receiver_email
        message["Subject"] = "Please verify your account"

        # Body of the email
        body = f"""To verify your account, please <a href="http://127.0.0.1/verify/{user_verification_key}">click here</a>"""
        message.attach(MIMEText(body, "html"))

        # Connect to Gmail's SMTP server and send the email
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()  # Upgrade the connection to secure
            server.login(sender_email, password)
            server.sendmail(sender_email, receiver_email, message.as_string())
        print("Email sent successfully!")

        return "email sent"
       
    except Exception as ex:
        raise_custom_exception("cannot send email", 500)
    finally:
        pass

    def send_reset_email(to_email, reset_key):
        try:
            sender_email = "sebschyb.dev@gmail.com"
            password = "eegt vaob dtvf sclh"

            receiver_email = to_email
            
            message = MIMEMultipart()
            message["From"] = "twitter"
            message["To"] = receiver_email
            message["Subject"] = "Reset your password"

            reset_url = f"http://127.0.0.1/reset-password/{reset_key}"

            body = f"""
            To reset your password, please 
            <a href="{reset_url}">click here</a>.
            """
            message.attach(MIMEText(body, "html"))

            with smtplib.SMTP("smtp.gmail.com", 587) as server:
                server.starttls()
                server.login(sender_email, password)
                server.sendmail(sender_email, receiver_email, message.as_string())

            return "email sent"

        except Exception as ex:
            raise_custom_exception("cannot send email", 500)

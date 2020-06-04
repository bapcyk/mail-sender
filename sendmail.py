import common
import os
import smtplib
import getpass
from email.mime.multipart import MIMEMultipart 
from email.mime.text import MIMEText 
from email.mime.base import MIMEBase 
from email import encoders 


class MailSender:
    host = None
    port = None
    use_ssl = True
    sender_email = None
    sender_password = None

    def __init__(self, host, port, sender_email, sender_password, use_ssl=False):
        if '@' not in sender_email:
            raise common.MailError("Invalid sender email address: '%s', expected '@' somewhere in it" % sender_email)
        self.sender_email = sender_email
        if not sender_password:
            self.sender_password = getpass.getpass('Enter SMTP password: ')
        else:
            self.sender_password = sender_password
        self.host = host
        self.port = port or 587
        self.use_ssl = use_ssl

    def connect(self):
        if not all((self.host, self.port, self.sender_email, self.sender_password)):
            raise common.MailError('Invalid SMTP configuration required for SMTP server connection')
        if self.use_ssl:
            self.smtp = smtplib.SMTP_SSL(self.host, self.port)
        else:
            self.smtp = smtplib.SMTP(self.host, self.port)
        self.smtp.ehlo()
        try:
            self.smtp.starttls()
        except:
            pass
        self.smtp.login(self.sender_email, self.sender_password)

    def disconnect(self):
        #self.smtp.quit()
        self.smtp.close()

    def send(self, recipient, subject, text, html=None, attachments=[]):
        """Send email, may raise exception!"""
        if not isinstance(recipient, list):
            recipient = [recipient]
        recipient = ', '.join(recipient)
        msg = MIMEMultipart()
        msg['From'] = self.sender_email
        msg['To'] = recipient
        msg['Subject'] = subject
        if text:
            msg.attach(MIMEText(text, 'plain'))
        if html:
            msg.attach(MIMEText(html, 'html'))
        for att_name, att_data in attachments:
            m = MIMEBase('application', 'octet-stream')
            m.set_payload(att_data)
            encoders.encode_base64(m)
            m.add_header('Content-Disposition', "attachment; filename= %s" % att_name)
            msg.attach(m)
        email_content = msg.as_string()
        self.smtp.sendmail(self.sender_email, recipient, email_content)

import common
import attachment as att
import sendmail
import log
import chevron
import time
import json
import os


logger = None

class MailText:
    """Loader of text files of mail: bodies and subject"""
    path = None # path where from all were load

    body_text = None # text body
    body_html = None # html body
    subject = None # subject as one line

    def __init__(self, path):
        """Load from `path`: subject.txt, body.txt, body.html. Mandatory files are subject.txt
        and one of bodies - if it's not true, then an exception is raising
        """
        self.path = path
        try:
            p = os.path.join(self.path, 'body.txt')
            with open(p, 'r', encoding='utf-8') as f:
                self.body_text = f.read()
        except: pass

        try:
            p = os.path.join(self.path, 'body.html')
            with open(p, 'r', encoding='utf-8') as f:
                self.body_html = f.read()
        except: pass

        try:
            p = os.path.join(self.path, 'subject.txt')
            with open(p, 'r', encoding='utf-8') as f:
                self.subject = '; '.join(s.rstrip() for s in f.read().splitlines())
        except: pass

####################################################################################################
class MailData:
    """Loader of all mail data"""
    path = None # path to recipient folder
    name = None # only directory name
    job = None # parent job
    email = None # recipient email
    variables = {} # content of variables.json
    text_data = None # MailText
    attachments = None # Attachments object
    subject = None
    body_text = None
    body_html = None

    def __init__(self, path, job):
        self.path = path
        self.name = os.path.basename(path)
        self.job = job
        self.text_data = MailText(self.path)
        self.load_variables()
        self.load_email()
        self.load_attachments()
        self.subject = self.get_subject()
        self.body_text = self.get_body_text()
        self.body_html = self.get_body_html()
        if not self.subject:
            raise common.MailError("Mail load error in '%s': subject.txt is mandatory file" % self.path)
        if not (self.body_text or self.body_html):
            raise common.MailError("Mail load error in '%s': either body.txt or body.html are mandatory files" % self.path)

    def load_attachments(self):
        p = os.path.join(self.path, 'attachments')
        self.attachments = att.Attachments(p, lazy=True)

    def load_variables(self):
        try:
            p = os.path.join(self.path, 'variables.json')
            with open(p, 'r', encoding='utf-8') as f:
                self.variables = json.load(f)
        except: pass
        self.variables = self.job.merge_variables(self.variables)
        self.variables.update(self.auto_variables())

    def load_email(self):
        try:
            p = os.path.join(self.path, 'email.txt')
            with open(p, 'r', encoding='utf-8') as f:
                email = f.read()
        except Exception as x:
            raise common.MailError("Mail load error in '%s': %s" % (p, x))
        if '@' not in email:
            raise common.MailError("Mail load error in '%s': invalid email address" % p)
        self.email = email

    def auto_variables(self):
        d = {'email': self.email, 'recipient_dir': self.name, 'subject': self.subject}
        return d

    def get_body_text(self):
        """Returns individual or common, if individual is missing"""
        return self.text_data.body_text or self.job.subst_body_text_template(self.variables)

    def get_body_html(self):
        """Returns individual or common, if individual is missing"""
        return self.text_data.body_html or self.job.subst_body_html_template(self.variables)

    def get_subject(self):
        """Returns individual or common, if individual is missing"""
        return self.text_data.subject or self.job.subst_subject_template(self.variables)


####################################################################################################
class Job:
    config = None
    redolog = None
    redolog_file = None
    smtp = None
    templates = None
    attachments = None # common for all the job (for all recipients)
    maildata = [] # MailData list
    # common variables for all job, allows to have for example individual body template (per recipient)
    # but with some common part for all recipients
    variables = {}
    restart = False

    def __init__(self, path, restart=True):
        global logger
        logger = log.logger()

        self.path = path
        self.restart = restart
        self.load_config()
        self.load_redolog()
        self.load_variables()
        self.templates = MailText(self.path)
        self.attachments = att.Attachments(os.path.join(self.path, 'attachments'), lazy=False)
        self.load_maildata()
        self.smtp = sendmail.MailSender(self.config['smtp']['host'], self.config['smtp']['port'],
                self.config['auth']['user'], self.config['auth']['password'], self.config['smtp']['use_ssl'])
        logger.info('Connected to %s' % self.config['smtp']['host'])

    def dispose_redolog(self):
        if self.redolog_file is not None:
            self.redolog_file.close()
            self.redolog_file = None

    def dispose_smtp(self):
        if self.smtp is not None:
            self.smtp.disconnect()
            self.smtp = None

    def dispose(self):
        self.dispose_smtp()
        self.dispose_redolog()

    def __del__(self):
        self.dispose()

    def send_all(self):
        self.smtp.connect()
        nsent = 0
        for md in self.maildata:
            if md.path in self.redolog:
                # was done in previous session
                continue
            try:
                self.smtp.send(md.email, md.subject, md.body_text, md.body_html, md.attachments.items())
            except Exception:
                logger.exception('Failure for %s recipient' % md.name)
            else:
                logger.info('Sent email for %s recipient' % md.name)
                self.commit_in_redolog(md.path)
                nsent += 1
            # TODO if -1 then in parallel
            time.sleep(self.config['mail_pause_msec'] / 1000.)
        logger.info('Sent %d emails (%d skipped)' % (nsent, len(self.redolog)))
        self.smtp.disconnect()
        logger.info('disconnected %s' % self.smtp.host)

    def commit_in_redolog(self, path):
        """Commits some path of individual mail folder in redolog as successfully done"""
        self.redolog_file.write(path + '\n')
        self.redolog_file.flush()
        os.fsync(self.redolog_file.fileno())

    def load_maildata(self):
        self.maildata = []
        for p in os.scandir(self.path):
            if p.is_dir() and p.name != 'attachments':
                logger.info('Loading info about recipient %s ...' % p.name)
                md = MailData(p.path, self)
                md.attachments.merge(self.attachments)
                self.maildata.append(md)

    def load_config(self):
        try:
            with open(os.path.join(self.path, 'config.json'), 'r', encoding='utf-8') as f:
                self.config = json.load(f)
        except Exception as x:
            raise common.MailError("Job '%s' configuration file 'config.json' error: %s" % (self.path, x))

    def load_redolog(self):
        self.dispose_redolog()
        p = os.path.join(self.path, 'redo.log')
        if self.restart and os.path.exists(p):
            os.remove(p)
        try:
            # mode - create if does not exist, able to be read, buf pointer is at the end, so rewind it first
            self.redolog_file = open(p, 'a+', encoding='utf-8')
            self.redolog_file.seek(0, os.SEEK_SET)
            buf = self.redolog_file.read()
            self.redolog = set(s for s in (s.rstrip() for s in buf.splitlines()) if s)
            logger.info('Loaded redolog: %d recipients will be skipped' % len(self.redolog))
            # now file pointer is at the end, we are ready to append
        except Exception as x:
            raise common.MailError("Job '%s' redo.log load error: %s" % (self.path, x))

    def load_variables(self):
        try:
            with open(os.path.join(self.path, 'variables.json'), 'r', encoding='utf-8') as f:
                self.variables = json.load(f)
        except: pass

    def auto_variables(self):
        d = {'asctime': time.asctime()}
        return d

    def merge_variables(self, mail_variables):
        v = {}
        v.update(self.variables)
        v.update(mail_variables)
        v.update(self.auto_variables())
        return v

    def subst_subject_template(self, variables):
        return chevron.render(self.templates.subject, variables)

    def subst_body_text_template(self, variables):
        return chevron.render(self.templates.body_text, variables)

    def subst_body_html_template(self, variables):
        return chevron.render(self.templates.body_html, variables)

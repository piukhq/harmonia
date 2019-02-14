import wtforms

from app.api import utils


class LoginForm(utils.RedirectForm):
    email_address = wtforms.TextField("Email Address")
    password = wtforms.PasswordField("Password")

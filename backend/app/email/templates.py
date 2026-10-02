"""Transactional email templates: table layout + inline styles so they render in Gmail, Outlook and Apple Mail.

Each returns (subject, html, text).
"""

from html import escape

from ..config import settings

INK = "#0b0b0b"
PAPER = "#ece9e2"
CARD = "#f4f2ec"
HOT = "#ff4a00"
MUTED = "#5f5b54"
SANS = "Arial, Helvetica, sans-serif"
MONO = "'Courier New', Courier, monospace"


def _layout(preheader: str, heading: str, body_html: str, footer_note: str = "") -> str:
    note = footer_note or "You’re receiving this because you have a BurnoutAI account."
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="light"><title>{escape(heading)}</title></head>
<body style="margin:0;padding:0;background:{PAPER};">
<div style="display:none;max-height:0;overflow:hidden;opacity:0;">{escape(preheader)}</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{PAPER};padding:32px 12px;">
<tr><td align="center">
<table role="presentation" width="560" cellpadding="0" cellspacing="0" style="max-width:560px;width:100%;background:{CARD};border:2px solid {INK};">
  <tr><td style="height:10px;background:repeating-linear-gradient(-45deg,{INK} 0 10px,{HOT} 10px 20px);background-color:{HOT};font-size:0;line-height:0;">&nbsp;</td></tr>
  <tr><td style="padding:20px 28px;border-bottom:2px solid {INK};">
    <table role="presentation" cellpadding="0" cellspacing="0"><tr>
      <td style="width:14px;height:14px;background:{HOT};font-size:0;">&nbsp;</td>
      <td style="padding-left:10px;font-family:{SANS};font-size:18px;font-weight:900;letter-spacing:1px;color:{INK};">BURNOUTAI</td>
    </tr></table>
  </td></tr>
  <tr><td style="padding:28px;">
    <h1 style="margin:0 0 16px;font-family:{SANS};font-size:30px;line-height:1.05;font-weight:900;text-transform:uppercase;color:{INK};">{escape(heading)}</h1>
    {body_html}
  </td></tr>
  <tr><td style="padding:18px 28px;border-top:2px solid {INK};font-family:{MONO};font-size:11px;line-height:1.6;color:{MUTED};text-transform:uppercase;letter-spacing:1px;">
    {note}<br>BurnoutAI · risk assessment, not diagnosis.
  </td></tr>
</table>
</td></tr></table>
</body></html>"""


def _p(text: str) -> str:
    return f'<p style="margin:0 0 14px;font-family:{SANS};font-size:15px;line-height:1.55;color:{INK};">{text}</p>'


def _button(url: str, label: str) -> str:
    return (f'<table role="presentation" cellpadding="0" cellspacing="0" style="margin:8px 0 18px;"><tr>'
            f'<td style="background:{HOT};border:2px solid {INK};"><a href="{escape(url)}" '
            f'style="display:inline-block;padding:14px 22px;font-family:{MONO};font-size:13px;font-weight:bold;'
            f'letter-spacing:2px;text-transform:uppercase;color:{INK};text-decoration:none;">{escape(label)} &rarr;</a></td>'
            f'</tr></table>')


def _code(code: str) -> str:
    spaced = " ".join(code)
    return (f'<table role="presentation" cellpadding="0" cellspacing="0" style="margin:6px 0 18px;"><tr>'
            f'<td style="background:{INK};padding:16px 24px;font-family:{MONO};font-size:34px;font-weight:bold;'
            f'letter-spacing:6px;color:{PAPER};">{spaced}</td></tr></table>')


def verify_code(name: str, code: str) -> tuple[str, str, str]:
    subject = f"{code} is your BurnoutAI verification code"
    html = _layout(f"Your code is {code}. It expires in 10 minutes.", "Confirm your email",
                   _p(f"Hi {escape(name)}, enter this code to finish setting up your account:") + _code(code)
                   + _p("It expires in <b>10 minutes</b>. If you didn’t sign up, you can ignore this email."))
    text = f"Hi {name},\n\nYour BurnoutAI verification code is {code}\nIt expires in 10 minutes.\n\nIf you didn't sign up, ignore this email."
    return subject, html, text


def reset_code(name: str, code: str) -> tuple[str, str, str]:
    subject = f"{code} is your BurnoutAI password reset code"
    html = _layout(f"Reset code {code}. Expires in 10 minutes.", "Reset your password",
                   _p(f"Hi {escape(name)}, use this code to choose a new password:") + _code(code)
                   + _p("It expires in <b>10 minutes</b>. If you didn’t ask for this, your password is unchanged and you can ignore this email."))
    text = (f"Hi {name},\n\nYour BurnoutAI password reset code is {code}\nIt expires in 10 minutes.\n\n"
            "If you didn't ask for this, your password is unchanged.")
    return subject, html, text


def welcome(name: str) -> tuple[str, str, str]:
    url = f"{settings.app_url}/check-in"
    subject = "Welcome to BurnoutAI"
    html = _layout("One minute a day. See it coming.", f"Welcome, {name.split(' ')[0]}",
                   _p("You’re set. Here’s how it works:")
                   + _p("<b>1.</b> One 1-minute check-in a day.<br><b>2.</b> Once a week, six extra taps measure your burnout properly."
                        "<br><b>3.</b> After three check-ins you’ll see your trend, and an early warning if it’s heading for the burnout line.")
                   + _button(url, "Take today’s check-in")
                   + _p("Your check-ins are private to you. Organisations only ever see team-level aggregates, and only if you join one."))
    text = (f"Welcome, {name}.\n\nOne 1-minute check-in a day. Once a week, six extra taps measure your burnout properly. "
            f"After three check-ins you'll see your trend and get early warnings.\n\nTake today's check-in: {url}")
    return subject, html, text


def invite(org_name: str, inviter: str, role: str, url: str, min_group: int) -> tuple[str, str, str]:
    subject = f"{inviter} invited you to {org_name} on BurnoutAI"
    what = ("you’ll see team-level aggregates and manage invites" if role == "admin"
            else "a 1-minute daily check-in that warns you early if burnout is building")
    html = _layout(f"Join {org_name} on BurnoutAI.", f"Join {org_name}",
                   _p(f"{escape(inviter)} invited you to join <b>{escape(org_name)}</b> on BurnoutAI: {what}.")
                   + _button(url, "See the invitation")
                   + _p(f"<b>Your privacy:</b> {escape(org_name)} never sees your individual answers, only the average of your team, "
                        f"and only when at least {min_group} people have answered. You’ll see exactly what’s shared before you join."),
                   "You received this because someone at this organisation invited your email address.")
    text = (f"{inviter} invited you to join {org_name} on BurnoutAI ({what}).\n\nSee the invitation: {url}\n\n"
            f"{org_name} never sees your individual answers, only team averages from groups of {min_group}+.")
    return subject, html, text


def reminder(name: str, unsubscribe_url: str) -> tuple[str, str, str]:
    url = f"{settings.app_url}/check-in"
    subject = "Your 1-minute check-in"
    html = _layout("Six taps. One minute.", f"Morning, {name.split(' ')[0]}",
                   _p("Six taps, about a minute. Daily check-ins are what make the early warning work.")
                   + _button(url, "Check in now"),
                   f'Daily reminder. <a href="{escape(unsubscribe_url)}" style="color:{MUTED};">Turn off reminders</a>.')
    text = f"Six taps, about a minute: {url}\n\nTurn off reminders: {unsubscribe_url}"
    return subject, html, text


def password_changed(name: str) -> tuple[str, str, str]:
    subject = "Your BurnoutAI password was changed"
    html = _layout("Your password was changed.", "Password changed",
                   _p(f"Hi {escape(name)}, your password was just changed and other devices were signed out.")
                   + _p("If this wasn’t you, reset your password now:")
                   + _button(f"{settings.app_url}/forgot", "Reset password"))
    text = f"Hi {name}, your BurnoutAI password was just changed. If this wasn't you, reset it: {settings.app_url}/forgot"
    return subject, html, text


def account_deleted(name: str) -> tuple[str, str, str]:
    subject = "Your BurnoutAI account was deleted"
    html = _layout("Your account and data were deleted.", "Account deleted",
                   _p(f"Hi {escape(name)}, your account and all your check-ins have been permanently deleted. "
                      "We’re sorry to see you go, and we hope you’re doing okay."))
    text = f"Hi {name}, your BurnoutAI account and all your check-ins have been permanently deleted."
    return subject, html, text

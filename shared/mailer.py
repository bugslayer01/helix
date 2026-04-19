"""SMTP mailer. Used by LenderCo + HiringCo to deliver contest links to applicants.

For the demo we restrict the recipient domain to mailinator.com so the inbox
is publicly viewable without auth (judges + recruiters click the inbox link
during the demo and see the mail land live). Production deployment would lift
that restriction in the route layer.

Reads SMTP config from env. Failures are LOGGED, not raised — link issuance
must succeed even if email is down.
"""
from __future__ import annotations

import logging
import os
import re
import smtplib
import ssl
from email.message import EmailMessage
from typing import Any

log = logging.getLogger(__name__)

_MAILINATOR_RX = re.compile(r"^[A-Za-z0-9._+\-]+@mailinator\.com$")


def is_demo_email(addr: str) -> bool:
    """Demo policy: only allow @mailinator.com so judges can read the inbox."""
    return bool(_MAILINATOR_RX.match((addr or "").strip().lower()))


def mailinator_inbox_url(addr: str) -> str:
    local = addr.split("@", 1)[0]
    return f"https://www.mailinator.com/v4/public/inboxes.jsp?to={local}"


def _config() -> dict[str, Any] | None:
    host = os.environ.get("SMTP_HOST")
    user = os.environ.get("SMTP_USER")
    pwd = os.environ.get("SMTP_PASSWORD")
    if not (host and user and pwd):
        return None
    return {
        "host": host,
        "port": int(os.environ.get("SMTP_PORT", 587)),
        "user": user,
        "password": pwd,
        "from_name": os.environ.get("SMTP_FROM_NAME", "Recourse"),
        "from_addr": os.environ.get("SMTP_FROM_ADDR", user),
    }


def render_contest_email(
    *,
    applicant_name: str,
    customer_name: str,
    case_ref: str,
    decision_summary: str,
    contest_url: str,
    expires_in_hours: int = 24,
    legal_citation: str = "GDPR Art. 22(3) · DPDP Section 11",
) -> tuple[str, str, str]:
    """Return (subject, plain_body, html_body) for a contest link mail."""
    subject = f"You can contest your {customer_name} decision — case {case_ref}"
    plain = (
        f"Hi {applicant_name},\n\n"
        f"{customer_name} reached an automated decision on your case {case_ref}: {decision_summary}.\n\n"
        f"Under {legal_citation}, you have a right to contest this decision. We have set up a\n"
        f"secure portal where you can review the model's reasoning, submit counter-evidence,\n"
        f"and have the decision re-evaluated.\n\n"
        f"Open the contest portal:\n{contest_url}\n\n"
        f"This link expires in {expires_in_hours} hours. You will be asked to confirm your\n"
        f"date of birth before the contest opens.\n\n"
        f"— Recourse · Independent contestation portal"
    )
    html = f"""<!doctype html>
<html lang="en">
  <body style="margin:0;padding:0;background:#faf7f2;font-family:Inter,system-ui,sans-serif;color:#1a1815;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#faf7f2;padding:32px 16px;">
      <tr>
        <td align="center">
          <table role="presentation" width="560" cellpadding="0" cellspacing="0" border="0" style="max-width:560px;background:#ffffff;border:1px solid #e2dcd0;border-radius:12px;overflow:hidden;">
            <tr>
              <td style="padding:24px 32px 8px;border-bottom:1px solid #e2dcd0;">
                <div style="display:inline-block;width:32px;height:32px;border-radius:50%;background:#1a1815;vertical-align:middle;"></div>
                <div style="display:inline-block;margin-left:12px;vertical-align:middle;">
                  <div style="font-family:Fraunces,Georgia,serif;font-size:18px;letter-spacing:-0.01em;color:#1a1815;">Recourse</div>
                  <div style="font-size:11px;letter-spacing:0.18em;text-transform:uppercase;color:#5d5649;margin-top:2px;">Independent contestation portal</div>
                </div>
              </td>
            </tr>
            <tr>
              <td style="padding:32px;">
                <div style="font-size:11px;letter-spacing:0.18em;text-transform:uppercase;color:#b5412b;margin-bottom:8px;">{customer_name} · case {case_ref}</div>
                <h1 style="margin:0 0 16px;font-family:Fraunces,Georgia,serif;font-size:28px;line-height:1.15;color:#1a1815;">You can contest this decision.</h1>
                <p style="margin:0 0 16px;font-size:15px;line-height:1.6;color:#1a1815;">Hi <strong>{applicant_name}</strong>,</p>
                <p style="margin:0 0 16px;font-size:15px;line-height:1.6;color:#5d5649;">
                  {customer_name} reached an automated decision on your case: <strong>{decision_summary}</strong>.
                  Under <strong>{legal_citation}</strong>, you have a statutory right to challenge this decision and have a model re-run on corrected information.
                </p>
                <p style="margin:0 0 28px;font-size:15px;line-height:1.6;color:#5d5649;">
                  Click below to review the model's reasoning, attach counter-evidence, and trigger a re-evaluation.
                </p>
                <table role="presentation" cellpadding="0" cellspacing="0" border="0" style="margin:0 auto;">
                  <tr>
                    <td align="center" style="border-radius:8px;background:#b5412b;">
                      <a href="{contest_url}" style="display:inline-block;padding:14px 28px;font-size:15px;font-weight:600;color:#ffffff;text-decoration:none;border-radius:8px;">Open contest portal →</a>
                    </td>
                  </tr>
                </table>
                <p style="margin:28px 0 0;font-size:12px;line-height:1.5;color:#5d5649;text-align:center;">
                  Link expires in <strong>{expires_in_hours} hours</strong>. You will be asked to confirm your date of birth before the contest opens.
                </p>
                <p style="margin:24px 0 0;font-size:11px;line-height:1.5;color:#5d5649;text-align:center;word-break:break-all;">
                  If the button does not work, paste this URL into your browser:<br/>
                  <span style="font-family:JetBrains Mono,monospace;color:#1a1815;">{contest_url}</span>
                </p>
              </td>
            </tr>
            <tr>
              <td style="padding:16px 32px;border-top:1px solid #e2dcd0;background:#f4efe6;">
                <div style="font-size:11px;line-height:1.5;color:#5d5649;text-align:center;">
                  Recourse is an independent contestation layer. Your evidence is encrypted at rest and never leaves the underwriting boundary. Audit chain SHA-256 sealed.
                </div>
              </td>
            </tr>
          </table>
          <div style="margin-top:16px;font-size:10px;color:#9b9387;letter-spacing:0.1em;text-transform:uppercase;">{legal_citation}</div>
        </td>
      </tr>
    </table>
  </body>
</html>"""
    return subject, plain, html


def send_contest_email(
    *,
    to: str,
    applicant_name: str,
    customer_name: str,
    case_ref: str,
    decision_summary: str,
    contest_url: str,
    expires_in_hours: int = 24,
) -> dict[str, Any]:
    """Send the contest-link email. Returns ``{ok, mailinator_inbox?, error?}``.

    Failures never raise — caller still wants to return the link to the recruiter
    even if mail delivery fails.
    """
    if not is_demo_email(to):
        return {"ok": False, "error": "recipient_not_mailinator", "to": to}
    cfg = _config()
    if not cfg:
        return {"ok": False, "error": "smtp_not_configured", "to": to}

    subject, plain, html = render_contest_email(
        applicant_name=applicant_name,
        customer_name=customer_name,
        case_ref=case_ref,
        decision_summary=decision_summary,
        contest_url=contest_url,
        expires_in_hours=expires_in_hours,
    )
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = f"{cfg['from_name']} <{cfg['from_addr']}>"
    msg["To"] = to
    msg.set_content(plain)
    msg.add_alternative(html, subtype="html")

    try:
        ctx = ssl.create_default_context()
        with smtplib.SMTP(cfg["host"], cfg["port"], timeout=15) as s:
            s.starttls(context=ctx)
            s.login(cfg["user"], cfg["password"])
            s.send_message(msg)
        log.info("contest mail sent to=%s subject=%s", to, subject)
        return {"ok": True, "mailinator_inbox": mailinator_inbox_url(to)}
    except Exception as exc:  # network, auth, anything
        log.exception("contest mail failed to=%s", to)
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}", "to": to}

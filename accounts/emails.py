import html
import logging
from email.mime.image import MIMEImage
from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.core.mail import EmailMultiAlternatives

logger = logging.getLogger(__name__)

ASSETS = Path(__file__).resolve().parent / "email_assets"
GREEN = "#1F8A45"


def send_approval_email(user, role_label):
    if not user.email:
        raise ValueError("Ce compte n'a pas d'adresse e-mail.")
    name = user.first_name.strip()
    greeting_name = name or ""
    message = EmailMultiAlternatives(
        subject="Vérification accordée",
        body=_plain_body(greeting_name, role_label),
        from_email=settings.DEFAULT_FROM_EMAIL or settings.EMAIL_HOST_USER,
        to=[user.email],
    )
    message.attach_alternative(_html_body(greeting_name, role_label), "text/html")
    _attach_inline(message, "paw-logo", ASSETS / "paw_logo.png")
    _attach_inline(message, "animals", ASSETS / "animals.png")
    message.send(fail_silently=False)


def notify_approval(request, user, role_label):
    try:
        send_approval_email(user, role_label)
    except Exception:
        logger.exception("Approval email failed for user %s", user.pk)
        messages.error(
            request,
            "Le compte est validé, mais l'e-mail n'a pas pu être envoyé.",
        )
        return
    messages.success(request, f"E-mail de validation envoyé à {user.email}.")


def _attach_inline(message, content_id, path):
    data = path.read_bytes()
    subtype = "jpeg" if data.startswith(b"\xff\xd8\xff") else "png"
    image = MIMEImage(data, _subtype=subtype)
    image.add_header("Content-ID", f"<{content_id}>")
    image.add_header("Content-Disposition", "inline", filename=f"{content_id}.{subtype}")
    message.attach(image)


def _plain_body(name, role_label):
    hello = f"Bonjour {name}," if name else "Bonjour,"
    return (
        "Vérification accordée\n\n"
        f"{hello}\n\n"
        "Félicitations ! Votre demande de vérification pour PawRescue a été approuvée. "
        f"Votre compte {role_label} est désormais pleinement activé.\n\n"
        "Vous pouvez maintenant :\n"
        "- Vous connecter à PawRescue.\n"
        "- Compléter votre profil.\n"
        "- Échanger avec les personnes qui vous contactent.\n\n"
        "Merci pour votre engagement envers la cause animale !\n"
        "L'équipe PawRescue\n"
        "Sauver, Protéger, Aimer.\n"
    )


def _html_body(name, role_label):
    hello = f"Bonjour {html.escape(name)}," if name else "Bonjour,"
    role = html.escape(role_label)
    return f"""\
<!DOCTYPE html>
<html lang="fr">
<body style="margin:0;padding:0;background:#F4F8F5;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#F4F8F5;padding:24px 12px;">
    <tr>
      <td align="center">
        <table role="presentation" width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;background:#ffffff;border-radius:16px;overflow:hidden;">
          <tr>
            <td style="background:#E7F5EC;padding:22px 28px;">
              <table role="presentation" cellpadding="0" cellspacing="0">
                <tr>
                  <td style="vertical-align:middle;">
                    <img src="cid:paw-logo" width="42" height="42" alt="" style="display:block;border:0;">
                  </td>
                  <td style="vertical-align:middle;padding-left:10px;font-family:Arial,Helvetica,sans-serif;font-size:26px;font-weight:800;color:{GREEN};">
                    PawRescue
                  </td>
                </tr>
              </table>
            </td>
          </tr>
          <tr>
            <td style="padding:28px 28px 8px 28px;font-family:Arial,Helvetica,sans-serif;">
              <table role="presentation" cellpadding="0" cellspacing="0">
                <tr>
                  <td style="font-size:28px;line-height:1.2;font-weight:800;color:#243028;">
                    Vérification accordée !
                  </td>
                  <td style="padding-left:10px;vertical-align:middle;">
                    <span style="display:inline-block;width:28px;height:28px;line-height:28px;border-radius:14px;background:{GREEN};color:#ffffff;font-size:16px;font-weight:700;text-align:center;">&#10003;</span>
                  </td>
                </tr>
              </table>
            </td>
          </tr>
          <tr>
            <td style="padding:12px 28px 0 28px;">
              <img src="cid:animals" width="544" alt="" style="display:block;width:100%;max-width:544px;height:auto;border:0;border-radius:12px;">
            </td>
          </tr>
          <tr>
            <td style="padding:22px 28px 8px 28px;font-family:Arial,Helvetica,sans-serif;font-size:16px;line-height:1.5;color:#243028;">
              {hello}
            </td>
          </tr>
          <tr>
            <td style="padding:0 28px 8px 28px;font-family:Arial,Helvetica,sans-serif;font-size:16px;line-height:1.55;color:#243028;">
              Félicitations ! Votre demande de vérification pour PawRescue a été approuvée.
              Votre compte {role} est désormais pleinement activé.
            </td>
          </tr>
          <tr>
            <td style="padding:12px 28px 6px 28px;font-family:Arial,Helvetica,sans-serif;font-size:16px;font-weight:700;color:#243028;">
              Vous pouvez maintenant :
            </td>
          </tr>
          <tr>
            <td style="padding:0 28px 8px 28px;">
              {_bullet("Vous connecter à PawRescue.")}
              {_bullet("Compléter votre profil.")}
              {_bullet("Échanger avec les personnes qui vous contactent.")}
            </td>
          </tr>
          <tr>
            <td style="padding:16px 28px 4px 28px;font-family:Arial,Helvetica,sans-serif;font-size:16px;line-height:1.5;color:#243028;">
              Merci pour votre engagement envers la cause animale !
            </td>
          </tr>
          <tr>
            <td style="padding:14px 28px 28px 28px;font-family:Arial,Helvetica,sans-serif;">
              <div style="font-size:16px;font-weight:700;color:#243028;">L'équipe PawRescue</div>
              <div style="margin-top:4px;font-size:14px;color:{GREEN};">Sauver, Protéger, Aimer.</div>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""


def _bullet(text):
    return (
        '<table role="presentation" cellpadding="0" cellspacing="0" style="margin:0 0 8px 0;">'
        "<tr>"
        f'<td style="vertical-align:top;padding:2px 8px 0 0;color:{GREEN};font-size:16px;">&#9679;</td>'
        f'<td style="font-family:Arial,Helvetica,sans-serif;font-size:16px;line-height:1.45;color:#243028;">{text}</td>'
        "</tr></table>"
    )

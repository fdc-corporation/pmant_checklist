from odoo import http
from odoo.http import request
from markupsafe import escape as esc
import logging

_logger = logging.getLogger(__name__)


class WebForm(http.Controller):

    @http.route(
        "/my/equipos/<int:equipo_id>/checklist/<int:plantilla_id>",
        type="http", auth="public", website=True
    )
    def show_checklist(self, equipo_id, plantilla_id, **kwargs):
        env = request.env
        equipo = env["maintenance.equipment"].sudo().browse(equipo_id)
        plantilla = env["pmant.checklist"].sudo().browse(plantilla_id)
        if not equipo.exists() or not plantilla.exists():
            return request.not_found()

        return request.render(
            "pmant_checklist.checklist_template",
            {"equipo": equipo, "plantilla": plantilla},
        )



    @http.route("/my/equipo/<int:equipo_id>/checklist/historial", type="http", auth="public", website=True)
    def checklist_historial(self, equipo_id, **kwargs):
        env = request.env
        equipo = env["maintenance.equipment"].sudo().browse(equipo_id)
        if not equipo.exists():
            return request.not_found()

        grupos = env["pmant.checklist.group"].sudo().search(
            [("equipo_id", "=", equipo.id)],
            order="create_date desc"
        )

        return request.render(
            "pmant_checklist.respuestas_pmant",   # ← usa este ID de plantilla
            {
                "equipo": equipo,
                "respuestas": grupos,  # tu variable 'respuestas' ahora son grupos
            },
        )


    @http.route(
        "/checklist/submit/<int:equipo_id>/<int:plantilla_id>",
        type="http", auth="public", website=True, csrf=False
    )
    def submit_checklist(self, equipo_id, plantilla_id, **post):
        env = request.env
        equipo = env["maintenance.equipment"].sudo().browse(equipo_id)
        plantilla = env["pmant.checklist"].sudo().browse(plantilla_id)
        if not equipo.exists() or not plantilla.exists():
            return request.not_found()

        # URL de detalle para los botones en correo
        base_url = (
            env["ir.config_parameter"].sudo()
            .get_param("web.base.url", request.httprequest.host_url.rstrip("/"))
        )
        url_detalle = f"{base_url}/my/equipos/{equipo.id}/detalles"

        respuestas_creadas = []
        preguntas_con_no = []

        # Un solo grupo para este envío
        grupo = env["pmant.checklist.group"].sudo().create({
            "equipo_id": equipo.id,
            "name": "New",  # se asignará secuencia en create()
        })

        # === Parseo de respuestas del formulario ===
        for pregunta in plantilla.line_questions:
            vals = {
                "question_id": pregunta.id,
                "equipo_id": equipo.id,
                "group_id": grupo.id,
                "usuario_responsable": env.user.id,
            }

            # Respuesta principal
            if pregunta.tipo_respuesta == "si_no":
                raw = post.get(f"respuesta_{pregunta.id}_si_no")
                raw = raw if raw in ("si", "no") else "no"
                is_yes = (raw == "si")
                vals["respuesta_si_no"] = is_yes
                if not is_yes:
                    preguntas_con_no.append(pregunta)

            elif pregunta.tipo_respuesta == "texto":
                texto = (post.get(f"respuesta_{pregunta.id}_texto") or "").strip()
                if texto:
                    vals["respuesta_texto"] = texto

            # Comentario por pregunta (checkbox + textarea)
            if post.get(f"comentario_{pregunta.id}"):
                vals["is_comentario"] = True
                comentario_txt = (post.get(f"comentario_texto_{pregunta.id}") or "").strip()
                vals["comentario"] = comentario_txt

            resp = env["pmant.checklist.respuesta"].sudo().create(vals)
            respuestas_creadas.append(resp)

        # === Destinatarios ===
        destinatarios = set()
        grp = env.ref("pmant.group_pmant_planner_tarea", raise_if_not_found=False)
        if grp:
            destinatarios |= {u.email for u in grp.sudo().users if u.email}

        if getattr(equipo, "propietario", False) and equipo.propietario.email:
            destinatarios.add(equipo.propietario.email)
        if getattr(equipo, "ubicacion", False) and equipo.ubicacion.email:
            destinatarios.add(equipo.ubicacion.email)

        email_to = ",".join(sorted(e for e in destinatarios if e))
        email_from = (env.company.sudo().email) or "noreply@tudominio.com"

        # === Correo 1: Resumen completo ===
        try:
            if email_to:
                items_html = []
                for r in respuestas_creadas:
                    # valor principal
                    if r.respuesta_texto:
                        respuesta_txt = esc(r.respuesta_texto)
                    else:
                        respuesta_txt = "Sí" if getattr(r, "respuesta_si_no", False) else "No"

                    li = f"<li><strong>{esc(r.question_id.name)}</strong>: {respuesta_txt}"
                    # comentario por pregunta (si lo hay)
                    if getattr(r, "is_comentario", False) and getattr(r, "comentario", ""):
                        li += f"<br/><span style='color:#666'><em>Comentario:</em> {esc(r.comentario)}</span>"
                    li += "</li>"
                    items_html.append(li)

                cuerpo_html = f"""
                <div style="font-family: Arial, sans-serif; font-size:14px; color:#333; line-height:1.6; max-width:680px;">
                  <p>Hola,</p>
                  <p>Se ha completado un checklist para el equipo
                     <strong style="color:#004080;">{esc(equipo.name)}</strong>.
                  </p>
                  <ul style="padding-left:20px; margin: 10px 0;">
                    {''.join(items_html)}
                  </ul>
                  <div style="margin:24px 0;">
                    <a href="{url_detalle}" style="
                        background:#004080; color:#fff; padding:12px 18px;
                        text-decoration:none; border-radius:6px; font-weight:600; display:inline-block;">
                      Ver detalles del equipo
                    </a>
                  </div>
                  <p style="color:#999;">Este es un mensaje automático, por favor no responder.</p>
                </div>
                """

                env["mail.mail"].sudo().create({
                    "subject": f"Checklist completado - {equipo.name}",
                    "body_html": cuerpo_html,
                    "email_to": email_to,
                    "email_from": email_from,
                }).send()
            else:
                _logger.warning("Checklist: no se encontraron destinatarios (grupo/propietario/ubicación).")
        except Exception as e:
            _logger.exception("Error al enviar correo resumen de checklist: %s", e)

        # === Correo 2: Alerta si hubo alguna respuesta "No" ===
        try:
            if preguntas_con_no:
                usuarios = grp.users
                for usuario in usuarios:
                    vendedor = usuario.partner_id
                    request.env["crm.lead"].sudo().create({
                        "name": f"Alerta Checklist - {equipo.name}",
                        "type": "opportunity",
                        "partner_id" : equipo.propietario.id if equipo.propietario else equipo.ubicacion.id ,
                        "user_id": vendedor.id,
                        "description": "Se detectaron respuestas negativas en el checklist del equipo.",
                        "automated_probability": 50,
                        "equipo_tarea" : [(6,0, [equipo.id])],
                        "ubicacion" : equipo.ubicacion.id
                    })
                
            if email_to and preguntas_con_no:
                items_no = "".join(
                    f"<li><strong>{esc(p.name)}</strong></li>" for p in preguntas_con_no
                )
                cuerpo_alerta = f"""
                <div style="font-family: Arial, sans-serif; font-size:14px; color:#333; line-height:1.6; max-width:680px;">
                  <p>
                    <strong style="color:#dc3545;">⚠ Atención:</strong>
                    Se detectaron respuestas negativas en el checklist del equipo
                    <strong style="color:#004080;">{esc(equipo.name)}</strong>.
                  </p>
                  <p>Preguntas con respuesta <strong style="color:#dc3545;">"No"</strong>:</p>
                  <ul style="padding-left:20px; margin: 10px 0 20px;">
                    {items_no}
                  </ul>
                  <div style="margin:24px 0;">
                    <a href="{url_detalle}" style="
                        background:#dc3545; color:#fff; padding:12px 18px;
                        text-decoration:none; border-radius:6px; font-weight:600; display:inline-block;">
                      Ver detalles del equipo
                    </a>
                  </div>
                  <p style="color:#999;">Por favor, revise el estado del equipo.</p>
                </div>
                """
                env["mail.mail"].sudo().create({
                    "subject": f"⚠ Alerta - Respuestas negativas en checklist de {equipo.name}",
                    "body_html": cuerpo_alerta,
                    "email_to": email_to,
                    "email_from": email_from,
                }).send()
                
        except Exception as e:
            _logger.exception("Error al enviar correo de alerta del checklist: %s", e)

        return request.render("pmant_checklist.template_checklist_thanks", {"equipo": equipo})

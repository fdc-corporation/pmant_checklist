from odoo import http
from odoo.http import request
import logging
_logger = logging.getLogger(__name__)

class WebForm(http.Controller):

    @http.route('/my/equipos/<int:equipo_id>/checklist/<int:plantilla_id>', type='http', auth='public', website=True)
    def show_checklist(self, equipo_id, plantilla_id, **kwargs):
        equipo = request.env['maintenance.equipment'].browse(equipo_id)
        plantilla = request.env['pmant.checklist'].browse(plantilla_id)
        if not equipo or not plantilla:
            return request.not_found()

        return request.render('pmant_checklist.checklist_template', {
            'equipo': equipo,
            'plantilla': plantilla,
        })

    @http.route('/checklist/submit/<int:equipo_id>/<int:plantilla_id>', type='http', auth='public', website=True, csrf=False)
    def submit_checklist(self, equipo_id, plantilla_id, **post):
        equipo = request.env['maintenance.equipment'].sudo().browse(equipo_id)
        plantilla = request.env['pmant.checklist'].sudo().browse(plantilla_id)

        if not equipo.exists() or not plantilla.exists():
            return request.not_found()

        respuestas_creadas = []
        respuestas_con_no = []

        for pregunta in plantilla.line_questions:
            grupo_respuestas = request.env['pmant.checklist.group'].sudo().create({
                'name': request.env['ir.sequence'].next_by_code('pmant.checklist.group')
            })
            respuesta_vals = {
                'question_id': pregunta.id,
                'equipo_id': equipo.id,
                'group_id': grupo_respuestas.id,
                'usuario_responsable': request.env.user.id,
            }

            if pregunta.tipo_respuesta == 'texto':
                respuesta_texto = post.get(f'respuesta_{pregunta.id}_texto', '').strip()
                if respuesta_texto:
                    respuesta_vals['respuesta_texto'] = respuesta_texto

            elif pregunta.tipo_respuesta == 'si_no':
                respuesta_si_no = post.get(f'respuesta_{pregunta.id}_si_no')
                respuesta_vals['respuesta_si_no'] = bool(respuesta_si_no)
                if not bool(respuesta_si_no):  # Solo si la respuesta es "No"
                    respuestas_con_no.append(pregunta)

            if post.get(f'comentario_{pregunta.id}'):
                respuesta_vals['is_comentario'] = True
                comentario = post.get(f'comentario_texto_{pregunta.id}', '').strip()
                respuesta_vals['comentario'] = comentario

            respuesta = request.env['pmant.checklist.respuesta'].sudo().create(respuesta_vals)
            respuestas_creadas.append(respuesta)

        # === Recolectar destinatarios ===
        try:
            group_users = request.env.ref('pmant.group_recibir_notificacion_web').sudo().users
            emails = [u.email for u in group_users if u.email]

            if equipo.propietario and equipo.propietario.email:
                emails.append(equipo.propietario.email)

            if equipo.ubicacion and equipo.ubicacion.email:
                emails.append(equipo.ubicacion.email)

            email_to = ",".join(set(filter(None, emails)))

            cuerpo_html = f"""
            <div style="font-family: Arial, sans-serif; font-size: 14px; color: #333333; line-height: 1.6; max-width: 600px;">
                <p>Hola,</p>
                
                <p>Se ha completado un checklist para el equipo: <strong style="color:#004080;">{equipo.name}</strong></p>
                
                <ul style="padding-left: 20px;">
            """

            for r in respuestas_creadas:
                respuesta = r.respuesta_texto if r.respuesta_texto else ('Sí' if r.respuesta_si_no else 'No')
                cuerpo_html += f"""
                    <li>
                        <strong>{r.question_id.name}</strong>: {respuesta}
                """
                if r.is_comentario:
                    cuerpo_html += f"""<br/><span style="color: #666;"><em>Comentario:</em> {r.comentario}</span>"""
                cuerpo_html += "</li>"

            cuerpo_html += """
                </ul>

                <div style="margin: 25px 0;">
                    <a href="{url_detalle}" style="
                        background-color: #004080;
                        color: #ffffff;
                        padding: 12px 20px;
                        text-decoration: none;
                        border-radius: 4px;
                        font-weight: bold;
                        display: inline-block;
                    ">
                        Ver detalles del equipo
                    </a>
                </div>

                <p style="color: #999;">Este es un mensaje automático. Por favor, no responda a este correo.</p>
            </div>
            """

            if email_to:
                # Correo general
                email_general = {
                    'subject': f"Checklist completado - {equipo.name}",
                    'body_html': cuerpo_html,
                    'email_to': email_to,
                    'email_from': request.env.company.email or 'noreply@tudominio.com',
                }
                request.env['mail.mail'].sudo().create(email_general).send()

                # Correo de advertencia si hay alguna respuesta "No"
                if respuestas_con_no:
                    preguntas_no = ''.join(
                        f"<li><strong>{preg.name}</strong></li>"
                        for preg in respuestas_con_no
                    )
                    cuerpo_alerta = f"""
                    <div style="font-family: Arial, sans-serif; font-size: 14px; color: #333333; max-width: 600px; line-height: 1.6;">
                        <p style="margin-bottom: 15px;">
                            <strong style="color: #dc3545;">⚠ Atención:</strong> Se detectaron respuestas negativas en el checklist del equipo 
                            <strong style="color:#004080;">{equipo.name}</strong>.
                        </p>

                        <p style="margin-bottom: 10px;">Preguntas con respuesta <strong style="color: #dc3545;">"No"</strong>:</p>
                        
                        <ul style="padding-left: 20px; margin-top: 0; margin-bottom: 20px;">
                            {preguntas_no}
                        </ul>

                        <div style="margin: 25px 0;">
                            <a href="{url_detalle}" style="
                                background-color: #dc3545;
                                color: #ffffff;
                                padding: 12px 20px;
                                text-decoration: none;
                                border-radius: 4px;
                                font-weight: bold;
                                display: inline-block;
                            ">
                                Ver detalles del equipo
                            </a>
                        </div>

                        <p style="color: #999;">Por favor, revise el estado del equipo lo antes posible.</p>
                    </div>
                    """

                    email_alerta = {
                        'subject': f"⚠ Alerta - Respuestas negativas en checklist de {equipo.name}",
                        'body_html': cuerpo_alerta,
                        'email_to': email_to,
                        'email_from': request.env.company.email or 'noreply@tudominio.com',
                    }
                    request.env['mail.mail'].sudo().create(email_alerta).send()

            else:
                _logger.warning("No se encontraron destinatarios para el correo del checklist.")

        except Exception as e:
            _logger.error(f"Error al enviar correo de checklist: {e}")

        return request.render('pmant_checklist.template_checklist_thanks', {
            'equipo': equipo,
        })
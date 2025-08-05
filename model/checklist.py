from odoo import models, fields, _, api
from odoo.exceptions import UserError


class CheckList(models.Model):
    _name = "pmant.checklist"
    _description = "Checklist de Mantenimiento"


    name = fields.Char(string="Nombre del Checklist", required=True)
    description = fields.Text(string="Descripción")
    creado_por = fields.Many2one(
        comodel_name="res.users",
        string="Creado por",
        default=lambda self: self.env.user,
        readonly=True,
    )
    fecha_creacion = fields.Datetime(
        string="Fecha de Creación",
        default=fields.Datetime.now,
        readonly=True,
    )

    line_questions = fields.One2many(
        comodel_name="pmant.checklist.question",
        inverse_name="checklist_id",
        string="Preguntas del Checklist",
        help="Lista de preguntas asociadas a este checklist",
    )



class Question(models.Model):
    _name = "pmant.checklist.question"
    _description = "Pregunta del Checklist"

    name = fields.Char(string="Pregunta", required=True)
    checklist_id = fields.Many2one(
        comodel_name="pmant.checklist",
        string="Checklist Asociado",
        required=True,
        ondelete="cascade",
    )
    tipo_respuesta = fields.Selection(
        selection=[
            ("texto", "Texto"),
            ("si_no", "Sí/No"),
        ],
        string="Tipo de Respuesta",
        required=True,
        default="texto",
    )

class GroupChecklist(models.Model):
    _name = "pmant.checklist.group"
    _description = "Grupo de Checklists"

    name = fields.Char(string="Referencia", required=True, copy=False, readonly=True, default="New")
    respuestas_ids = fields.One2many(
        comodel_name="pmant.checklist.respuesta",
        inverse_name="group_id",
        string="Respuestas del Grupo",
        help="Respuestas asociadas a las preguntas del checklist de este grupo",
    )

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('pmant.checklist.group') or 'New'
        return super(GroupChecklist, self).create(vals)


class Respuesta(models.Model):
    _name = "pmant.checklist.respuesta"
    _description = "Respuesta a una Pregunta del Checklist"

    question_id = fields.Many2one(
        "pmant.checklist.question",
        string="Pregunta",
        required=True,
        ondelete="cascade",
    )
    group_id = fields.Many2one(
        "pmant.checklist.group",
        string="Grupo de Checklist",
        required=False,
        ondelete="cascade",
    )
    equipo_id = fields.Many2one(
        "maintenance.equipment",
        string="Equipo",
        required=True,
        ondelete="cascade",
    )
    respuesta_texto = fields.Text(string="Respuesta (Texto)")
    respuesta_si_no = fields.Boolean(string="Respuesta (Sí/No)")
    fecha_respuesta = fields.Datetime(
        string="Fecha de Respuesta", default=fields.Datetime.now, readonly=True
    )
    usuario_responsable = fields.Many2one(
        comodel_name="res.users",
        string="Usuario Responsable",
        default=lambda self: self.env.user,
        readonly=True,
    )
    is_comentario = fields.Boolean(
        string="Tiene comentarios?",
        help="Indica si esta respuesta es un comentario adicional",
        default=False,
    )
    comentario = fields.Text(
        string="Comentario Adicional",
        help="Comentario adicional sobre la respuesta, si aplica",
        default="",
    )



from odoo import models, fields, api

class VehicleService(models.Model):
    _name = 'vehicle.service'
    _description = 'Vehicle Service'

    name = fields.Char(default='New')

    vehicle_id = fields.Many2one(
        'vehicle.master',
        string="Vehicle",
        required=True
    )

    service_date = fields.Date(string="Service Date")
    description = fields.Text(string="Details")

    cost = fields.Float(string="Service Cost")

    state = fields.Selection([
        ('draft', 'Draft'),
        ('in_service', 'In Service'),
        ('done', 'Done')
    ], default='draft')

    def action_start(self):
        for rec in self:
            rec.vehicle_id.state = 'service'
            rec.state = 'in_service'

    def action_done(self):
        for rec in self:
            rec.vehicle_id.state = 'available'
            rec.state = 'done'

    #
    # def action_view_services(self):
    #     return {
    #         'type': 'ir.actions.act_window',
    #         'name': 'Services',
    #         'res_model': 'vehicle.service',
    #         'view_mode': 'tree,form',
    #         'domain': [('vehicle_id', '=', self.id)],
    #     }
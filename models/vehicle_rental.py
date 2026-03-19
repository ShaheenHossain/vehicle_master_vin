from odoo import models, fields, api
from odoo.exceptions import UserError

class VehicleRental(models.Model):
    _name = 'vehicle.rental'
    _description = 'Vehicle Rental'

    name = fields.Char(string="Rental Reference", required=True, copy=False, default='New')

    vehicle_id = fields.Many2one(
        'vehicle.master',
        string="Vehicle",
        required=True,
        domain="[('state','=','available')]"
    )

    partner_id = fields.Many2one('res.partner', string="Customer", required=True)

    start_date = fields.Datetime(string="Start Date", required=True)
    end_date = fields.Datetime(string="End Date")

    rent_price = fields.Float(string="Rent Price (Per Day)")
    total_amount = fields.Float(string="Total", compute='_compute_total', store=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('running', 'Running'),
        ('done', 'Done'),
        ('cancel', 'Cancelled')
    ], default='draft')

    @api.depends('start_date', 'end_date', 'rent_price')
    def _compute_total(self):
        for rec in self:
            if rec.start_date and rec.end_date:
                days = (rec.end_date - rec.start_date).days or 1
                rec.total_amount = days * rec.rent_price
            else:
                rec.total_amount = 0

    # START RENTAL
    def action_start(self):
        for rec in self:
            if rec.vehicle_id.state != 'available':
                raise UserError("Vehicle not available!")

            rec.vehicle_id.state = 'rented'
            rec.state = 'running'

    # END RENTAL
    def action_end(self):
        for rec in self:
            rec.vehicle_id.state = 'available'
            rec.state = 'done'

    # def action_view_rentals(self):
    #     return {
    #         'type': 'ir.actions.act_window',
    #         'name': 'Rentals',
    #         'res_model': 'vehicle.rental',
    #         'view_mode': 'tree,form',
    #         'domain': [('vehicle_id', '=', self.id)],
    #     }
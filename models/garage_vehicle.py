from odoo import models, fields, api, _


class GarageVehicle(models.Model):
    _name = 'garage.vehicle'
    _description = 'Vehicle Master'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'display_name'

    vin = fields.Char(string='VIN/Chassis Number', required=True, index=True, copy=False )
    license_plate = fields.Char(string='License Plate', required=True, tracking=True)
    partner_id = fields.Many2one('res.partner', string='Owner', tracking=True)

    brand = fields.Char(string='Brand')
    model = fields.Char(string='Model')
    variant = fields.Char(string='Variant / Type')

    first_registration_date = fields.Date(string='First Registration Date')
    current_mileage = fields.Integer(string='Current Mileage (KM)', tracking=True)

    # Relations
    sale_order_ids = fields.One2many(
        'sale.order', 'vehicle_id', string='Workshop Orders'
    )

    invoice_ids = fields.One2many(
        'account.move', 'vehicle_id', string='Invoices'
    )

    state = fields.Selection([
        ('customer', 'Customer Vehicle'),
        ('stock', 'Stock Vehicle'),
        ('company', 'Company Vehicle'),
        ('sold', 'Sold / Inactive')
    ], default='customer', tracking=True)

    stock_lot_id = fields.Many2one(
        'stock.production.lot', string='Stock Serial / VIN'
    )


    display_name = fields.Char(
        compute='_compute_display_name',
        store=True
    )

    # service_count = fields.Integer(
    #     string="Service Count",
    #     compute="_compute_service_count"
    # )

    # service_order_ids = fields.One2many(
    #     'vehicle.service.order',
    #     'vehicle_id',
    #     string='Service Orders'
    # )

    # service_order_ids = fields.One2many(
    #     'vehicle.service.order',
    #     'vehicle_id',
    #     string='Workshop Orders'  # Make sure required=True is NOT here
    # )


    vehicle_id = fields.Many2one(
        'garage.vehicle',
        string='Vehicle',
        required=True,
        tracking=True
    )

    # def _compute_service_count(self):
    #     for rec in self:
    #         rec.service_count = self.env['vehicle.service.order'].search_count([
    #             ('vehicle_id', '=', rec.id)
    #         ])

    def action_view_services(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Service Orders',
            'view_mode': 'tree,form',
            'res_model': 'vehicle.service.order',
            'domain': [('vehicle_id', '=', self.id)],
            'context': {'default_vehicle_id': self.id},
        }


    @api.depends('vin', 'license_plate', 'brand', 'model')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f"{rec.license_plate or ''} - {rec.brand or ''} {rec.model or ''} ({rec.vin or ''})"

    _sql_constraints = [
        ('vin_unique', 'unique(vin)', 'VIN must be unique!'),
    ]


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    vehicle_id = fields.Many2one(
        'garage.vehicle',
        string='Vehicle'
    )



    # @api.onchange('partner_id')
    # def _onchange_partner_vehicle(self):
    #     if self.partner_id:
    #         return {
    #             'domain': {
    #                 'vehicle_id': [('partner_id', '=', self.partner_id.id)]
    #             }
    #         }

class ResPartner(models.Model):
    _inherit = 'res.partner'

    # This allows one customer to have multiple vehicles
    vehicle_ids = fields.One2many('garage.vehicle', 'partner_id', string='Vehicles')



class AccountMove(models.Model):
    _inherit = 'account.move'

    vehicle_id = fields.Many2one(
        'garage.vehicle',
        string='Vehicle'
    )



class StockLot(models.Model):
    _inherit = 'stock.lot'

    vehicle_id = fields.Many2one('garage.vehicle', string='Vehicle Master')

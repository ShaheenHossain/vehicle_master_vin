from odoo import models, fields, api

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    inquiry_date = fields.Date(string="Inquiry Date")
    deadline_date = fields.Date(string="Deadline")

    # your_ref = fields.Many2one('res.partner', related='vehicle_id.your_ref', string='Your Ref', readonly=False)
    # our_ref = fields.Many2one('res.partner', related='vehicle_id.our_ref', string='Our Ref', readonly=False)

    your_ref = fields.Many2one('res.partner', string='Your Ref', compute='_compute_refs', store=True)
    our_ref = fields.Many2one('res.partner', string='Our Ref', compute='_compute_refs', store=True)

    @api.depends('vehicle_id')
    def _compute_refs(self):
        for rec in self:
            rec.your_ref = rec.vehicle_id.your_ref or False
            rec.our_ref = rec.vehicle_id.our_ref or False


    brand_id = fields.Many2one('vehicle.brand', string='Brand')
    model_id = fields.Many2one('vehicle.model', string='Model', domain="[('brand_id','=',brand_id)]")

    year = fields.Selection([(str(y), str(y)) for y in range(1980, 2031)],
        string='Year')

    year_from = fields.Integer(string="Year From")
    year_to = fields.Integer(string="Year To")
    variant_id = fields.Many2one('vehicle.variant', string='Variant', domain="[('model_id','=',model_id)]")
    vehicle_id = fields.Many2one('vehicle.master', string='Vehicle', domain="[('partner_id','=',partner_id)]")
    license_plate = fields.Char(related='vehicle_id.license_plate', string='License Plate', required=True)

    # first_registration = fields.Date(string='First Registration', store=True, readonly=False)
    first_registration = fields.Date(related='vehicle_id.first_registration', string='First Registration', store=True, readonly=False)

    mileage = fields.Integer(string='Mileage')

    type_code = fields.Char(string='Type Code')

    vin = fields.Char(related='vehicle_id.vin', store=True, readonly=False)
    color_id = fields.Many2one('vehicle.color', related='vehicle_id.color_id', store=True)

    fuel_type = fields.Char(related='vehicle_id.fuel_type', store=True, readonly=False)


    # fuel_type = fields.Selection(related='vehicle_id.fuel_type', store=True, readonly=False)
    master_number = fields.Char(related='vehicle_id.master_number', store=True, readonly=False)
    last_service_date = fields.Date(related='vehicle_id.last_service_date', string='Last Service Date', store=True, readonly=False)

    @api.onchange('partner_id')
    def _onchange_partner_id_vehicle_id(self):
        self.vehicle_id = False
        if self.partner_id:
            return {
                'domain': {
                    'vehicle_id': [('partner_id', '=', self.partner_id.id)]
                }
            }
        return {'domain': {'vehicle_id': []}}

    def _prepare_invoice(self):
        invoice_vals = super()._prepare_invoice()

        invoice_vals.update({
            'inquiry_date': self.inquiry_date,
            'deadline_date': self.deadline_date,
            'your_ref': self.your_ref.id if self.your_ref else False,
            'our_ref': self.our_ref.id if self.our_ref else False,
            'vehicle_id': self.vehicle_id.id if self.vehicle_id else False,

            # If these are Char fields
            'license_plate': self.license_plate,
            'vin': self.vin,
            'color_id': self.color_id.id if self.color_id else False,

            # Add these also if needed
            'fuel_type': self.fuel_type,
            'master_number': self.master_number,
            'first_registration': self.first_registration,
            'last_service_date': self.last_service_date,
        })

        return invoice_vals



class AccountMove(models.Model):
    _inherit = 'account.move'

    inquiry_date = fields.Date(string="Inquiry Date")
    deadline_date = fields.Date(string="Deadline")

    # Change these to related to match Sale Order behavior
    # your_ref = fields.Many2one('res.partner', related='vehicle_id.your_ref', string='Your Ref', store=True, readonly=False )
    # our_ref = fields.Many2one('res.partner', related='vehicle_id.our_ref', string='Our Ref', store=True, readonly=False)

    your_ref = fields.Many2one('res.partner', string='Your Ref', compute='_compute_refs', store=True)
    our_ref = fields.Many2one('res.partner', string='Our Ref', compute='_compute_refs', store=True)

    @api.depends('vehicle_id')
    def _compute_refs(self):
        for rec in self:
            rec.your_ref = rec.vehicle_id.your_ref or False
            rec.our_ref = rec.vehicle_id.our_ref or False


    vehicle_id = fields.Many2one('vehicle.master', string='Vehicle', domain="[('partner_id','=',partner_id)]")

    # Adding 'related' allows these to fill automatically when vehicle_id is selected
    license_plate = fields.Char(related='vehicle_id.license_plate', string='License Plate', store=True, readonly=False)
    vin = fields.Char(related='vehicle_id.vin', string='VIN/Chassis Number', store=True, readonly=False)
    color_id = fields.Many2one('vehicle.color', related='vehicle_id.color_id', string="Color", store=True)
    # fuel_type = fields.Selection(related='vehicle_id.fuel_type', string='Fuel Type', store=True, readonly=False)
    fuel_type = fields.Char(related='vehicle_id.fuel_type', store=True, readonly=False)


    master_number = fields.Char(related='vehicle_id.master_number', string='Master Number', store=True, readonly=False)
    first_registration = fields.Date(related='vehicle_id.first_registration', string='First Registration', store=True,
                                     readonly=False)
    last_service_date = fields.Date(related='vehicle_id.last_service_date', string='Last Service Date', store=True,
                                    readonly=False)

    # These usually stay manual per invoice
    mileage = fields.Integer(string='Mileage')
    type_code = fields.Char(string='Type Code')

    # This handles the filtering of vehicles when you select a customer on the Invoice
    @api.onchange('partner_id')
    def _onchange_partner_id_vehicle_id(self):
        self.vehicle_id = False
        if self.partner_id:
            return {
                'domain': {
                    'vehicle_id': [('partner_id', '=', self.partner_id.id)]
                }
            }
        return {'domain': {'vehicle_id': []}}




class StockPicking(models.Model):
    _inherit = 'stock.picking'

    inquiry_date = fields.Date(string="Inquiry Date")
    deadline_date = fields.Date(string="Deadline")

    your_ref = fields.Many2one('res.partner', string='Your Ref', compute='_compute_refs', store=True)
    our_ref = fields.Many2one('res.partner', string='Our Ref', compute='_compute_refs', store=True)

    @api.depends('vehicle_id')
    def _compute_refs(self):
        for rec in self:
            rec.your_ref = rec.vehicle_id.your_ref or False
            rec.our_ref = rec.vehicle_id.our_ref or False


    # vehicle_ids = fields.Many2many('vehicle.master', 'account_move_vehicle_rel',
    #         'move_id', 'vehicle_id', string='Vehicles')

    vehicle_id = fields.Many2one(
        'vehicle.master',
        string='Vehicle'
    )


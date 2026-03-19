from operator import index

from odoo import models, fields, api, _
from odoo.tools import format_date

class SaleOrder(models.Model):
    _inherit = 'sale.order'


    issue_place_id = fields.Many2one('vehicle.issue.place', string="Issue Place")
    issue_date = fields.Date(string="Issue Date")

    inquiry_date = fields.Date(string="Inquiry Date")
    deadline_date = fields.Date(string="Deadline")

    # your_ref = fields.Many2one('res.partner', related='vehicle_id.your_ref', string='Your Ref', readonly=False)
    # our_ref = fields.Many2one('res.partner', related='vehicle_id.our_ref', string='Our Ref', readonly=False)

    your_ref = fields.Many2one('res.partner', string='Your Ref', compute='_compute_refs', store=True)
    our_ref = fields.Many2one('res.partner', string='Our Ref', compute='_compute_refs', store=True)
    page_no = fields.Integer(string='Page No.')


    @api.depends('vehicle_id')
    def _compute_refs(self):
        for rec in self:
            rec.your_ref = rec.vehicle_id.your_ref or False
            rec.our_ref = rec.vehicle_id.our_ref or False

    @api.onchange('vehicle_id')
    def _onchange_vehicle_id(self):
        if self.vehicle_id:
            self.issue_place_id = self.vehicle_id.issue_place_id


    def action_confirm(self):
        res = super().action_confirm()

        for order in self:
            for line in order.order_line:
                vehicle = line.vehicle_id

                if not vehicle:
                    continue

                # Check availability
                if vehicle.state != 'available':
                    raise UserError(
                        f"Vehicle {vehicle.name or vehicle.vin} is not available!"
                    )

                # Mark as sold
                vehicle.write({
                    'state': 'sold',
                    'partner_id': order.partner_id.id,
                    'sale_order_id': order.id
                })

        return res






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
    master_number = fields.Char(related='vehicle_id.master_number', string="Master Number", store=True, readonly=False)
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
            'page_no': self.page_no if self.page_no else False,
            'vehicle_id': self.vehicle_id.id if self.vehicle_id else False,

            # If these are Char fields
            'license_plate': self.license_plate,
            'vin': self.vin,
            'issue_place_id': self.issue_place_id.id if self.issue_place_id else False,
            'color_id': self.color_id.id if self.color_id else False,

            # Add these also if needed
            'fuel_type': self.fuel_type,
            'master_number': self.master_number,
            'first_registration': self.first_registration,
            'last_service_date': self.last_service_date,
        })

        return invoice_vals


    def _compute_l10n_din5008_template_data(self):
        for record in self:
            data = []

            # if record.date_order:
            #     data.append((_("Quotation Date"), format_date(self.env, record.date_order)))
            #
            # if record.validity_date:
            #     data.append((_("Expiration"), format_date(self.env, record.validity_date)))

            # Your Reference
            if record.your_ref:
                data.append((_("Your Ref."), record.your_ref.name))

            # Our Reference
            if record.our_ref:
                data.append((_("Our Ref."), record.our_ref.name))

            # Inquiry Date
            if record.inquiry_date:
                data.append((_("Inquiry Date"), format_date(self.env, record.inquiry_date)))

            # Deadline Date
            if record.deadline_date:
                data.append((_("Deadline Date"), format_date(self.env, record.deadline_date)))

            # Page No.
            if record.page_no:
                data.append((_("Page No."), record.page_no))


            record.l10n_din5008_template_data = data



    def _compute_l10n_din5008_document_title(self):
        for record in self:
            if self._context.get('proforma'):
                record.l10n_din5008_document_title = _('Pro Forma Invoice %s') % (record.name or '')
            elif record.state in ('draft', 'sent'):
                record.l10n_din5008_document_title = _('Quotation %s') % (record.name or '')
            else:
                record.l10n_din5008_document_title = _('Sales Order %s') % (record.name or '')



class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    vehicle_id = fields.Many2one(
        'vehicle.master',
        string="Vehicle",
        domain="[('state','=','available')]"
    )

    lot_id = fields.Many2one(
        'stock.lot',
        string="VIN",
    )

    @api.onchange('vehicle_id')
    def _onchange_vehicle_id(self):
        if self.vehicle_id:
            self.product_id = self.vehicle_id.product_id
            self.lot_id = self.vehicle_id.lot_id
            self.price_unit = self.vehicle_id.sale_price



class AccountMove(models.Model):
    _inherit = 'account.move'

    issue_place_id = fields.Many2one('vehicle.issue.place', string="Issue Place")

    issue_date = fields.Date(string="Issue Date")

    inquiry_date = fields.Date(string="Inquiry Date")
    deadline_date = fields.Date(string="Deadline")

    # Change these to related to match Sale Order behavior
    # your_ref = fields.Many2one('res.partner', related='vehicle_id.your_ref', string='Your Ref', store=True, readonly=False )
    # our_ref = fields.Many2one('res.partner', related='vehicle_id.our_ref', string='Our Ref', store=True, readonly=False)

    your_ref = fields.Many2one('res.partner', string='Your Ref', compute='_compute_refs', store=True)
    our_ref = fields.Many2one('res.partner', string='Our Ref', compute='_compute_refs', store=True)
    page_no = fields.Integer(string='Page No.')

    @api.depends('vehicle_id')
    def _compute_refs(self):
        for rec in self:
            rec.your_ref = rec.vehicle_id.your_ref or False
            rec.our_ref = rec.vehicle_id.our_ref or False


    # vehicle_id = fields.Many2one('vehicle.master', string='Vehicle', domain="[('partner_id','=',partner_id)]")
    vehicle_id = fields.Many2one('vehicle.master', string='Vehicle', domain = "[('state','=','available')]")

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


    def _compute_l10n_din5008_document_title(self):
        for record in self:
            record.l10n_din5008_document_title = ''

            if record.move_type == 'out_invoice':
                if record.state == 'posted':
                    record.l10n_din5008_document_title = _('Invoice %s') % (record.name or '')
                elif record.state == 'draft':
                    record.l10n_din5008_document_title = _('Draft Invoice %s') % (record.name or '')
                elif record.state == 'cancel':
                    record.l10n_din5008_document_title = _('Cancelled Invoice %s') % (record.name or '')

            elif record.move_type == 'out_refund':
                record.l10n_din5008_document_title = _('Credit Note %s') % (record.name or '')

            elif record.move_type == 'in_refund':
                record.l10n_din5008_document_title = _('Vendor Credit Note %s') % (record.name or '')

            elif record.move_type == 'in_invoice':
                record.l10n_din5008_document_title = _('Vendor Bill %s') % (record.name or '')


    def _compute_l10n_din5008_template_data(self):
        for record in self:
            data = []

            # Invoice Information

            if record.invoice_date:
                data.append((_("Invoice Date"), format_date(self.env, record.invoice_date)))


            if record.invoice_origin:
                data.append((_("Source"), record.invoice_origin))

            # References
            if record.your_ref:
                data.append((_("Your Ref."), record.your_ref.name))

            if record.our_ref:
                data.append((_("Our Ref."), record.our_ref.name))

            # Custom Dates
            if record.inquiry_date:
                data.append((_("Inquiry Date"), format_date(self.env, record.inquiry_date)))

            if record.deadline_date:
                data.append((_("Deadline Date"), format_date(self.env, record.deadline_date)))

            # Page No.
            if record.page_no:
                data.append((_("Page No."), record.page_no))

            record.l10n_din5008_template_data = data





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


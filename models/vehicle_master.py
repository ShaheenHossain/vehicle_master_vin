import os

# These MUST be set before importing cv2, numpy, or odoo
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['VECLIB_MAXIMUM_THREADS'] = '1'
os.environ['NUMEXPR_NUM_THREADS'] = '1'

import numpy as np
import cv2
import logging
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import base64
import imghdr
import re
import requests
import pytesseract
from PIL import Image
import io
from datetime import datetime

import google.generativeai as genai
import json



_logger = logging.getLogger(__name__)



class VehicleMaster(models.Model):
    _name = 'vehicle.master'
    _description = 'Vehicle'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'

    # --- Owner / Halter (Boxes 1-8) ---
    owner_name = fields.Char(string="Owner Name")
    owner_id = fields.Char(string="Owner ID")
    owner_last_name = fields.Char(string="Last Name", help="Box 1")
    owner_first_name = fields.Char(string="First Name", help="Box 2")
    street = fields.Char(string="Street Address", help="Box 3/5")
    zip = fields.Char(string="Postal Code", help="Box 4")
    city = fields.Char(string="City / Town", help="Box 5")
    telephone = fields.Char(string="Telephone")
    phone = fields.Char(string="Phone")
    mobile = fields.Char(string="Mobile")
    fax = fields.Char(string="Fax")
    email = fields.Char(string="Email")
    owner_ref_uid = fields.Char(string="Reference / UID", help="Box 6")
    owner_dob = fields.Date(string="Date of Birth", help="Box 07")
    place_of_origin = fields.Char(string="Place of Origin", help="Box 08")

    # --- Insurance & Admin (Boxes 9-14) ---
    insurance_company = fields.Char(string="Insurance Company", help="Box 09")
    cantonal_notes = fields.Text(string="Cantonal Notes", help="Box 13")
    official_instructions = fields.Text(string="Official Instructions", help="Box 14")

    # --- Technical Specifications (Boxes 25-35) ---
    body_type = fields.Char(string="Body Type", help="Box 25")
    body_type_code = fields.Char(string="Body type Code", help="Box 25.1")
    approval_type = fields.Char(string="Approval Type", help="Box 24")
    seats_total = fields.Integer(string="Seats (Total)", help="Box 27")
    weight_empty = fields.Integer(string="Empty Weight (kg)", help="Box 30")
    towing_capacity = fields.Integer(string="Towing Capacity (kg)", help="Box 31")
    payload = fields.Integer(string="Payload (kg)", help="Box 32")
    total_weight = fields.Integer(string="Total Weight (kg)", help="Box 33")
    roof_load = fields.Integer(string="Roof Load (kg)", help="Box 35")

    # --- Engine & Emissions (Boxes 37-78) ---
    displacement_cc = fields.Integer(string="Displacement (cm³)", help="Box 37")
    place_date_issue = fields.Char(string="Place date Issue", help="Box 38")
    last_inspection = fields.Char(string="Last Inspection", help="Box 39")
    # power_kw = fields.Integer(string="Power (KW)", help="Box 76")
    power_kw = fields.Char(string="Power (KW)", help="Box 76")
    emission_code = fields.Char(string="Emission Code", help="Box 72")
    power_weight_ratio = fields.Float(string="Power/Weight Ratio (kW/kg)", help="Box 78")


    # ==================== FIELD DEFINITIONS ==================== size=17,
    vin = fields.Char(string="VIN", tracking=True)
    brand = fields.Char(string="Brand", help="Box 21")
    model = fields.Char(string="Model", help="Box 21.1")
    model_code = fields.Char(string="Model Code")
    master_number = fields.Char(string="Master Number (Stammnummer)")
    brand_id = fields.Many2one('vehicle.brand', string='Brand ID', help="Box 21")
    model_id = fields.Many2one('vehicle.model', string='Model ID', domain="[('brand_id', '=', brand_id)]")
    partner_id = fields.Many2one('res.partner', string="Owner Partner ID")
    license_plate = fields.Char(string="License Plate No.", tracking=True)
    certificate_image = fields.Binary("Vehicle Certificate", attachment=True)
    certificate_filename = fields.Char()
    issue_place_id = fields.Many2one('vehicle.issue.place', string="Issue Place")
    issue_place = fields.Char(string="Issue Place")
    issue_date = fields.Date(string="Issue Date")
    year = fields.Char(string="Year")
    engine = fields.Char()
    fuel_type = fields.Char(string="Fuel Type")
    transmission = fields.Char()
    color_id = fields.Many2one('vehicle.color', string="Color ID")
    color = fields.Char(string="Color", help="Box 26")

    vehicle_type = fields.Char(string="Vehicle Type", help="Box 25")
    vehicle_type_code = fields.Char(string="Vehicle Type Code", help="Box 24")
    vehicle_category = fields.Char(string="Vehicle Category", help="Box 19")
    vehicle_category_code = fields.Char(string="Category Code", help="Box 20")
    body_class = fields.Char()
    doors = fields.Char()
    drive_type = fields.Char()
    engine_cylinders = fields.Char()
    engine_displacement = fields.Char()
    manufacturer = fields.Char()
    plant_country = fields.Char()
    plant_city = fields.Char()
    steering_location = fields.Char()
    brake_system = fields.Char()
    series = fields.Char()
    trim = fields.Char()
    name = fields.Char(string='Vehicles Name ', compute='_compute_vehicle_name', store=True)

    type_code = fields.Char(string='Type Code', help="Box 24")
    # first_registration = fields.Date(string="1st Registration")
    first_registration = fields.Char(string="1st Registration")
    your_ref = fields.Many2one('res.partner', string='Your Ref')
    our_ref = fields.Many2one('res.partner', string='Our Ref', domain="[('employee_ids', '!=', False)]")
    page_no = fields.Integer(string='Page No.')
    year_from = fields.Integer(string="Year From")
    year_to = fields.Integer(string="Year To")
    chassis_id = fields.Many2one('vehicle.chassis', string='Chassis Code', domain="[('model_id', '=', model_id)]")
    body_style_id = fields.Many2one('vehicle.body', string='Body Style', domain="[('model_id', '=', model_id)]")
    variant_id = fields.Many2one('vehicle.variant', string='Variant', domain="[('model_id', '=', model_id)]")
    mileage = fields.Integer(string='Mileage')
    last_service_date = fields.Date(string='Last Service Date')
    vehicle_id = fields.Many2one('vehicle.master', string="Vehicle")
    image_front = fields.Image(string="Front View", max_width=1920, max_height=1080)
    image_back = fields.Image(string="Back View", max_width=1920, max_height=1080)
    image_side = fields.Image(string="Side View", max_width=1920, max_height=1080)

    purchase_price = fields.Float(string="Purchase Price")
    sale_price = fields.Float(string="Sale Price")

    total_service_cost = fields.Float(tring="Total Service Cost", compute="_compute_service_cost" )
    profit = fields.Float(string="Profit", compute="_compute_profit")

    rental_ids = fields.One2many('vehicle.rental', 'vehicle_id')

    service_ids = fields.One2many('vehicle.service', 'vehicle_id')

    product_id = fields.Many2one('product.product', string="Product")
    lot_id = fields.Many2one('stock.lot', string="Serial / VIN")
    sale_order_id = fields.Many2one('sale.order')







    def action_scan_certificate_with_gemini(self):
        self.ensure_one()
        if not self.certificate_image:
            raise UserError("Please upload the Swiss certificate first.")

        api_key = self.env['ir.config_parameter'].sudo().get_param('gemini.api.key')
        if not api_key:
            raise UserError("API Key missing in System Parameters.")

        try:
            import requests
            import json
            import base64
            import re
            from datetime import datetime

            # --- 1. PREPARE FILE ---
            file_content = base64.b64decode(self.certificate_image)
            mime_type = "application/pdf" if file_content.startswith(b'%PDF') else "image/jpeg"

            # --- 2. MODEL & URL (March 2026 Stable Standard) ---
            model_id = "models/gemini-2.5-flash"
            url = f"https://generativelanguage.googleapis.com/v1beta/{model_id}:generateContent?key={api_key}"

            # --- 3. REFINED PROMPT ---
            prompt_text = """
            Extract Swiss Fahrzeugausweis (vehicle certificate) data to JSON format.
            - last_name: Box 1
            - first_name: Box 2
            - street: Box 3/5
            - zip: Box 4
            - city: Box 5
            - dob: Box 07 (DD.MM.YYYY)
            - vin: Box 23
            - license_plate: Box 15
            - master_number: Box 18
            - insurance: Box 09
            - instructions: Box 14
            - power: Box 76
            - color: Box 26
            - seats_total: Box 27
            - brand_id: Box 21
            - model_id: Box 21.1
            - owner_ref_uid: Box 6
            - place_of_origin: Box 8
            - vehicle_type_code: Box 24
            - vehicle_type: Box 25
            - vehicle_category: Box 19
            - vehicle_category_code: Box 20
            - body_type: Box 25
            - body_type_code: Box 25.1
            - approval_type: Box 24
            - displacement_cc: Box 37
            - place_date_issue: Box 38
            - last_inspection: Box 39
            - power_kw: Box 76
            """

            # --- 4. THE PAYLOAD ---
            payload = {
                "contents": [{
                    "parts": [
                        {"text": prompt_text},
                        {"inlineData": {
                            "mimeType": mime_type,
                            "data": self.certificate_image.decode('utf-8')
                        }}
                    ]
                }],
                "generationConfig": {
                    "temperature": 0.1,
                }
            }

            response = requests.post(url, json=payload, timeout=30)
            if response.status_code != 200:
                raise UserError(f"API HTTP {response.status_code}: {response.text}")

            result = response.json()
            if 'candidates' not in result:
                raise UserError(f"Gemini API Error: {json.dumps(result)}")

            ai_text = result['candidates'][0]['content']['parts'][0]['text']

            # Extract JSON from markdown if present
            json_match = re.search(r'\{.*\}', ai_text, re.DOTALL)
            data = json.loads(json_match.group() if json_match else ai_text)

            # --- 5. DATE FORMATTER ---
            def format_odoo_date(raw_val):
                if not raw_val: return False
                try:
                    clean_str = re.sub(r'[^0-9.]', '', str(raw_val))
                    return datetime.strptime(clean_str, '%d.%m.%Y').strftime('%Y-%m-%d')
                except:
                    return False

            # --- 6. PREPARE DATA & HANDLE MANDATORY PRODUCT ---
            # 6a. Search for existing Product
            product = self.env['product.product'].search([('name', '=', 'Vehicle')], limit=1)

            # 6b. If not found, create it (prevents Validation Error)
            if not product:
                product = self.env['product.product'].create({
                    'name': 'Vehicle',
                    'type': 'service',
                    'sale_ok': True,
                    'purchase_ok': True,
                })

            # 6c. Map all fields to vals
            vals = {
                'vin': data.get('vin', '').replace(' ', '').upper(),
                'license_plate': data.get('license_plate', '').replace(' ', '').upper(),
                # 'license_plate': data.get('license_plate'),
                'owner_last_name': data.get('last_name'),
                'owner_first_name': data.get('first_name'),
                'street': data.get('street'),
                'zip': data.get('zip'),
                'city': data.get('city'),
                'owner_dob': format_odoo_date(data.get('dob')),
                'master_number': data.get('master_number'),
                'vehicle_type_code': data.get('vehicle_type_code'),
                'vehicle_type': data.get('vehicle_type'),
                'insurance_company': data.get('insurance'),
                'official_instructions': data.get('instructions'),
                'power_kw': data.get('power_kw'),
                'color': data.get('color'),
                'brand': data.get('brand'),
                'model': data.get('model'),
                'owner_ref_uid': data.get('owner_ref_uid'),
                'place_of_origin': data.get('place_of_origin'),
                'vehicle_category': data.get('vehicle_category'),
                'vehicle_category_code': data.get('vehicle_category_code'),
                'body_type': data.get('body_type'),
                'body_type_code': data.get('body_type_code'),
                'seats_total': data.get('seats_total'),
                'approval_type': data.get('approval_type'),
                'displacement_cc': data.get('displacement_cc'),
                'place_date_issue': data.get('place_date_issue'),
                'last_inspection': data.get('last_inspection'),
            }

            # 6d. Ensure product_id is set if current record doesn't have one
            if not self.product_id:
                vals['product_id'] = product.id

            # --- 7. FINAL WRITE ---
            self.write(vals)

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Success',
                    'message': f'Extracted: {data.get("last_name", "Vehicle Data")}',
                    'type': 'success',
                    'next': {'type': 'ir.actions.client', 'tag': 'reload'},
                }
            }

        except Exception as e:
            raise UserError(f"Extraction Error: {str(e)}")




    def action_view_services(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Services',
            'res_model': 'vehicle.service',
            'view_mode': 'tree,form',
            'domain': [('vehicle_id', '=', self.id)],
            'context': {'default_vehicle_id': self.id}
        }

    def action_view_rentals(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Rentals',
            'res_model': 'vehicle.rental',
            'view_mode': 'tree,form',
            'domain': [('vehicle_id', '=', self.id)],
            'context': {'default_vehicle_id': self.id}
        }




    state = fields.Selection([
        ('draft', 'Draft'),
        ('available', 'Available'),
        ('sold', 'Sold'),
        ('rented', 'Rented'),
        ('service', 'Service'),
    ], default='draft', tracking=True)


    @api.depends('service_ids.cost')
    def _compute_service_cost(self):
        for rec in self:
            rec.total_service_cost = sum(rec.service_ids.mapped('cost'))

    @api.depends('sale_price', 'purchase_price', 'total_service_cost')
    def _compute_profit(self):
        for rec in self:
            rec.profit = rec.sale_price - rec.purchase_price - rec.total_service_cost


    @api.model
    def create(self, vals):
        record = super().create(vals)
        if record.vin and record.product_id:
            lot = self.env['stock.lot'].create({
                'name': record.vin,
                'product_id': record.product_id.id,
            })
            record.lot_id = lot.id
        return record


    @api.constrains('state')
    def _check_sold_once(self):
        for rec in self:
            if rec.state == 'sold' and rec.sale_order_id:
                existing = self.search([
                    ('id', '!=', rec.id),
                    ('lot_id', '=', rec.lot_id.id),
                    ('state', '=', 'sold')
                ])
                if existing:
                    raise ValidationError("Vehicle already sold once!")



    # ==================== COMPUTE METHODS ====================

    @api.depends('brand_id', 'model_id', 'chassis_id', 'body_style_id', 'variant_id')
    def _compute_vehicle_name(self):
        for vehicle in self:
            parts = []

            if vehicle.brand_id:
                parts.append(vehicle.brand_id.name)

            if vehicle.model_id:
                parts.append(vehicle.model_id.name)

            if vehicle.chassis_id:
                parts.append(vehicle.chassis_id.name)

            if vehicle.body_style_id:
                parts.append(vehicle.body_style_id.name)

            if vehicle.variant_id:
                parts.append(vehicle.variant_id.name)

            vehicle.name = " ".join(parts) if parts else "New Vehicle"



    # ==================== CONSTRAINTS ====================
    @api.constrains('master_number')
    def _check_master_number_format(self):
        for record in self:
            if record.master_number:
                digits = re.sub(r'\D', '', record.master_number)
                if len(digits) != 9:
                    raise ValidationError(_("The Stammnummer (Master Number) must contain exactly 9 digits."))

    # @api.constrains('vin')
    # def _check_vin(self):
    #     for rec in self:
    #         if rec.vin:
    #             cleaned = re.sub(r'[^A-Z0-9]', '', rec.vin.upper())
    #             if len(cleaned) != 17:
    #                 raise ValidationError(
    #                     _("VIN must be exactly 17 characters. Detected: %s (%s)") % (len(cleaned), cleaned))

    @api.constrains('image_front', 'image_back', 'image_side')
    def _check_image_type(self):
        for record in self:
            for field_name in ['image_front', 'image_back', 'image_side']:
                image_data = record[field_name]
                if image_data:
                    decoded_data = base64.b64decode(image_data)
                    extension = imghdr.what(None, h=decoded_data)
                    valid_types = ['jpeg', 'png']
                    if extension not in valid_types:
                        raise ValidationError(_(
                            "Invalid file format for %s! Only JPG and PNG are allowed."
                        ) % record._fields[field_name].string)

    # ==================== ONCHANGE METHODS ====================
    @api.onchange('master_number')
    def _onchange_master_number(self):
        if self.master_number:
            digits = re.sub(r'\D', '', self.master_number)
            if len(digits) == 9:
                self.master_number = f"{digits[:3]}.{digits[3:6]}.{digits[6:]}"

    @api.onchange('brand_id')
    def _onchange_brand(self):
        self.model_id = False

    @api.onchange('model_id')
    def _onchange_model(self):
        self.chassis_id = False
        self.body_style_id = False
        self.variant_id = False

    # @api.onchange('vin')
    # def _onchange_vin_auto_decode(self):
    #     if self.vin and len(self.vin) == 17:
    #         self.action_decode_vin_chain()

    # ==================== VIN DECODING ====================
    def action_decode_vin_chain(self):
        providers = [self.decode_autoidat, self.decode_dbvin, self.decode_nhtsa]
        for provider in providers:
            try:
                if provider():
                    self._update_brand_model_records()
                    return True
            except Exception:
                continue
        return False

    def decode_nhtsa(self):
        url = f"https://vpic.nhtsa.dot.gov/api/vehicles/decodevin/{self.vin}?format=json"
        try:
            res = requests.get(url, timeout=5).json()
            results = res.get('Results', [])

            def get_v(key):
                for i in results:
                    if i['Variable'] == key: return i['Value']
                return False

            self.brand = get_v('Make')
            self.model = get_v('Model')
            self.year = get_v('Model Year')
            self.fuel_type = get_v('Fuel Type - Primary')
            return True if self.brand else False
        except:
            return False

    def decode_autoidat(self):
        params = self.env['ir.config_parameter'].sudo()
        user = params.get_param('vehicle.autoidat_user')
        key = params.get_param('vehicle.autoidat_key')
        if not user or not key: return False
        try:
            r = requests.post("https://api.auto-i-dat.com/vehicle",
                              json={"vin": self.vin},
                              headers={"Authorization": f"Bearer {key}", "User": user}, timeout=5)
            data = r.json()
            self.brand, self.model = data.get('make'), data.get('model')
            return True if self.brand else False
        except:
            return False

    def decode_dbvin(self):
        try:
            r = requests.get(f"https://db.vin/api/v1/vin/{self.vin}", timeout=5)
            data = r.json()
            self.brand, self.model = data.get("brand"), data.get("model")
            return True if self.brand else False
        except:
            return False

    def _update_brand_model_records(self):
        for rec in self:
            if rec.brand:
                brand = self.env['vehicle.brand'].search([('name', '=ilike', rec.brand)], limit=1)
                if not brand:
                    brand = self.env['vehicle.brand'].create({'name': rec.brand.upper()})
                rec.brand_id = brand
                if rec.model:
                    model = self.env['vehicle.model'].search([
                        ('name', '=ilike', rec.model), ('brand_id', '=', brand.id)
                    ], limit=1)
                    if not model:
                        model = self.env['vehicle.model'].create({'name': rec.model.upper(), 'brand_id': brand.id})
                    rec.model_id = model

    # def action_fetch_vehicle_data(self):
    #     self.ensure_one()
    #     config = self._get_api_config()
    #     if not config['url']:
    #         raise UserError(_("Please configure Vehicle API URL in Settings."))
    #     try:
    #         response = requests.get(f"{config['url']}/decodevinvalues/{self.vin}?format=json", timeout=10)
    #         response.raise_for_status()
    #         data = response.json()
    #         results = data.get('Results', [{}])[0]
    #     except Exception as e:
    #         raise UserError(_("Failed to fetch data: %s") % e)
    #
    #     self.brand = results.get('Make')
    #     self.model = results.get('Model')
    #     self.year = results.get('ModelYear')
    #     self.engine = results.get('EngineModel')
    #     self.engine_cylinders = results.get('EngineCylinders')
    #     self.engine_displacement = results.get('DisplacementL')
    #     self.power_kw = results.get('EngineHP')
    #     self.fuel_type = results.get('FuelTypePrimary')
    #     self.transmission = results.get('TransmissionStyle')
    #     self.body_class = results.get('BodyClass')
    #     self.doors = results.get('Doors')
    #     self.drive_type = results.get('DriveType')
    #     self.vehicle_type = results.get('VehicleType')
    #     self.manufacturer = results.get('Manufacturer')
    #     self.plant_country = results.get('PlantCountry')
    #     self.plant_city = results.get('PlantCity')
    #     self.series = results.get('Series')
    #     self.trim = results.get('Trim')
    #     self.steering_location = results.get('SteeringLocation')
    #     self.brake_system = results.get('BrakeSystemType')
    #     self._update_brand_model_records()

    @api.model
    def _get_api_config(self):
        IrValues = self.env['ir.config_parameter'].sudo()
        return {
            'url': IrValues.get_param('vehicle_master_vin.vehicle_api_url'),
            'user': IrValues.get_param('vehicle_master_vin.vehicle_api_user'),
            'key': IrValues.get_param('vehicle_master_vin.vehicle_api_key'),
        }

    def name_get(self):
        result = []
        for vehicle in self:
            name = vehicle.name or "New Vehicle"

            if vehicle.master_number:
                name += f" - {vehicle.master_number}"

            result.append((vehicle.id, name))
        return result




    def _name_search(self, name='', args=None, operator='ilike', limit=100, order=None):
        args = args or []
        if name:
            args += ['|', '|', '|', '|', '|',
                     ('partner_id.name', operator, name),
                     ('brand_id.name', operator, name),
                     ('model_id.name', operator, name),
                     ('master_number', operator, name),
                     ('license_plate', operator, name),
                     ('vin', operator, name)]
        return self._search(args, limit=limit, order=order)

    _sql_constraints = [
        ('master_number_unique', 'unique(master_number)', 'This Stammnummer already exists in the system!')
    ]

    _sql_constraints = [
        ('unique_lot', 'unique(lot_id)', 'This VIN already exists!'),
    ]

# ==================== OTHER MODEL CLASSES ====================
class VehicleSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    vehicle_api_url = fields.Char(string="Vehicle API URL")
    vehicle_api_user = fields.Char(string="Vehicle API User")
    vehicle_api_key = fields.Char(string="Vehicle API Key")

    def get_values(self):
        res = super().get_values()
        IrValues = self.env['ir.config_parameter'].sudo()
        res.update(
            vehicle_api_url=IrValues.get_param('vehicle_master_vin.vehicle_api_url'),
            vehicle_api_user=IrValues.get_param('vehicle_master_vin.vehicle_api_user'),
            vehicle_api_key=IrValues.get_param('vehicle_master_vin.vehicle_api_key'),
        )
        return res

    def set_values(self):
        super().set_values()
        IrValues = self.env['ir.config_parameter'].sudo()
        IrValues.set_param('vehicle_master_vin.vehicle_api_url', self.vehicle_api_url or '')
        IrValues.set_param('vehicle_master_vin.vehicle_api_user', self.vehicle_api_user or '')
        IrValues.set_param('vehicle_master_vin.vehicle_api_key', self.vehicle_api_key or '')


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    vin_api_provider = fields.Selection([
        ('nhtsa', 'NHTSA (Free VIN Decoder)'),
        ('autoidat', 'AUTO-i-DAT')
    ], string="VIN API Provider", default='nhtsa', config_parameter='vehicle_master_vin.provider')
    autoidat_api_url = fields.Char(string="AUTO-i-DAT API URL", config_parameter='vehicle_master_vin.api_url')
    autoidat_api_key = fields.Char(string="AUTO-i-DAT API Key", config_parameter='vehicle_master_vin.api_key')
    autoidat_api_user = fields.Char(string="AUTO-i-DAT API User", config_parameter='vehicle_master_vin.api_user')
    autoidat_user = fields.Char(string="AUTO-i-DAT API User", config_parameter='vehicle.autoidat_user')
    autoidat_key = fields.Char(string="AUTO-i-DAT API Key", config_parameter='vehicle.autoidat_key')

    def set_values(self):
        super().set_values()
        self.env['ir.config_parameter'].sudo().set_param('vehicle.autoidat_user', self.autoidat_user)
        self.env['ir.config_parameter'].sudo().set_param('vehicle.autoidat_key', self.autoidat_key)

    @api.model
    def get_values(self):
        res = super().get_values()
        params = self.env['ir.config_parameter'].sudo()
        res.update(
            autoidat_user=params.get_param('vehicle.autoidat_user'),
            autoidat_key=params.get_param('vehicle.autoidat_key'),
        )
        return res


class VehicleColor(models.Model):
    _name = 'vehicle.color'
    _description = 'Vehicle Color'
    name = fields.Char(string="Color Name", required=True)
    active = fields.Boolean(default=True)


class ResPartner(models.Model):
    _inherit = 'res.partner'
    vehicle_ids = fields.One2many('vehicle.master', 'partner_id', string='Vehicles')
    date_of_birth = fields.Date(string="Date of Birth")
    insurance_company = fields.Char(string="Insurance Company")
    whatsapp_no = fields.Char(string="WhatsApp No.")


class VehicleBrand(models.Model):
    _name = 'vehicle.brand'
    _description = 'Vehicle Brand'
    name = fields.Char(string="Brand Name", required=True)
    logo = fields.Image(string="Logo", max_width=256, max_height=256)
    model_ids = fields.One2many('vehicle.model', 'brand_id', string="Models")
    active = fields.Boolean(default=True)
    model_count = fields.Integer(string="Model Count", compute="_compute_model_count")

    @api.depends('model_ids')
    def _compute_model_count(self):
        for record in self:
            record.model_count = len(record.model_ids)

    _sql_constraints = [('brand_name_unique', 'unique(name)', 'Brand name must be unique!')]


class VehicleModel(models.Model):
    _name = 'vehicle.model'
    _description = 'Vehicle Model'
    name = fields.Char(string="Model Name", required=True)
    brand_id = fields.Many2one('vehicle.brand', string="Brand", required=True, ondelete='cascade')
    chassis_ids = fields.One2many('vehicle.chassis', 'model_id', string="Chassis Codes")
    body_style_ids = fields.One2many('vehicle.body', 'model_id', string="Body Styles")
    variant_ids = fields.One2many('vehicle.variant', 'model_id', string="Variants")
    _sql_constraints = [('model_brand_unique', 'unique(name, brand_id)', 'Model already exists for this brand!')]


class VehicleChassis(models.Model):
    _name = 'vehicle.chassis'
    _description = 'Chassis Code'
    name = fields.Char(string="Chassis Code", required=True)
    model_id = fields.Many2one('vehicle.model', required=True, ondelete='cascade')
    _sql_constraints = [('chassis_unique', 'unique(name, model_id)', 'Chassis already exists for this model!')]


class VehicleBody(models.Model):
    _name = 'vehicle.body'
    _description = 'Body Style'
    name = fields.Char(string="Body Style", required=True)
    model_id = fields.Many2one('vehicle.model', required=True, ondelete='cascade')
    _sql_constraints = [('body_unique', 'unique(name, model_id)', 'Body style already exists for this model!')]


class VehicleVariant(models.Model):
    _name = 'vehicle.variant'
    _description = 'Vehicle Variant'
    name = fields.Char(required=True)
    model_id = fields.Many2one('vehicle.model', required=True, ondelete='cascade')
    year_from = fields.Integer(string="Year From")
    year_to = fields.Integer(string="Year To")
    _sql_constraints = [('variant_unique', 'unique(name, model_id)', 'Variant already exists for this model!')]


class VehicleIssuePlace(models.Model):
    _name = 'vehicle.issue.place'
    _description = 'Vehicle Issue Place'
    name = fields.Char(string="Place", required=True)


class VehicleService(models.Model):
    _name = 'vehicle.service'


    vehicle_id = fields.Many2one('vehicle.master', string="Vehicle")
    cost = fields.Float(string="Service Cost")
    date = fields.Date()
    description = fields.Text()


    def action_start_service(self):
        self.vehicle_id.state = 'service'

    def action_done(self):
        self.vehicle_id.state = 'available'





class VehicleRental(models.Model):
    _name = 'vehicle.rental'

    vehicle_id = fields.Many2one('vehicle.master', required=True)
    customer_id = fields.Many2one('res.partner')
    start_date = fields.Date()
    end_date = fields.Date()
    rent_amount = fields.Float()

    def action_start(self):
        self.vehicle_id.state = 'rented'

    def action_end(self):
        self.vehicle_id.state = 'available'
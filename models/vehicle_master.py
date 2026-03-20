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

    # --- Owner / Halter (Boxes 1-8) ---
    owner_last_name = fields.Char(string="Last Name", help="Box 1")
    owner_first_name = fields.Char(string="First Name", help="Box 2")
    owner_street = fields.Char(string="Street Address", help="Box 3/5")
    owner_zip = fields.Char(string="Postal Code", help="Box 4")
    owner_city = fields.Char(string="City / Town", help="Box 5")
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
    power_kw = fields.Integer(string="Power (KW)", help="Box 76")
    emission_code = fields.Char(string="Emission Code", help="Box 72")
    power_weight_ratio = fields.Float(string="Power/Weight Ratio (kW/kg)", help="Box 78")


    # ==================== FIELD DEFINITIONS ====================
    vin = fields.Char(string="VIN", size=17, tracking=True)
    brand = fields.Char(string="Brand", help="Box 21")
    model = fields.Char(string="Model", help="Box 21.1")
    master_number = fields.Char(string="Master Number (Stammnummer)")
    brand_id = fields.Many2one('vehicle.brand', string='Brand')
    model_id = fields.Many2one('vehicle.model', string='Model', domain="[('brand_id', '=', brand_id)]")
    partner_id = fields.Many2one('res.partner', string="Owner")
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
    color_id = fields.Many2one('vehicle.color', string="Color")
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
    name = fields.Char(string='Vehicle Name', compute='_compute_vehicle_name', store=True)
    type_code = fields.Char(string='Type Code', help="Box 24")
    first_registration = fields.Date(string="1st Registration")
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



    @api.depends('brand', 'model')
    def _compute_vehicle_name(self):
        for rec in self:
            rec.name = f"{rec.brand or ''} {rec.model or ''}".strip() or "New Vehicle"

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
            - brand: Box 21
            - model: Box 21.1
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
                'owner_street': data.get('street'),
                'owner_zip': data.get('zip'),
                'owner_city': data.get('city'),
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
    @api.depends('brand_id', 'model_id', 'license_plate')
    def _compute_vehicle_name(self):
        for vehicle in self:
            parts = []
            if vehicle.brand_id:
                parts.append(vehicle.brand_id.name)
            if vehicle.model_id:
                parts.append(vehicle.model_id.name)
            vehicle.name = " ".join(parts) if parts else vehicle.license_plate or "New Vehicle"

    @api.depends('brand_id', 'model_id', 'chassis_id', 'body_style_id', 'variant_id')
    def _compute_vehicle_name_full(self):
        for vehicle in self:
            parts = []
            if vehicle.brand_id: parts.append(vehicle.brand_id.name)
            if vehicle.model_id: parts.append(vehicle.model_id.name)
            if vehicle.chassis_id: parts.append(vehicle.chassis_id.name)
            if vehicle.body_style_id: parts.append(vehicle.body_style_id.name)
            if vehicle.variant_id: parts.append(vehicle.variant_id.name)
            vehicle.name = " ".join(parts) if parts else vehicle.license_plate

    # ==================== CONSTRAINTS ====================
    @api.constrains('master_number')
    def _check_master_number_format(self):
        for record in self:
            if record.master_number:
                digits = re.sub(r'\D', '', record.master_number)
                if len(digits) != 9:
                    raise ValidationError(_("The Stammnummer (Master Number) must contain exactly 9 digits."))

    @api.constrains('vin')
    def _check_vin(self):
        for rec in self:
            if rec.vin:
                cleaned = re.sub(r'[^A-Z0-9]', '', rec.vin.upper())
                if len(cleaned) != 17:
                    raise ValidationError(
                        _("VIN must be exactly 17 characters. Detected: %s (%s)") % (len(cleaned), cleaned))

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

    @api.onchange('vin')
    def _onchange_vin_auto_decode(self):
        if self.vin and len(self.vin) == 17:
            self.action_decode_vin_chain()

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

    def action_fetch_vehicle_data(self):
        self.ensure_one()
        config = self._get_api_config()
        if not config['url']:
            raise UserError(_("Please configure Vehicle API URL in Settings."))
        try:
            response = requests.get(f"{config['url']}/decodevinvalues/{self.vin}?format=json", timeout=10)
            response.raise_for_status()
            data = response.json()
            results = data.get('Results', [{}])[0]
        except Exception as e:
            raise UserError(_("Failed to fetch data: %s") % e)

        self.brand = results.get('Make')
        self.model = results.get('Model')
        self.year = results.get('ModelYear')
        self.engine = results.get('EngineModel')
        self.engine_cylinders = results.get('EngineCylinders')
        self.engine_displacement = results.get('DisplacementL')
        self.power_kw = results.get('EngineHP')
        self.fuel_type = results.get('FuelTypePrimary')
        self.transmission = results.get('TransmissionStyle')
        self.body_class = results.get('BodyClass')
        self.doors = results.get('Doors')
        self.drive_type = results.get('DriveType')
        self.vehicle_type = results.get('VehicleType')
        self.manufacturer = results.get('Manufacturer')
        self.plant_country = results.get('PlantCountry')
        self.plant_city = results.get('PlantCity')
        self.series = results.get('Series')
        self.trim = results.get('Trim')
        self.steering_location = results.get('SteeringLocation')
        self.brake_system = results.get('BrakeSystemType')
        self._update_brand_model_records()

    @api.model
    def _get_api_config(self):
        IrValues = self.env['ir.config_parameter'].sudo()
        return {
            'url': IrValues.get_param('vehicle_master_vin.vehicle_api_url'),
            'user': IrValues.get_param('vehicle_master_vin.vehicle_api_user'),
            'key': IrValues.get_param('vehicle_master_vin.vehicle_api_key'),
        }

    # ==================== OCR SCANNING METHODS ====================

    # def _extract_swiss_certificate_data_stable(self, image_data):
    #     """Stable multi-pass extraction with validation"""
    #     extracted_data = {
    #         'license_plate': None,
    #         'vin': None,
    #         'brand': None,
    #         'model': None,
    #         'first_registration': None,
    #         'year': None,
    #         'master_number': None,
    #     }
    #
    #     try:
    #         nparr = np.frombuffer(base64.b64decode(image_data), np.uint8)
    #         img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    #         height, width = img.shape[:2]
    #         _logger.info(f"Image dimensions: {width}x{height}")
    #
    #         # PASS 1: ZONE-BASED EXTRACTION
    #         _logger.info("PASS 1: Zone-based extraction")
    #         zones = {
    #             'license_plate': (0.05, 0.18, 0.65, 0.98),
    #             'vin': (0.35, 0.45, 0.20, 0.85),
    #             'brand_model': (0.25, 0.35, 0.20, 0.85),
    #             'date': (0.65, 0.75, 0.10, 0.40),
    #             'master': (0.15, 0.25, 0.50, 0.85),
    #         }
    #
    #         zone_results = {}
    #         for field, (y1_pct, y2_pct, x1_pct, x2_pct) in zones.items():
    #             y1, y2 = int(height * y1_pct), int(height * y2_pct)
    #             x1, x2 = int(width * x1_pct), int(width * x2_pct)
    #             zone = img[y1:y2, x1:x2]
    #             if zone.size > 0:
    #                 text = self._extract_zone_text(zone)
    #                 zone_results[field] = text
    #                 _logger.info(f"Zone {field}: {text[:100]}...")
    #
    #         # Extract fields from zones
    #         if zone_results.get('license_plate'):
    #             plate = self._extract_plate_from_text(zone_results['license_plate'])
    #             if plate:
    #                 extracted_data['license_plate'] = plate
    #
    #         if zone_results.get('vin'):
    #             vin = self._extract_vin_from_text(zone_results['vin'])
    #             if vin:
    #                 extracted_data['vin'] = vin
    #
    #         if zone_results.get('brand_model'):
    #             brand, model = self._extract_brand_model_from_text(zone_results['brand_model'])
    #             if brand:
    #                 extracted_data['brand'] = brand
    #             if model:
    #                 extracted_data['model'] = model
    #
    #         if zone_results.get('date'):
    #             date = self._extract_date_from_text(zone_results['date'])
    #             if date:
    #                 extracted_data['first_registration'] = date
    #                 extracted_data['year'] = date[:4] if date else None
    #
    #         if zone_results.get('master'):
    #             master = self._extract_master_from_text(zone_results['master'])
    #             if master:
    #                 extracted_data['master_number'] = master
    #
    #         # PASS 2: FULL IMAGE EXTRACTION (fallback)
    #         _logger.info("PASS 2: Full image extraction")
    #         full_texts = self._extract_full_image_text(img)
    #
    #         # Fill missing fields
    #         if not extracted_data['license_plate']:
    #             for text in full_texts:
    #                 plate = self._extract_plate_from_text(text)
    #                 if plate:
    #                     extracted_data['license_plate'] = plate
    #                     break
    #
    #         if not extracted_data['vin']:
    #             for text in full_texts:
    #                 vin = self._extract_vin_from_text(text)
    #                 if vin:
    #                     extracted_data['vin'] = vin
    #                     break
    #
    #         if not extracted_data['brand'] or not extracted_data['model']:
    #             for text in full_texts:
    #                 brand, model = self._extract_brand_model_from_text(text)
    #                 if brand and not extracted_data['brand']:
    #                     extracted_data['brand'] = brand
    #                 if model and not extracted_data['model']:
    #                     extracted_data['model'] = model
    #                 if extracted_data['brand'] and extracted_data['model']:
    #                     break
    #
    #         # PASS 3: VALIDATION
    #         _logger.info("PASS 3: Validation")
    #         if extracted_data['vin'] and len(extracted_data['vin']) != 17:
    #             cleaned = re.sub(r'[^A-Z0-9]', '', extracted_data['vin'].upper())
    #             if len(cleaned) >= 17:
    #                 extracted_data['vin'] = cleaned[:17]
    #             else:
    #                 extracted_data['vin'] = None
    #
    #         if extracted_data['license_plate']:
    #             plate = extracted_data['license_plate'].upper()
    #             match = re.search(r'([A-Z]{2})\D*(\d{6})', plate)
    #             if match:
    #                 extracted_data['license_plate'] = match.group(1) + match.group(2)
    #
    #         return extracted_data
    #
    #     except Exception as e:
    #         _logger.error(f"Stable extraction error: {str(e)}", exc_info=True)
    #         return extracted_data
    #
    # def _extract_zone_text(self, zone_img):
    #     """Extract text from a zone with multiple preprocessing"""
    #     try:
    #         gray = cv2.cvtColor(zone_img, cv2.COLOR_BGR2GRAY)
    #         texts = []
    #         for scale in [2, 3, 4]:
    #             resized = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    #             _, thresh = cv2.threshold(resized, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    #             text = pytesseract.image_to_string(Image.fromarray(thresh), config='--psm 6')
    #             if text.strip():
    #                 texts.append(text.strip())
    #         if texts:
    #             return max(texts, key=len)
    #         return ""
    #     except Exception as e:
    #         _logger.error(f"Zone extraction error: {str(e)}")
    #         return ""
    #
    # def _extract_full_image_text(self, img):
    #     """Extract text from full image using multiple methods"""
    #     texts = []
    #     gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    #
    #     gray1 = cv2.resize(gray, None, fx=2, fy=2)
    #     _, thresh1 = cv2.threshold(gray1, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    #     texts.append(pytesseract.image_to_string(Image.fromarray(thresh1)))
    #
    #     gray2 = cv2.resize(gray, None, fx=2, fy=2)
    #     thresh2 = cv2.adaptiveThreshold(gray2, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
    #     texts.append(pytesseract.image_to_string(Image.fromarray(thresh2)))
    #
    #     gray3 = cv2.resize(gray, None, fx=2, fy=2)
    #     texts.append(pytesseract.image_to_string(Image.fromarray(gray3)))
    #
    #     return texts
    #
    # def _extract_plate_from_text(self, text):
    #     """Extract Swiss license plate from text"""
    #     text_upper = text.upper()
    #     patterns = [
    #         r'([A-Z]{2})[\s\-]?(\d{6})',
    #         r'([A-Z]{2})(\d{6})',
    #         r'2H[\s\-]?(\d{6})',
    #         r'([A-Z]{1})[\s\-]?(\d{6})',
    #     ]
    #     for pattern in patterns:
    #         match = re.search(pattern, text_upper)
    #         if match:
    #             if len(match.groups()) == 2:
    #                 letters = match.group(1)
    #                 numbers = match.group(2)
    #                 if letters == '2H':
    #                     letters = 'ZH'
    #                 if len(numbers) > 6:
    #                     numbers = numbers[:6]
    #                 elif len(numbers) < 6:
    #                     numbers = numbers.zfill(6)
    #                 return f"{letters}{numbers}"
    #     return None
    #
    # def _extract_vin_from_text(self, text):
    #     """Extract VIN from text"""
    #     text_upper = text.upper()
    #     mercedes_pattern = r'WDD\s*\d{3}\s*\d{3}\s*[A-Z0-9]{3}\s*\d{3}\s*\d{2}'
    #     match = re.search(mercedes_pattern, text_upper)
    #     if match:
    #         return re.sub(r'\s+', '', match.group(0))
    #     vin_pattern = r'[A-HJ-NPR-Z0-9]{17}'
    #     match = re.search(vin_pattern, text_upper)
    #     if match:
    #         return match.group(0)
    #     wdd_match = re.search(r'WDD[A-Z0-9]{14,}', text_upper)
    #     if wdd_match:
    #         vin = wdd_match.group(0)[:17]
    #         if len(vin) == 17:
    #             return vin
    #     return None
    #
    # def _extract_brand_model_from_text(self, text):
    #     """Extract brand and model from text"""
    #     text_upper = text.upper()
    #     brand = None
    #     model = None
    #
    #     if 'MERCEDES' in text_upper or 'BENZ' in text_upper:
    #         brand = 'MERCEDES-BENZ'
    #         model_patterns = [r'C\s*250', r'C250', r'E\s*220', r'E220']
    #         for pattern in model_patterns:
    #             match = re.search(pattern, text, re.IGNORECASE)
    #             if match:
    #                 model = match.group(0).replace(' ', '')
    #                 break
    #     elif 'KIA' in text_upper:
    #         brand = 'KIA'
    #         if 'RIO' in text_upper:
    #             model = 'RIO'
    #
    #     return brand, model
    #
    # def _extract_date_from_text(self, text):
    #     """Extract date from text"""
    #     date_patterns = [
    #         r'(\d{2})[./](\d{2})[./](\d{4})',
    #         r'(\d{4})[./-](\d{2})[./-](\d{2})',
    #     ]
    #     for pattern in date_patterns:
    #         match = re.search(pattern, text)
    #         if match:
    #             if pattern == r'(\d{2})[./](\d{2})[./](\d{4})':
    #                 day, month, year = match.groups()
    #                 return f"{year}-{month}-{day}"
    #             else:
    #                 year, month, day = match.groups()
    #                 return f"{year}-{month}-{day}"
    #     return None
    #
    # def _extract_master_from_text(self, text):
    #     """Extract master number from text"""
    #     patterns = [
    #         r'(\d{3})[.\s]?(\d{3})[.\s]?(\d{3})',
    #         r'(\d{9})',
    #     ]
    #     for pattern in patterns:
    #         match = re.search(pattern, text)
    #         if match:
    #             if pattern == r'(\d{9})':
    #                 digits = match.group(1)
    #                 return f"{digits[:3]}.{digits[3:6]}.{digits[6:]}"
    #             else:
    #                 return f"{match.group(1)}.{match.group(2)}.{match.group(3)}"
    #     return None
    #
    # def _send_notification(self, message, msg_type='info'):
    #     """Send notification to user"""
    #     return {
    #         'type': 'ir.actions.client',
    #         'tag': 'display_notification',
    #         'params': {
    #             'title': 'Vehicle Scan',
    #             'message': message,
    #             'sticky': False,
    #             'type': msg_type,
    #         }
    #     }
    #
    # def action_scan_certificate(self):
    #     self.ensure_one()
    #
    #     if not self.certificate_image:
    #         raise UserError("Please upload an image first")
    #
    #     try:
    #         self._send_notification("Starting scan...", "info")
    #
    #         # Detect format
    #         format_type = self._detect_certificate_format(self.certificate_image)
    #         _logger.info(f"Detected certificate format: {format_type}")
    #
    #         # Extract data
    #         if format_type == 'single_page':
    #             extracted_data = self._extract_single_page_certificate(self.certificate_image)
    #         else:
    #             extracted_data = self._extract_two_page_certificate(self.certificate_image)
    #
    #         # Prepare values
    #         values_to_write = self._prepare_values_to_write(extracted_data)
    #
    #         # Write data
    #         if values_to_write:
    #             self.write(values_to_write)
    #
    #         # ==============================
    #         # LOT (VIN) CREATION - FIXED
    #         # ==============================
    #         if self.vin and self.product_id:
    #
    #             # Check existing lot first
    #             lot = self.env['stock.lot'].search([
    #                 ('name', '=', self.vin),
    #                 ('product_id', '=', self.product_id.id)
    #             ], limit=1)
    #
    #             if not lot:
    #                 lot = self.env['stock.lot'].create({
    #                     'name': self.vin,
    #                     'product_id': self.product_id.id,
    #                 })
    #
    #             self.lot_id = lot.id
    #
    #         # ==============================
    #         # Notification
    #         # ==============================
    #         if values_to_write:
    #             message = self._format_success_message(extracted_data)
    #             self._send_notification(message, "success")
    #         else:
    #             self._send_notification("No data could be extracted", "warning")
    #
    #         return {'type': 'ir.actions.client', 'tag': 'reload'}
    #
    #     except Exception as e:
    #         _logger.error(f"Scan error: {str(e)}", exc_info=True)
    #         self._send_notification(f"Error: {str(e)}", "danger")
    #         raise UserError(f"Error: {str(e)}")
    #
    #
    # def _detect_certificate_format(self, image_data):
    #     """Detect whether this is a single-page or two-page Swiss certificate"""
    #     try:
    #         nparr = np.frombuffer(base64.b64decode(image_data), np.uint8)
    #         img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    #
    #         # Convert to grayscale
    #         gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    #
    #         # Extract text from top portion to look for indicators
    #         top_section = gray[0:int(img.shape[0] * 0.2), 0:img.shape[1]]
    #         top_text = pytesseract.image_to_string(Image.fromarray(top_section)).upper()
    #
    #         # Check for indicators of two-page format
    #         if 'PASSAGIER' in top_text or 'NAME' in top_text or 'VORN' in top_text:
    #             _logger.info("Detected two-page format (has owner info)")
    #             return 'two_page'
    #         elif 'SCHILD' in top_text or 'PLAQUE' in top_text or 'A 15' in top_text:
    #             _logger.info("Detected single-page format (technical data only)")
    #             return 'single_page'
    #         else:
    #             # Look for technical fields that indicate single-page
    #             full_text = pytesseract.image_to_string(Image.fromarray(gray)).upper()
    #             if 'FAHRGESTELL-NR' in full_text or 'CHASSIS' in full_text:
    #                 return 'single_page'
    #             else:
    #                 return 'unknown'
    #
    #     except Exception as e:
    #         _logger.error(f"Format detection error: {str(e)}")
    #         return 'unknown'
    #
    # def _extract_single_page_certificate(self, image_data):
    #     """Extract data from single-page Swiss certificate (like the KIA one)"""
    #     extracted_data = {
    #         'license_plate': None,
    #         'vin': None,
    #         'brand': None,
    #         'model': None,
    #         'first_registration': None,
    #         'year': None,
    #         'master_number': None,
    #         'type_code': None,
    #         'power_kw': None,
    #         'color': None,
    #     }
    #
    #     try:
    #         nparr = np.frombuffer(base64.b64decode(image_data), np.uint8)
    #         img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    #
    #         # Enhanced preprocessing for single-page format
    #         gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    #         gray = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    #         _, gray = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    #
    #         # Extract all text
    #         full_text = pytesseract.image_to_string(Image.fromarray(gray))
    #         full_text_upper = full_text.upper()
    #
    #         _logger.info("=" * 60)
    #         _logger.info("SINGLE-PAGE EXTRACTED TEXT:")
    #         _logger.info(full_text)
    #         _logger.info("=" * 60)
    #
    #         # ==================== LICENSE PLATE ====================
    #         # Look for FR 260230 format
    #         plate_patterns = [
    #             r'FR\s*(\d{6})',  # FR 260230
    #             r'([A-Z]{2})\s*(\d{5,6})',  # Generic canton + numbers
    #             r'[A-Z]{1,2}[\s-]?\d{5,6}',
    #         ]
    #
    #         for pattern in plate_patterns:
    #             match = re.search(pattern, full_text_upper)
    #             if match:
    #                 if len(match.groups()) == 2:
    #                     extracted_data['license_plate'] = match.group(1) + match.group(2)
    #                 else:
    #                     plate = match.group(0).replace(' ', '').replace('-', '')
    #                     extracted_data['license_plate'] = plate
    #                 _logger.info(f"Found plate: {extracted_data['license_plate']}")
    #                 break
    #
    #         # ==================== VIN ====================
    #         # Look for KIA VIN: KNA DC5 17A N66 952 81
    #         vin_patterns = [
    #             r'KNA\s*DC5\s*17A\s*N66\s*952\s*81',
    #             r'KNADC5\s*17A\s*N66\s*952\s*81',
    #             r'KNA[A-Z0-9]{14,}',
    #             r'[A-HJ-NPR-Z0-9]{17}',
    #         ]
    #
    #         for pattern in vin_patterns:
    #             match = re.search(pattern, full_text_upper)
    #             if match:
    #                 vin = re.sub(r'\s+', '', match.group(0))
    #                 if len(vin) >= 17:
    #                     extracted_data['vin'] = vin[:17]
    #                     _logger.info(f"Found VIN: {extracted_data['vin']}")
    #                     break
    #
    #         # ==================== BRAND AND MODEL ====================
    #         # Look for KIA Rio
    #         if 'KIA' in full_text_upper:
    #             extracted_data['brand'] = 'KIA'
    #             if 'RIO' in full_text_upper:
    #                 model_match = re.search(r'RIO\s*1\.0\s*T-GDI', full_text, re.IGNORECASE)
    #                 if model_match:
    #                     extracted_data['model'] = model_match.group(0)
    #                 else:
    #                     extracted_data['model'] = 'Rio'
    #
    #         # ==================== MASTER NUMBER ====================
    #         master_patterns = [
    #             r'(\d{3})[.\s]?(\d{3})[.\s]?(\d{3})',  # 685.581.486
    #             r'(\d{9})',
    #         ]
    #
    #         for pattern in master_patterns:
    #             match = re.search(pattern, full_text)
    #             if match:
    #                 if pattern == r'(\d{9})':
    #                     digits = match.group(1)
    #                     extracted_data['master_number'] = f"{digits[:3]}.{digits[3:6]}.{digits[6:]}"
    #                 else:
    #                     extracted_data['master_number'] = f"{match.group(1)}.{match.group(2)}.{match.group(3)}"
    #                 _logger.info(f"Found master number: {extracted_data['master_number']}")
    #                 break
    #
    #         # ==================== FIRST REGISTRATION ====================
    #         date_match = re.search(r'(\d{2})[./](\d{2})[./](\d{4})', full_text)
    #         if date_match:
    #             day, month, year = date_match.groups()
    #             extracted_data['first_registration'] = f"{year}-{month}-{day}"
    #             extracted_data['year'] = year
    #             _logger.info(f"Found first registration: {extracted_data['first_registration']}")
    #
    #         # ==================== TYPE CODE ====================
    #         type_match = re.search(r'KIA\s*7\s*13', full_text_upper)
    #         if type_match:
    #             extracted_data['type_code'] = type_match.group(0)
    #
    #         # ==================== POWER ====================
    #         power_match = re.search(r'(\d{2,3}\.\d)\s*kW', full_text, re.IGNORECASE)
    #         if power_match:
    #             extracted_data['power_kw'] = power_match.group(1)
    #
    #         # ==================== COLOR ====================
    #         if 'BLEU' in full_text_upper:
    #             extracted_data['color'] = 'Blue'
    #
    #         return extracted_data
    #
    #     except Exception as e:
    #         _logger.error(f"Single-page extraction error: {str(e)}", exc_info=True)
    #         return extracted_data
    #
    # def _extract_two_page_certificate(self, image_data):
    #     """Extract data from two-page Swiss certificate (like the Mercedes one)"""
    #     extracted_data = {
    #         'license_plate': None,
    #         'vin': None,
    #         'brand': None,
    #         'model': None,
    #         'first_registration': None,
    #         'year': None,
    #         'master_number': None,
    #         'owner_name': None,
    #         'owner_address': None,
    #     }
    #
    #     try:
    #         nparr = np.frombuffer(base64.b64decode(image_data), np.uint8)
    #         img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    #
    #         # Enhanced preprocessing
    #         gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    #         gray = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    #         _, gray = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    #
    #         # Extract all text
    #         full_text = pytesseract.image_to_string(Image.fromarray(gray))
    #         full_text_upper = full_text.upper()
    #
    #         _logger.info("=" * 60)
    #         _logger.info("TWO-PAGE EXTRACTED TEXT:")
    #         _logger.info(full_text)
    #         _logger.info("=" * 60)
    #
    #         # ==================== LICENSE PLATE ====================
    #         plate_match = re.search(r'ZH\s*(\d{6})', full_text_upper)
    #         if plate_match:
    #             extracted_data['license_plate'] = 'ZH' + plate_match.group(1)
    #             _logger.info(f"Found plate: {extracted_data['license_plate']}")
    #
    #         # ==================== VIN ====================
    #         vin_patterns = [
    #             r'WDD\s*205\s*209\s*1F4\s*028\s*97',
    #             r'WDD2052091F402897',
    #             r'WDD\s*\d{3}\s*\d{3}\s*[A-Z0-9]{3}\s*\d{3}\s*\d{2}',
    #         ]
    #
    #         for pattern in vin_patterns:
    #             match = re.search(pattern, full_text_upper)
    #             if match:
    #                 vin = re.sub(r'\s+', '', match.group(0))
    #                 extracted_data['vin'] = vin
    #                 _logger.info(f"Found VIN: {extracted_data['vin']}")
    #                 break
    #
    #         # ==================== BRAND AND MODEL ====================
    #         if 'MERCEDES' in full_text_upper:
    #             extracted_data['brand'] = 'MERCEDES-BENZ'
    #             model_match = re.search(r'C\s*250\s*d', full_text, re.IGNORECASE)
    #             if model_match:
    #                 extracted_data['model'] = model_match.group(0).replace(' ', '')
    #
    #         # ==================== MASTER NUMBER ====================
    #         master_match = re.search(r'(\d{3})[.\s]?(\d{3})[.\s]?(\d{3})', full_text)
    #         if master_match:
    #             extracted_data[
    #                 'master_number'] = f"{master_match.group(1)}.{master_match.group(2)}.{master_match.group(3)}"
    #
    #         # ==================== OWNER INFO ====================
    #         owner_match = re.search(r'Vidovic\s+Dragana', full_text, re.IGNORECASE)
    #         if owner_match:
    #             extracted_data['owner_name'] = 'Vidovic Dragana'
    #
    #         return extracted_data
    #
    #     except Exception as e:
    #         _logger.error(f"Two-page extraction error: {str(e)}", exc_info=True)
    #         return extracted_data
    #
    # def _prepare_values_to_write(self, extracted_data):
    #     """Prepare values to write to database"""
    #     values = {}
    #
    #     if extracted_data.get('license_plate'):
    #         values['license_plate'] = extracted_data['license_plate']
    #
    #     if extracted_data.get('vin'):
    #         values['vin'] = extracted_data['vin']
    #
    #     if extracted_data.get('year'):
    #         values['year'] = extracted_data['year']
    #
    #     if extracted_data.get('first_registration'):
    #         values['first_registration'] = extracted_data['first_registration']
    #
    #     if extracted_data.get('master_number'):
    #         values['master_number'] = extracted_data['master_number']
    #
    #     if extracted_data.get('type_code'):
    #         values['type_code'] = extracted_data['type_code']
    #
    #     if extracted_data.get('power_kw'):
    #         values['power_kw'] = extracted_data['power_kw']
    #
    #     # Handle brand
    #     if extracted_data.get('brand'):
    #         values['brand'] = extracted_data['brand']
    #         brand = self.env['vehicle.brand'].search([('name', 'ilike', extracted_data['brand'])], limit=1)
    #         if not brand:
    #             brand = self.env['vehicle.brand'].create({'name': extracted_data['brand'].upper()})
    #         self.brand_id = brand
    #
    #     # Handle model
    #     if extracted_data.get('model') and self.brand_id:
    #         values['model'] = extracted_data['model']
    #         model = self.env['vehicle.model'].search([
    #             ('name', 'ilike', extracted_data['model']),
    #             ('brand_id', '=', self.brand_id.id)
    #         ], limit=1)
    #         if not model:
    #             model = self.env['vehicle.model'].create({
    #                 'name': extracted_data['model'].upper(),
    #                 'brand_id': self.brand_id.id
    #             })
    #         self.model_id = model
    #
    #     # Handle color
    #     if extracted_data.get('color'):
    #         color = self.env['vehicle.color'].search([('name', 'ilike', extracted_data['color'])], limit=1)
    #         if color:
    #             self.color_id = color
    #
    #     return values
    #
    # def _format_success_message(self, extracted_data):
    #     """Format success message"""
    #     message = f"✅ Plate: {extracted_data.get('license_plate', 'Not found')}\n"
    #     message += f"✅ VIN: {extracted_data.get('vin', 'Not found')}\n"
    #     message += f"✅ Brand: {extracted_data.get('brand', 'Not found')} {extracted_data.get('model', '')}"
    #     return message
    #




    # ==================== NAME SEARCH ====================

    def name_get(self):
        result = []
        for vehicle in self:
            name = f"[{vehicle.license_plate}] {vehicle.brand_id.name or ''} {vehicle.model_id.name or ''}"
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
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import base64
import imghdr
import re
import requests


class VehicleMaster(models.Model):
    _name = 'vehicle.master'
    _description = 'Vehicle'


    issue_place = fields.Char(string="Issue Place")
    issue_date = fields.Date(string="Issue Date")
    # name = fields.Char(string="Display Name")
    vin = fields.Char(string="VIN", required=True)
    brand = fields.Char()
    model = fields.Char()
    year = fields.Char()
    engine = fields.Char()
    fuel_type = fields.Char()
    power_kw = fields.Char()
    transmission = fields.Char()
    partner_id = fields.Many2one('res.partner', string="Owner")
    # license_plate = fields.Char()
    color_id = fields.Many2one('vehicle.color', string="Color")
    # Add other fields you need

    vehicle_type = fields.Char()
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

    def action_fetch_vehicle_data(self):
        self.ensure_one()
        config = self._get_api_config()

        if not config['url']:
            raise UserError(_("Please configure Vehicle API URL in Settings."))

        vin = self.vin
        api_url = f"{config['url']}/decodevinvalues/{vin}?format=json"

        try:
            response = requests.get(api_url, timeout=10)
            response.raise_for_status()
            data = response.json()
            results = data.get('Results', [{}])[0]
        except Exception as e:
            raise UserError(_("Failed to fetch data: %s") % e)

        # Basic vehicle info
        self.brand = results.get('Make')
        self.model = results.get('Model')
        self.year = results.get('ModelYear')

        # Engine information
        self.engine = results.get('EngineModel')
        self.engine_cylinders = results.get('EngineCylinders')
        self.engine_displacement = results.get('DisplacementL')
        self.power_kw = results.get('EngineHP')

        # Fuel & transmission
        self.fuel_type = results.get('FuelTypePrimary')
        self.transmission = results.get('TransmissionStyle')

        # Vehicle structure
        self.body_class = results.get('BodyClass')
        self.doors = results.get('Doors')
        self.drive_type = results.get('DriveType')
        self.vehicle_type = results.get('VehicleType')

        # Manufacturer information
        self.manufacturer = results.get('Manufacturer')
        self.plant_country = results.get('PlantCountry')
        self.plant_city = results.get('PlantCity')

        # Additional vehicle details
        self.series = results.get('Series')
        self.trim = results.get('Trim')

        # Safety / configuration
        self.steering_location = results.get('SteeringLocation')
        self.brake_system = results.get('BrakeSystemType')

        # ✅ Update Many2one brand_id and model_id automatically
        self._update_brand_model_records()


    @api.model
    def _get_api_config(self):
        IrValues = self.env['ir.config_parameter'].sudo()
        return {
            'url': IrValues.get_param('vehicle_master_vin.vehicle_api_url'),
            'user': IrValues.get_param('vehicle_master_vin.vehicle_api_user'),
            'key': IrValues.get_param('vehicle_master_vin.vehicle_api_key'),
        }

    def _update_brand_model_records(self):
        for rec in self:

            # Handle Brand
            if rec.brand:
                brand = self.env['vehicle.brand'].search(
                    [('name', '=', rec.brand)],
                    limit=1
                )

                if not brand:
                    brand = self.env['vehicle.brand'].create({
                        'name': rec.brand
                    })

                rec.brand_id = brand.id

            # Handle Model
            if rec.model and rec.brand_id:
                model = self.env['vehicle.model'].search(
                    [
                        ('name', '=', rec.model),
                        ('brand_id', '=', rec.brand_id.id)
                    ],
                    limit=1
                )

                if not model:
                    model = self.env['vehicle.model'].create({
                        'name': rec.model,
                        'brand_id': rec.brand_id.id
                    })

                rec.model_id = model.id


    # Owner
    # partner_id = fields.Many2one('res.partner', string='Owner', required=True)

    your_ref = fields.Many2one('res.partner', string='Your Ref')
    # our_ref = fields.Many2one('res.partner', string='Our Ref')

    our_ref = fields.Many2one('res.partner', string='Our Ref', domain="[('employee_ids', '!=', False)]")
    page_no = fields.Integer(string='Page No.')


    # year = fields.Selection([(str(y), str(y)) for y in range(1980, 2031)], string='Year')
    year_from = fields.Integer(string="Year From")
    year_to = fields.Integer(string="Year To")

    # license_plate = fields.Char(string='License Plate', required=True)
    # vin = fields.Char(string='VIN/Chassis Number')
    # color_id = fields.Many2one('vehicle.color', string='Color')

    brand_id = fields.Many2one('vehicle.brand', string='Brand')
    model_id = fields.Many2one('vehicle.model', string='Model/Series', domain="[('brand_id', '=', brand_id)]")
    chassis_id = fields.Many2one('vehicle.chassis', string='Chassis Code', domain="[('model_id', '=', model_id)]")
    body_style_id = fields.Many2one('vehicle.body', string='Body Style', domain="[('model_id', '=', model_id)]")  # Linked to Model for flexibility
    variant_id = fields.Many2one('vehicle.variant', string='Variant',  domain="[('model_id', '=', model_id)]")  # Linked to Model for flexibility

    name = fields.Char(string='Vehicle Name', compute='_compute_vehicle_name', store=True)

    plate_scan_temp = fields.Binary(string="Capture Plate")

    @api.depends('brand_id', 'model_id', 'chassis_id', 'body_style_id', 'variant_id')
    def _compute_vehicle_name(self):
        for vehicle in self:
            parts = []
            if vehicle.brand_id: parts.append(vehicle.brand_id.name)
            if vehicle.model_id: parts.append(vehicle.model_id.name)
            if vehicle.chassis_id: parts.append(vehicle.chassis_id.name)
            if vehicle.body_style_id: parts.append(vehicle.body_style_id.name)
            if vehicle.variant_id: parts.append(vehicle.variant_id.name)
            vehicle.name = " ".join(parts) if parts else vehicle.license_plate

    # Onchanges to clear sub-fields if parent changes (Good UX)
    @api.onchange('brand_id')
    def _onchange_brand(self):
        self.model_id = False

    @api.onchange('model_id')
    def _onchange_model(self):
        self.chassis_id = False
        self.body_style_id = False
        self.variant_id = False


    # fuel_type = fields.Selection(
    #     [
    #         ('petrol', 'Petrol'),
    #         ('diesel', 'Diesel'),
    #         ('hybrid', 'Hybrid'),
    #         ('electric', 'Electric'),
    #         ('cng', 'CNG'),
    #         ('octane', 'Octane'),
    #         ('lpg', 'LPG'),
    #     ],
    #     string='Fuel Type'
    # )


    first_registration = fields.Date(string='First Registration')
    mileage = fields.Integer(string='Mileage')

    # type_code = fields.Char(string='Type Code')
    # master_number = fields.Char(string='Master Number')
    last_service_date = fields.Date(string='Last Service Date')

    vehicle_id = fields.Many2one('vehicle.master', string="Vehicle")


    # Vehicle Photos (Front, Back, Side)
    image_front = fields.Image(string="Front View", max_width=1920, max_height=1080)
    image_back = fields.Image(string="Back View", max_width=1920, max_height=1080)
    image_side = fields.Image(string="Side View", max_width=1920, max_height=1080)

    # 2. Constraint to block PDF and allow only PNG/JPG
    @api.constrains('image_front', 'image_back', 'image_side')
    def _check_image_type(self):
        for record in self:
            for field_name in ['image_front', 'image_back', 'image_side']:
                image_data = record[field_name]
                if image_data:
                    # Decode base64 to check the header
                    decoded_data = base64.b64decode(image_data)
                    extension = imghdr.what(None, h=decoded_data)

                    # imghdr returns 'jpeg' or 'png' for valid images
                    valid_types = ['jpeg', 'png']

                    if extension not in valid_types:
                        raise ValidationError(_(
                            "Invalid file format for %s! Only JPG and PNG are allowed. PDFs are strictly prohibited."
                        ) % record._fields[field_name].string)





    license_plate = fields.Char(string='License Plate', placeholder="e.g. ZH 123456", help="The Swiss cantonal registration plate (Kontrollschild).")
    # vin = fields.Char(string='VIN/Chassis Number', placeholder="17-digit VIN", help="Vehicle Identification Number (Fahrgestellnummer) found on the dash or door pillar.")
    type_code = fields.Char(string='Type Code', placeholder="e.g. 1VC644", help="Swiss Type Approval (Typengenehmigung) found in Box 24 of the grey card.")

    master_number = fields.Char(
        string='Stammnummer',
        help="Format: 000.000.000 (Official Swiss vehicle number)",
        copy=False,
        placeholder='e.g., 123.456.789'
    )

    # 2. Add a constraint to ensure the format is correct (XXX.XXX.XXX)
    @api.constrains('master_number')
    def _check_stammnummer_format(self):
        for record in self:
            if record.master_number:
                # Regex to check for 3 digits, dot, 3 digits, dot, 3 digits
                pattern = r'^\d{3}\.\d{3}\.\d{3}$'
                if not re.match(pattern, record.master_number):
                    raise ValidationError(_(
                        "The Stammnummer (Master Number) must be in the format 000.000.000"
                    ))

    # 3. Clean the input (if user types 618578306, automatically add the dots)
    @api.onchange('master_number')
    def _onchange_master_number(self):
        if self.master_number:
            # Remove everything except numbers
            digits = re.sub(r'\D', '', self.master_number)
            if len(digits) == 9:
                self.master_number = f"{digits[:3]}.{digits[3:6]}.{digits[6:]}"


    _sql_constraints = [
        ('master_number_unique', 'unique(master_number)', 'This Stammnummer already exists in the system!')
    ]

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



    @api.onchange('vin')
    def decode_vin(self):

        if not self.vin:
            return

        params = self.env['ir.config_parameter'].sudo()

        auto_user = params.get_param('vehicle.autoidat_user')
        auto_key = params.get_param('vehicle.autoidat_key')

        if auto_user and auto_key:
            self.decode_autoidat()
        else:
            self.decode_nhtsa()



    @api.constrains('vin')
    def _check_vin(self):
        for rec in self:
            if rec.vin and len(rec.vin) != 17:
                raise ValidationError("VIN must be 17 characters.")


    def decode_nhtsa(self):

        url = f"https://vpic.nhtsa.dot.gov/api/vehicles/decodevin/{self.vin}?format=json"

        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        results = data.get('Results', [])

        def get_value(key):
            for item in results:
                if item['Variable'] == key:
                    return item['Value']
            return False

        self.brand = get_value('Make')
        self.model = get_value('Model')
        self.year = get_value('Model Year')
        self.fuel_type = get_value('Fuel Type - Primary')
        self.transmission = get_value('Transmission Style')



    def decode_autoidat(self):

        params = self.env['ir.config_parameter'].sudo()

        user = params.get_param('vehicle.autoidat_user')
        key = params.get_param('vehicle.autoidat_key')

        url = "https://api.auto-i-dat.com/vehicle"

        payload = {
            "vin": self.vin
        }

        headers = {
            "Authorization": f"Bearer {key}",
            "User": user
        }

        response = requests.post(url, json=payload, headers=headers)

        if response.status_code != 200:
            return

        data = response.json()

        self.brand = data.get('make')
        self.model = data.get('model')
        self.year = data.get('year')
        self.fuel_type = data.get('fuelType')
        self.transmission = data.get('transmission')



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
    ], string="VIN API Provider", default='nhtsa',
       config_parameter='vehicle_master_vin.provider')

    autoidat_api_url = fields.Char(
        string="AUTO-i-DAT API URL",
        config_parameter='vehicle_master_vin.api_url'
    )

    autoidat_api_key = fields.Char(
        string="AUTO-i-DAT API Key",
        config_parameter='vehicle_master_vin.api_key'
    )

    autoidat_api_user = fields.Char(
        string="AUTO-i-DAT API User",
        config_parameter='vehicle_master_vin.api_user'
    )

    autoidat_user = fields.Char(
        string="AUTO-i-DAT API User",
        config_parameter='vehicle.autoidat_user'
    )
    autoidat_key = fields.Char(
        string="AUTO-i-DAT API Key",
        config_parameter='vehicle.autoidat_key'
    )


    def set_values(self):
        super().set_values()
        self.env['ir.config_parameter'].sudo().set_param(
            'vehicle.autoidat_user', self.autoidat_user)
        self.env['ir.config_parameter'].sudo().set_param(
            'vehicle.autoidat_key', self.autoidat_key)


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

    _sql_constraints = [
        ('brand_name_unique', 'unique(name)', 'Brand name must be unique!')
    ]


class VehicleModel(models.Model):
    _name = 'vehicle.model'
    _description = 'Vehicle Model'

    name = fields.Char(string="Model Name", required=True)
    brand_id = fields.Many2one('vehicle.brand', string="Brand", required=True, ondelete='cascade')

    chassis_ids = fields.One2many('vehicle.chassis', 'model_id', string="Chassis Codes")
    body_style_ids = fields.One2many('vehicle.body', 'model_id', string="Body Styles")
    variant_ids = fields.One2many('vehicle.variant', 'model_id', string="Variants")

    _sql_constraints = [
        ('model_brand_unique',
         'unique(name, brand_id)',
         'Model already exists for this brand!')
    ]


class VehicleChassis(models.Model):
    _name = 'vehicle.chassis'
    _description = 'Chassis Code'

    name = fields.Char(string="Chassis Code", required=True)
    # model_id = fields.Many2one('vehicle.model', string="Model") # Linked to Model

    model_id = fields.Many2one('vehicle.model', required=True, ondelete='cascade' )

    _sql_constraints = [
        (
            'chassis_unique',
            'unique(name, model_id)',
            'Chassis already exists for this model!'
        )
    ]

class VehicleBody(models.Model):
    _name = 'vehicle.body'
    _description = 'Body Style'

    name = fields.Char(string="Body Style", required=True)
    # model_id = fields.Many2one('vehicle.model', string="Model") # Linked to Model
    model_id = fields.Many2one('vehicle.model', required=True, ondelete='cascade' )

    _sql_constraints = [
        (
            'body_unique',
            'unique(name, model_id)',
            'Body style already exists for this model!'
        )
    ]


class VehicleVariant(models.Model):
    _name = 'vehicle.variant'
    _description = 'Vehicle Variant'

    name = fields.Char(required=True)
    model_id = fields.Many2one('vehicle.model', required=True, ondelete='cascade' )

    year_from = fields.Integer(string="Year From")
    year_to = fields.Integer(string="Year To")

    _sql_constraints = [
        ('variant_unique',
         'unique(name, model_id)',
         'Variant already exists for this model!')
    ]


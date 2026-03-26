from odoo import models, fields, api, _
from odoo.exceptions import UserError
import base64
import io
import csv
import logging

_logger = logging.getLogger(__name__)


class VehicleImportWizard(models.TransientModel):
    _name = 'vehicle.import.wizard'
    _description = 'Import Vehicles from CSV'

    csv_file = fields.Binary(string="CSV File", required=True)
    csv_filename = fields.Char(string="Filename")
    import_log = fields.Text(string="Import Log", readonly=True)

    def action_import(self):
        """Import vehicles from CSV"""
        self.ensure_one()

        if not self.csv_file:
            raise UserError(_("Please select a CSV file to import."))

        try:
            # Decode CSV content
            csv_data = base64.b64decode(self.csv_file)
            csv_content = csv_data.decode('utf-8-sig')
            csv_file = io.StringIO(csv_content)
            reader = csv.DictReader(csv_file)

            imported = 0
            errors = []
            log_lines = []

            if not reader.fieldnames:
                raise UserError(_("CSV file must have headers."))

            log_lines.append(f"Found columns: {', '.join(reader.fieldnames)}")
            log_lines.append("=" * 50)

            for row_num, row in enumerate(reader, start=2):
                try:
                    vals = self._prepare_vals(row, row_num, log_lines)
                    self._create_or_update_vehicle(vals, row_num, log_lines)
                    imported += 1
                except Exception as e:
                    error_msg = f"Row {row_num}: {str(e)}"
                    errors.append(error_msg)
                    log_lines.append(f"ERROR: {error_msg}")

            # Save log
            self.import_log = "\n".join(log_lines)

            # Show result
            message = f"Successfully imported {imported} vehicles."
            if errors:
                message += f"\nErrors: {len(errors)}"
                message += f"\n\nFirst 5 errors:\n" + "\n".join(errors[:5])

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Import Complete',
                    'message': message,
                    'type': 'success' if not errors else 'warning',
                    'sticky': bool(errors),
                    'next': {'type': 'ir.actions.act_window_close'},
                }
            }

        except Exception as e:
            raise UserError(_("Error processing CSV: %s") % str(e))

    def _prepare_vals(self, row, row_num, log_lines):
        """Prepare values dictionary from CSV row"""
        vals = {}

        # Owner name
        if row.get('owner_name'):
            vals['owner_name'] = row['owner_name'].strip()
            log_lines.append(f"Row {row_num}: Processing owner: {vals['owner_name']}")

        # Handle brand
        if row.get('brand'):
            brand_name = row['brand'].strip()
            brand = self.env['vehicle.brand'].search([
                ('name', '=ilike', brand_name)
            ], limit=1)

            if not brand:
                brand = self.env['vehicle.brand'].create({
                    'name': brand_name.upper()
                })
                log_lines.append(f"Row {row_num}: Created new brand: {brand_name}")

            vals['brand_id'] = brand.id

        # Handle model
        if row.get('model') and vals.get('brand_id'):
            model_name = row['model'].strip()
            model = self.env['vehicle.model'].search([
                ('name', '=ilike', model_name),
                ('brand_id', '=', vals['brand_id'])
            ], limit=1)

            if not model:
                model = self.env['vehicle.model'].create({
                    'name': model_name.upper(),
                    'brand_id': vals['brand_id']
                })
                log_lines.append(f"Row {row_num}: Created new model: {model_name}")

            vals['model_id'] = model.id

        # Map basic fields
        field_mapping = {
            'vin': 'vin',
            'license_plate': 'license_plate',
            'master_number': 'master_number',
            'year': 'year',
            'color': 'color',
            'mileage': 'mileage',
            'fuel_type': 'fuel_type',
            'transmission': 'transmission',
            'engine': 'engine',
            'purchase_price': 'purchase_price',
            'sale_price': 'sale_price',
            'street': 'street',
            'zip': 'zip',
            'city': 'city',
            'telephone': 'telephone',
            'email': 'email',
        }

        for csv_field, model_field in field_mapping.items():
            if row.get(csv_field):
                value = row[csv_field].strip()
                if value:
                    vals[model_field] = value

        # Handle numeric fields
        numeric_fields = ['mileage', 'purchase_price', 'sale_price']
        for field in numeric_fields:
            if field in vals and vals[field]:
                try:
                    vals[field] = float(vals[field])
                except:
                    pass

        return vals

    def _create_or_update_vehicle(self, vals, row_num, log_lines):
        """Create or update vehicle"""
        vehicle = None

        # Check if vehicle exists by VIN
        if vals.get('vin'):
            vehicle = self.env['vehicle.master'].search([
                ('vin', '=', vals['vin'])
            ], limit=1)

        if vehicle:
            vehicle.write(vals)
            log_lines.append(f"Row {row_num}: Updated vehicle: {vals.get('vin', 'N/A')}")
        else:
            self.env['vehicle.master'].create(vals)
            log_lines.append(f"Row {row_num}: Created vehicle: {vals.get('vin', 'N/A')}")

    def action_download_template(self):
        """Download template CSV file"""
        template_content = """owner_name,brand,model,vin,license_plate,master_number,year,color,mileage,fuel_type,transmission,purchase_price,sale_price,street,zip,city,telephone,email
Marcel Egli,Audi,A4,WVWZZZ1KZ9W123456,ZH123456,123.456.789,2020,Black,45000,Diesel,Automatic,35000,45000,Example St. 123,8000,Zurich,+41 44 123 45 67,info@example.com
Hans Müller,BMW,X5,WBA123456789ABC,ZH789012,987.654.321,2021,White,30000,Petrol,Automatic,55000,65000,Main St. 45,8001,Zurich,+41 44 987 65 43,hans@example.com
Peter Meier,Mercedes-Benz,C-Class,WDD123456789DEF,ZH345678,456.789.012,2019,Silver,60000,Diesel,Manual,28000,38000,Street 78,8002,Zurich,+41 44 456 78 90,peter@example.com"""

        attachment = self.env['ir.attachment'].create({
            'name': 'vehicle_import_template.csv',
            'datas': base64.b64encode(template_content.encode('utf-8')),
            'type': 'binary',
            'mimetype': 'text/csv',
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }
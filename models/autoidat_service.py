import requests
from odoo import models
from odoo.exceptions import UserError


class AutoIDATService(models.AbstractModel):

    _name = 'autoidat.service'
    _description = 'AutoIDAT Service'

    def get_vehicle_by_vin(self, vin):

        params = self.env['ir.config_parameter'].sudo()

        api_url = params.get_param('vehicle_master.api_url')
        api_user = params.get_param('vehicle_master.api_user')
        api_key = params.get_param('vehicle_master.api_key')

        if not api_url:
            raise UserError("AutoIDAT API not configured")

        try:

            response = requests.get(
                f"{api_url}/vehicle",
                params={'vin': vin},
                auth=(api_user, api_key),
                timeout=20
            )

            response.raise_for_status()

            return response.json()

        except Exception as e:

            raise UserError(
                f"API connection error: {str(e)}"
            )
from odoo import models, fields


class VehicleBrand(models.Model):
    _name = 'vehicle.brand'
    _description = 'Vehicle Brand'
    _rec_name = 'name'

    name = fields.Char(string='Brand Name', required=True)
    model_ids = fields.One2many('vehicle.model', 'brand_id', string='Models')


class VehicleModel(models.Model):
    _name = 'vehicle.model'
    _description = 'Vehicle Model'
    _rec_name = 'name'

    name = fields.Char(string='Model Name', required=True)
    brand_id = fields.Many2one('vehicle.brand', string='Brand', required=True)

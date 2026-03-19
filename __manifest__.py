{
    'name': 'Vehicle Master',
    'version': '17.0.1.0',
    'category': 'Garage',
    'depends': [
        'base',
        'contacts',
        'mail',
        'sale',
        'sale_management',
        'account',
        'stock',   # ✅ VERY IMPORTANT
        'hr',   # ✅ VERY IMPORTANT
    ],
    'data': [
        'security/ir.model.access.csv',
        # 'views/garage_vehicle_views.xml',
        'views/vehicle_views.xml',
        'views/sale_order_views.xml',
        'views/vehicle_settings.xml',
        # 'views/vehicle_brand_model_views.xml',
        'data/vehicle_master_sequence.xml',
        'data/vehicle_cars_data.xml',
        'data/vehicle_color_data.xml',
        # 'data/vehicle.brand.csv',
    ],

    'external_dependencies': {
            'python': ['google-generativeai'],
        },

    "assets": {
        "web.report_assets_common": [
            "vehicle_master_vin/static/src/report_din5008.scss",
        ],
    },

    'installable': True,
    'application': True,
    # 'post_init_hook': 'generate_vehicle_demo_data',
}

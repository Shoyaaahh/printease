"""
Pricing configuration for PrintEase.

Adjust the numbers below to match Marian's Printing Services' actual price
list — nothing else in the app needs to change. All amounts are in
Philippine Pesos (PHP) by default.
"""

CURRENCY_SYMBOL = '₱'

SERVICE_TYPES = {
    'document_print': 'Normal Print (on paper)',
    'tarpaulin': 'Tarpaulin',
    'shirt_print': 'Shirt Printing',
    'soft_bind': 'Soft Bind',
    'hard_bind': 'Hard Bind',
    'laminate': 'Laminate',
}

PAPER_SIZES = ['Short (8.5x11)', 'A4', 'Long (8.5x13)', 'Legal', 'Custom']
SHIRT_SIZES = ['XS', 'S', 'M', 'L', 'XL', 'XXL']

PRICING = {
    'document_print': {
        'bw_per_page': 2.0,
        'color_per_page': 8.0,
    },
    'tarpaulin': {
        'per_sqft': 15.0,
        'min_charge': 100.0,
    },
    'shirt_print': {
        'per_shirt': 150.0,
    },
    'soft_bind': {
        'base_fee': 40.0,
        'per_page': 2.0,
    },
    'hard_bind': {
        'base_fee': 150.0,
        'per_page': 2.0,
    },
    'laminate': {
        'per_sheet': 10.0,
    },
}

URGENT_SURCHARGE_RATE = 0.20  # +20% on top of the computed base price


def calculate_price(service_type, copies=1, is_colored=False, page_count=None,
                     width_ft=None, height_ft=None, is_urgent=False):
    """Returns an ESTIMATED price (float) for a print request, for the
    customer's reference. Final pricing is always confirmed by the shop
    when the request is accepted."""
    rules = PRICING.get(service_type)
    if not rules:
        return 0.0

    copies = copies or 1
    base = 0.0

    if service_type == 'document_print':
        per_page = rules['color_per_page'] if is_colored else rules['bw_per_page']
        base = per_page * (page_count or 1) * copies

    elif service_type == 'tarpaulin':
        area = max((width_ft or 0) * (height_ft or 0), 0)
        base = max(area * rules['per_sqft'], rules['min_charge']) * copies

    elif service_type == 'shirt_print':
        base = rules['per_shirt'] * copies

    elif service_type in ('soft_bind', 'hard_bind'):
        base = (rules['base_fee'] + rules['per_page'] * (page_count or 1)) * copies

    elif service_type == 'laminate':
        base = rules['per_sheet'] * copies

    if is_urgent:
        base *= (1 + URGENT_SURCHARGE_RATE)

    return round(base, 2)

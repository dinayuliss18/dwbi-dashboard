"""Generate synthetic operational data for an Indonesian online retail store.

The script loads source-system style tables to PostgreSQL schema `raw` and can
also export the generated data to CSV. It intentionally models operational
messiness: skewed product popularity, delayed shipping, cancellations, returns,
vouchers, shipping subsidies, and customer address changes for SCD Type 2.
"""

from __future__ import annotations

import argparse
import os
import random
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd


DEFAULT_MIN_ITEMS = 12_000
DEFAULT_CUSTOMERS = 2_500
DEFAULT_PRODUCTS = 350
DEFAULT_SEED = 20260523


INDONESIA_CITIES = [
    ("Jakarta", "DKI Jakarta", "Java"),
    ("Bogor", "Jawa Barat", "Java"),
    ("Depok", "Jawa Barat", "Java"),
    ("Tangerang", "Banten", "Java"),
    ("Bekasi", "Jawa Barat", "Java"),
    ("Bandung", "Jawa Barat", "Java"),
    ("Cirebon", "Jawa Barat", "Java"),
    ("Semarang", "Jawa Tengah", "Java"),
    ("Surakarta", "Jawa Tengah", "Java"),
    ("Yogyakarta", "DI Yogyakarta", "Java"),
    ("Surabaya", "Jawa Timur", "Java"),
    ("Malang", "Jawa Timur", "Java"),
    ("Denpasar", "Bali", "Bali Nusa Tenggara"),
    ("Mataram", "Nusa Tenggara Barat", "Bali Nusa Tenggara"),
    ("Kupang", "Nusa Tenggara Timur", "Bali Nusa Tenggara"),
    ("Medan", "Sumatera Utara", "Sumatra"),
    ("Padang", "Sumatera Barat", "Sumatra"),
    ("Pekanbaru", "Riau", "Sumatra"),
    ("Batam", "Kepulauan Riau", "Sumatra"),
    ("Jambi", "Jambi", "Sumatra"),
    ("Palembang", "Sumatera Selatan", "Sumatra"),
    ("Bengkulu", "Bengkulu", "Sumatra"),
    ("Bandar Lampung", "Lampung", "Sumatra"),
    ("Pontianak", "Kalimantan Barat", "Kalimantan"),
    ("Palangka Raya", "Kalimantan Tengah", "Kalimantan"),
    ("Banjarmasin", "Kalimantan Selatan", "Kalimantan"),
    ("Samarinda", "Kalimantan Timur", "Kalimantan"),
    ("Balikpapan", "Kalimantan Timur", "Kalimantan"),
    ("Tarakan", "Kalimantan Utara", "Kalimantan"),
    ("Manado", "Sulawesi Utara", "Sulawesi"),
    ("Palu", "Sulawesi Tengah", "Sulawesi"),
    ("Makassar", "Sulawesi Selatan", "Sulawesi"),
    ("Kendari", "Sulawesi Tenggara", "Sulawesi"),
    ("Jayapura", "Papua", "Papua"),
]

CATEGORIES = {
    "Electronics": ["Smartphone", "Audio", "Laptop Accessories", "Wearable"],
    "Fashion": ["Men Apparel", "Women Apparel", "Shoes", "Bags"],
    "Beauty": ["Skincare", "Makeup", "Fragrance", "Hair Care"],
    "Home & Living": ["Kitchen", "Storage", "Bedding", "Decor"],
    "Sports": ["Fitness", "Outdoor", "Cycling", "Yoga"],
    "Books": ["Business", "Technology", "Fiction", "Education"],
    "Mother & Baby": ["Baby Care", "Toys", "Feeding", "Maternity"],
    "Automotive": ["Motorcycle", "Car Accessories", "Tools", "Oils"],
}

PAYMENT_METHODS = [
    ("E-wallet", "Digital wallet", 0.38),
    ("QRIS", "QR payment", 0.28),
    ("COD", "Cash on delivery", 0.19),
    ("Paylater", "Consumer credit", 0.15),
]

SHIPPING_SERVICES = [
    ("JNE", "REG", "Regular", 0.23, 2, 5),
    ("JNE", "YES", "Express", 0.08, 1, 2),
    ("SiCepat", "REG", "Regular", 0.19, 2, 4),
    ("J&T", "EZ", "Regular", 0.18, 2, 5),
    ("AnterAja", "Regular", "Regular", 0.14, 2, 5),
    ("Ninja Xpress", "Standard", "Regular", 0.10, 3, 6),
    ("GrabExpress", "Instant", "Same Day", 0.05, 0, 1),
    ("GoSend", "Instant", "Same Day", 0.03, 0, 1),
]

VOUCHERS = [
    (
        "NO_DISCOUNT",
        "No discount",
        "none",
        "Tidak menggunakan voucher.",
        0,
        0,
        0.00,
    ),
    (
        "CASHBACK_10_MIN_200K",
        "Cashback 10% minimal belanja 200k",
        "cashback",
        "Minimal belanja Rp200.000 mendapat cashback 10% dari total belanja.",
        200_000,
        0,
        0.10,
    ),
    (
        "FREE_SHIPPING_MIN_50K",
        "Free ongkir minimal belanja 50k",
        "shipping_discount",
        "Minimal belanja Rp50.000 mendapat subsidi ongkir.",
        50_000,
        0,
        0.00,
    ),
    (
        "ELECTRONICS_100K",
        "Potongan langsung elektronik 100k",
        "direct_discount",
        "Potongan langsung Rp100.000 hanya untuk barang kategori Electronics.",
        0,
        100_000,
        0.00,
    ),
]


PEAK_SEASON_DATES = [
    # Tahun Baru, Ramadan/Lebaran, Natal, Nyepi, Waisak, Imlek, Idul Adha.
    date(2022, 1, 1),
    date(2022, 2, 1),
    date(2022, 3, 3),
    date(2022, 5, 2),
    date(2022, 5, 16),
    date(2022, 7, 10),
    date(2022, 12, 25),
    date(2023, 1, 1),
    date(2023, 1, 22),
    date(2023, 3, 22),
    date(2023, 4, 22),
    date(2023, 6, 4),
    date(2023, 6, 29),
    date(2023, 12, 25),
    date(2024, 1, 1),
    date(2024, 2, 10),
    date(2024, 3, 11),
    date(2024, 4, 10),
    date(2024, 5, 23),
    date(2024, 6, 17),
    date(2024, 12, 25),
    date(2025, 1, 1),
    date(2025, 1, 29),
    date(2025, 3, 29),
    date(2025, 3, 31),
    date(2025, 5, 12),
    date(2025, 6, 6),
    date(2025, 12, 25),
    date(2026, 1, 1),
]


def money(value) -> int:
    return int(round(float(value)))


def weighted_choice(rows, weight_idx: int):
    return random.choices(rows, weights=[row[weight_idx] for row in rows], k=1)[0]


def fake_instance(seed: int):
    from faker import Faker

    random.seed(seed)
    Faker.seed(seed)
    return Faker(["id_ID", "en_US"])


@dataclass(frozen=True)
class GeneratedData:
    cities: pd.DataFrame
    categories: pd.DataFrame
    products: pd.DataFrame
    payment_methods: pd.DataFrame
    shipping_services: pd.DataFrame
    vouchers: pd.DataFrame
    customer_profile_events: pd.DataFrame
    orders: pd.DataFrame
    order_items: pd.DataFrame
    payments: pd.DataFrame
    shipments: pd.DataFrame
    order_status_events: pd.DataFrame

    def as_dict(self) -> dict[str, pd.DataFrame]:
        return {
            "cities": self.cities,
            "categories": self.categories,
            "products": self.products,
            "payment_methods": self.payment_methods,
            "shipping_services": self.shipping_services,
            "vouchers": self.vouchers,
            "customer_profile_events": self.customer_profile_events,
            "orders": self.orders,
            "order_items": self.order_items,
            "payments": self.payments,
            "shipments": self.shipments,
            "order_status_events": self.order_status_events,
        }


def base_entities(product_count: int, seed: int) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    fake = fake_instance(seed)
    cities = pd.DataFrame(
        [
            {
                "city_id": idx,
                "city_name": city,
                "province": province,
                "region": region,
                "country": "Indonesia",
            }
            for idx, (city, province, region) in enumerate(INDONESIA_CITIES, start=1)
        ]
    )

    category_rows = []
    category_id = 1
    for category, subcategories in CATEGORIES.items():
        for subcategory in subcategories:
            category_rows.append(
                {
                    "category_id": category_id,
                    "category_name": category,
                    "subcategory_name": subcategory,
                    "department": category,
                }
            )
            category_id += 1
    categories = pd.DataFrame(category_rows)

    product_rows = []
    for product_id in range(1, product_count + 1):
        category = categories.sample(1, random_state=random.randint(1, 1_000_000)).iloc[0]
        cat_name = category["category_name"]
        if cat_name == "Electronics":
            price = random.uniform(250_000, 6_500_000)
            margin = random.uniform(0.12, 0.28)
        elif cat_name == "Fashion":
            price = random.uniform(85_000, 900_000)
            margin = random.uniform(0.28, 0.55)
        elif cat_name == "Books":
            price = random.uniform(45_000, 280_000)
            margin = random.uniform(0.18, 0.35)
        else:
            price = random.uniform(60_000, 1_800_000)
            margin = random.uniform(0.18, 0.45)
        standard_price = money(price)
        estimated_unit_cost = money(standard_price * (1.00 - margin))
        product_rows.append(
            {
                "product_id": product_id,
                "sku": f"SKU-{cat_name[:3].upper()}-{product_id:05d}",
                "product_name": f"{fake.word().title()} {category['subcategory_name']}",
                "category_id": int(category["category_id"]),
                "standard_price": standard_price,
                "estimated_unit_cost": estimated_unit_cost,
                "is_active": True,
                "created_at": datetime(2021, 1, 1) + timedelta(days=random.randint(0, 900)),
            }
        )
    products = pd.DataFrame(product_rows)

    payment_methods = pd.DataFrame(
        [
            {"payment_method_id": idx, "payment_method_name": name, "payment_group": group}
            for idx, (name, group, _) in enumerate(PAYMENT_METHODS, start=1)
        ]
    )
    shipping_services = pd.DataFrame(
        [
            {
                "shipping_service_id": idx,
                "shipping_provider": provider,
                "shipping_service": service,
                "service_level": level,
                "min_delivery_days": min_days,
                "max_delivery_days": max_days,
            }
            for idx, (provider, service, level, _, min_days, max_days) in enumerate(SHIPPING_SERVICES, start=1)
        ]
    )
    vouchers = pd.DataFrame(
        [
            {
                "voucher_id": idx,
                "voucher_code": code,
                "voucher_name": name,
                "voucher_type": voucher_type,
                "rule_description": rule_description,
                "min_order_amount": min_order,
                "discount_amount": discount_amount,
                "cashback_rate": cashback_rate,
            }
            for idx, (code, name, voucher_type, rule_description, min_order, discount_amount, cashback_rate) in enumerate(VOUCHERS, start=1)
        ]
    )
    return cities, categories, products, payment_methods, shipping_services, vouchers


def generate_customers(customer_count: int, cities: pd.DataFrame, seed: int, start_at: datetime, end_at: datetime) -> pd.DataFrame:
    fake = fake_instance(seed + 1)
    tiers = ["New", "Regular", "Silver", "Gold", "Platinum"]
    rows = []
    event_id = 1

    for customer_id in range(1, customer_count + 1):
        city = cities.sample(1, weights=[10 if c in {"Jakarta", "Surabaya", "Bandung", "Medan"} else 2 for c in cities["city_name"]]).iloc[0]
        signup_at = start_at - timedelta(days=random.randint(1, 500))
        base = {
            "customer_id": customer_id,
            "full_name": fake.name(),
            "email": fake.unique.email().lower(),
            "gender": random.choice(["Female", "Male"]),
            "birth_date": fake.date_of_birth(minimum_age=18, maximum_age=70),
            "city_id": int(city["city_id"]),
            "loyalty_tier": random.choices(tiers, [45, 30, 15, 8, 2], k=1)[0],
            "marketing_opt_in": random.random() < 0.7,
        }
        rows.append({"customer_profile_event_id": event_id, **base, "effective_at": signup_at, "operation": "insert"})
        event_id += 1

        change_count = int(random.random() < 0.28) + int(random.random() < 0.07)
        for change_idx in range(change_count):
            change_at = start_at + timedelta(days=random.randint(30, max(31, (end_at - start_at).days - 30)))
            if random.random() < 0.65:
                new_city = cities.sample(1).iloc[0]
                base["city_id"] = int(new_city["city_id"])
            if random.random() < 0.50:
                base["loyalty_tier"] = random.choices(tiers, [10, 30, 30, 20, 10], k=1)[0]
            base["marketing_opt_in"] = random.random() < 0.7
            rows.append({"customer_profile_event_id": event_id, **base, "effective_at": change_at + timedelta(seconds=change_idx), "operation": "update"})
            event_id += 1

    return pd.DataFrame(rows).sort_values(["customer_id", "effective_at", "customer_profile_event_id"])


def final_order_status(order_ts: datetime, end_at: datetime) -> tuple[str, str | None]:
    age_days = (end_at - order_ts).days
    if age_days < 3:
        status = random.choices(["placed", "paid", "packed", "cancelled"], [20, 35, 30, 15], k=1)[0]
    elif age_days < 10:
        status = random.choices(["shipped", "delivered", "cancelled", "returned"], [25, 55, 12, 8], k=1)[0]
    else:
        status = random.choices(["delivered", "cancelled", "returned"], [82, 8, 10], k=1)[0]

    cancellation_stage = None
    if status == "cancelled":
        cancellation_stage = random.choices(["placed", "paid", "packed", "shipped"], [35, 30, 25, 10], k=1)[0]
    return status, cancellation_stage


def status_events(order_id: int, order_ts: datetime, final_status: str, cancellation_stage: str | None) -> list[dict]:
    stages = ["placed", "paid", "packed", "shipped", "delivered"]
    rows = []
    current_ts = order_ts
    for stage in stages:
        rows.append({"order_id": order_id, "status": stage, "status_ts": current_ts})
        if final_status == "cancelled" and stage == cancellation_stage:
            rows.append({"order_id": order_id, "status": "cancelled", "status_ts": current_ts + timedelta(minutes=random.randint(10, 360))})
            break
        if stage == final_status:
            break
        if stage == "placed":
            current_ts += timedelta(minutes=random.randint(1, 120))
        elif stage == "paid":
            current_ts += timedelta(hours=random.randint(1, 20))
        elif stage == "packed":
            current_ts += timedelta(hours=random.randint(4, 36))
        elif stage == "shipped":
            current_ts += timedelta(days=random.randint(1, 7))
    if final_status == "returned":
        if rows[-1]["status"] != "delivered":
            rows.append({"order_id": order_id, "status": "delivered", "status_ts": current_ts + timedelta(days=random.randint(1, 6))})
        rows.append({"order_id": order_id, "status": "returned", "status_ts": rows[-1]["status_ts"] + timedelta(days=random.randint(1, 20))})
    return rows


def random_order_timestamp(start_at: datetime, end_at: datetime) -> datetime:
    """Generate timestamps with higher order density around religious holidays."""
    eligible_peaks = [peak for peak in PEAK_SEASON_DATES if start_at.date() <= peak <= end_at.date()]
    if eligible_peaks and random.random() < 0.35:
        peak_date = random.choice(eligible_peaks)
        selected_date = peak_date + timedelta(days=random.randint(-10, 10))
        selected_date = min(max(selected_date, start_at.date()), end_at.date())
        # Evening hours are intentionally heavier for online shopping behavior.
        hour = random.choices(range(24), weights=[2, 1, 1, 1, 1, 2, 3, 4, 4, 3, 3, 4, 5, 4, 4, 5, 6, 8, 10, 11, 10, 8, 5, 3], k=1)[0]
        return datetime.combine(selected_date, datetime.min.time()) + timedelta(
            hours=hour,
            minutes=random.randint(0, 59),
            seconds=random.randint(0, 59),
        )
    return start_at + timedelta(seconds=random.randint(0, int((end_at - start_at).total_seconds())))


def choose_voucher(vouchers: pd.DataFrame, subtotal: int, has_electronics: bool) -> int:
    no_discount_id = int(vouchers.loc[vouchers["voucher_code"] == "NO_DISCOUNT", "voucher_id"].iloc[0])
    candidates = ["NO_DISCOUNT"]
    if subtotal >= 200_000:
        candidates.append("CASHBACK_10_MIN_200K")
    if subtotal >= 50_000:
        candidates.append("FREE_SHIPPING_MIN_50K")
    if has_electronics:
        candidates.append("ELECTRONICS_100K")

    if random.random() > 0.70:
        return no_discount_id

    weights = {
        "NO_DISCOUNT": 20,
        "CASHBACK_10_MIN_200K": 35,
        "FREE_SHIPPING_MIN_50K": 30,
        "ELECTRONICS_100K": 15,
    }
    selected_code = random.choices(candidates, weights=[weights[code] for code in candidates], k=1)[0]
    return int(vouchers.loc[vouchers["voucher_code"] == selected_code, "voucher_id"].iloc[0])


def generate_transactions(
    min_items: int,
    order_count: int | None,
    customers: pd.DataFrame,
    products: pd.DataFrame,
    categories: pd.DataFrame,
    payment_methods: pd.DataFrame,
    shipping_services: pd.DataFrame,
    vouchers: pd.DataFrame,
    start_at: datetime,
    end_at: datetime,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    customer_ids = customers["customer_id"].drop_duplicates().tolist()
    product_weights = [1 / (idx ** 0.85) for idx in range(1, len(products) + 1)]
    product_records = products.sort_values("product_id").to_dict("records")
    voucher_lookup = vouchers.set_index("voucher_id").to_dict("index")
    category_lookup = categories.set_index("category_id")["category_name"].to_dict()

    orders, order_items, payments, shipments, events = [], [], [], [], []
    order_id = item_id = payment_id = shipment_id = event_id = 1
    loaded_at = datetime.utcnow()

    while len(orders) < order_count if order_count is not None else len(order_items) < min_items:
        order_ts = random_order_timestamp(start_at, end_at)
        customer_id = random.choice(customer_ids)
        payment_tuple = weighted_choice(PAYMENT_METHODS, 2)
        payment_method_id = int(payment_methods.loc[payment_methods["payment_method_name"] == payment_tuple[0], "payment_method_id"].iloc[0])
        shipping_tuple = weighted_choice(SHIPPING_SERVICES, 3)
        shipping_service_id = int(
            shipping_services.loc[
                (shipping_services["shipping_provider"] == shipping_tuple[0])
                & (shipping_services["shipping_service"] == shipping_tuple[1]),
                "shipping_service_id",
            ].iloc[0]
        )
        final_status, cancellation_stage = final_order_status(order_ts, end_at)
        item_count = random.choices([1, 2, 3, 4, 5, 6], [38, 27, 17, 10, 5, 3], k=1)[0]
        selected_products = random.choices(product_records, weights=product_weights, k=item_count)
        order_subtotal = 0
        electronics_subtotal = 0

        temp_items = []
        for item_number, product in enumerate(selected_products, start=1):
            quantity = random.choices([1, 2, 3, 4], [64, 24, 9, 3], k=1)[0]
            unit_price = money(product["standard_price"] * random.uniform(0.88, 1.10))
            subtotal = money(unit_price * quantity)
            item_discount = money(subtotal * random.choice([0, 0, 0.03, 0.05, 0.08, 0.10]))
            estimated_cost = money(product["estimated_unit_cost"] * quantity)
            order_subtotal += subtotal
            category_name = category_lookup[int(product["category_id"])]
            if category_name == "Electronics":
                electronics_subtotal += subtotal
            temp_items.append((item_number, product, category_name, quantity, unit_price, subtotal, item_discount, estimated_cost))

        voucher_id = choose_voucher(vouchers, order_subtotal, electronics_subtotal > 0)
        voucher = voucher_lookup[voucher_id]
        base_shipping_fee = money(random.choice([9000, 12000, 15000, 18000, 25000, 35000, 50000]))
        cashback_pool = money(order_subtotal * 0.10) if voucher["voucher_code"] == "CASHBACK_10_MIN_200K" else 0
        electronics_discount_pool = min(100_000, electronics_subtotal) if voucher["voucher_code"] == "ELECTRONICS_100K" else 0
        shipping_subsidy_pool = base_shipping_fee if voucher["voucher_code"] == "FREE_SHIPPING_MIN_50K" else 0

        orders.append(
            {
                "order_id": order_id,
                "order_number": f"ORD-{order_ts:%Y%m%d}-{order_id:08d}",
                "customer_id": customer_id,
                "order_ts": order_ts,
                "order_status": final_status,
                "cancellation_stage": cancellation_stage,
                "payment_method_id": payment_method_id,
                "shipping_service_id": shipping_service_id,
                "voucher_id": voucher_id,
                "sales_channel": "web",
                "currency": "IDR",
                "loaded_at": loaded_at,
            }
        )

        order_total_payment = 0
        for item_number, product, category_name, quantity, unit_price, subtotal, item_discount, estimated_cost in temp_items:
            allocation = subtotal / order_subtotal if order_subtotal else 0
            electronics_allocation = subtotal / electronics_subtotal if electronics_subtotal and category_name == "Electronics" else 0
            voucher_amount = money(cashback_pool * allocation + electronics_discount_pool * electronics_allocation)
            shipping_subsidy = money(shipping_subsidy_pool * allocation)
            total_payment = money(subtotal - item_discount - voucher_amount)
            profit = money(total_payment - estimated_cost - shipping_subsidy)
            order_total_payment += total_payment
            order_items.append(
                {
                    "order_item_id": item_id,
                    "order_id": order_id,
                    "product_id": int(product["product_id"]),
                    "item_number": item_number,
                    "quantity": quantity,
                    "unit_price": unit_price,
                    "subtotal": subtotal,
                    "discount_amount": item_discount,
                    "shipping_subsidy": shipping_subsidy,
                    "voucher_amount": voucher_amount,
                    "total_payment": total_payment,
                    "estimated_cost": estimated_cost,
                    "profit": profit,
                    "is_returned": final_status == "returned",
                    "is_cancelled": final_status == "cancelled",
                    "loaded_at": loaded_at,
                }
            )
            item_id += 1

        status_rows = status_events(order_id, order_ts, final_status, cancellation_stage)
        for row in status_rows:
            events.append({"status_event_id": event_id, **row, "loaded_at": loaded_at})
            event_id += 1

        shipped_ts = next((row["status_ts"] for row in status_rows if row["status"] == "shipped"), None)
        delivered_ts = next((row["status_ts"] for row in status_rows if row["status"] == "delivered"), None)
        is_delayed = False
        if shipped_ts and not delivered_ts and final_status not in {"cancelled"}:
            delivered_ts = shipped_ts + timedelta(days=random.randint(shipping_tuple[4], shipping_tuple[5] + 3))
        if delivered_ts and shipped_ts:
            is_delayed = (delivered_ts - shipped_ts).days > shipping_tuple[5] or random.random() < 0.10
            if is_delayed:
                delivered_ts += timedelta(days=random.randint(1, 5))

        payments.append(
            {
                "payment_id": payment_id,
                "order_id": order_id,
                "payment_ts": order_ts + timedelta(minutes=random.randint(1, 120)),
                "payment_method_id": payment_method_id,
                "payment_status": "cancelled" if final_status == "cancelled" and cancellation_stage == "placed" else ("refunded" if final_status == "returned" else "paid"),
                "payment_amount": money(order_total_payment),
                "transaction_reference": f"PAY-{uuid.uuid4().hex[:16].upper()}",
                "loaded_at": loaded_at,
            }
        )
        payment_id += 1

        shipments.append(
            {
                "shipment_id": shipment_id,
                "order_id": order_id,
                "shipping_service_id": shipping_service_id,
                "checkout_ts": order_ts,
                "shipped_ts": shipped_ts,
                "delivered_ts": delivered_ts,
                "shipping_fee": base_shipping_fee,
                "shipping_subsidy": shipping_subsidy_pool,
                "is_delayed": is_delayed,
                "shipping_status": "cancelled" if final_status == "cancelled" else ("delivered" if delivered_ts else "in_progress"),
                "tracking_number": None if not shipped_ts else f"TRK{random.randint(10_000_000, 99_999_999)}",
                "loaded_at": loaded_at,
            }
        )
        shipment_id += 1
        order_id += 1

    return pd.DataFrame(orders), pd.DataFrame(order_items), pd.DataFrame(payments), pd.DataFrame(shipments), pd.DataFrame(events)


def generate_data(args: argparse.Namespace) -> GeneratedData:
    start_at = datetime.fromisoformat(args.start_date)
    end_at = datetime.fromisoformat(args.end_date) + timedelta(hours=23, minutes=59, seconds=59)
    cities, categories, products, payment_methods, shipping_services, vouchers = base_entities(args.products, args.seed)
    customers = generate_customers(args.customers, cities, args.seed, start_at, end_at)
    orders, items, payments, shipments, events = generate_transactions(
        args.min_items,
        args.orders,
        customers,
        products,
        categories,
        payment_methods,
        shipping_services,
        vouchers,
        start_at,
        end_at,
    )
    return GeneratedData(cities, categories, products, payment_methods, shipping_services, vouchers, customers, orders, items, payments, shipments, events)


def db_connection():
    import psycopg2

    return psycopg2.connect(
        host=os.getenv("DB_HOST", os.getenv("POSTGRES_HOST", "localhost")),
        port=int(os.getenv("DB_PORT", os.getenv("POSTGRES_PORT", "5432"))),
        dbname=os.getenv("DB_NAME", os.getenv("POSTGRES_DB", "retail_dw")),
        user=os.getenv("DB_USER", os.getenv("POSTGRES_USER", "dwbi")),
        password=os.getenv("DB_PASSWORD", os.getenv("POSTGRES_PASSWORD", "dwbi")),
    )


def create_raw_tables(conn) -> None:
    ddl = """
    create schema if not exists raw;

    -- Watermark table: records the last successful seed load so
    -- the incremental pipeline knows which rows are truly new.
    create table if not exists raw._pipeline_watermark (
        table_name   text primary key,
        last_loaded_at timestamp not null default '1970-01-01'
    );

    create table if not exists raw.cities (
        city_id bigint primary key,
        city_name text not null,
        province text not null,
        region text not null,
        country text not null,
        loaded_at timestamp default current_timestamp
    );
    create table if not exists raw.categories (
        category_id bigint primary key,
        category_name text not null,
        subcategory_name text not null,
        department text not null,
        loaded_at timestamp default current_timestamp
    );
    create table if not exists raw.products (
        product_id bigint primary key,
        sku text not null unique,
        product_name text not null,
        category_id bigint not null,
        standard_price bigint not null,
        estimated_unit_cost bigint not null,
        is_active boolean not null,
        created_at timestamp not null,
        loaded_at timestamp default current_timestamp
    );
    create table if not exists raw.payment_methods (
        payment_method_id bigint primary key,
        payment_method_name text not null,
        payment_group text not null,
        loaded_at timestamp default current_timestamp
    );
    create table if not exists raw.shipping_services (
        shipping_service_id bigint primary key,
        shipping_provider text not null,
        shipping_service text not null,
        service_level text not null,
        min_delivery_days integer not null,
        max_delivery_days integer not null,
        loaded_at timestamp default current_timestamp
    );
    create table if not exists raw.vouchers (
        voucher_id bigint primary key,
        voucher_code text not null,
        voucher_name text not null,
        voucher_type text not null,
        rule_description text not null,
        min_order_amount bigint not null,
        discount_amount bigint not null,
        cashback_rate numeric(8,4) not null,
        loaded_at timestamp default current_timestamp
    );
    create table if not exists raw.customer_profile_events (
        customer_profile_event_id bigint primary key,
        customer_id bigint not null,
        full_name text not null,
        email text not null,
        gender text not null,
        birth_date date not null,
        city_id bigint not null,
        loyalty_tier text not null,
        marketing_opt_in boolean not null,
        effective_at timestamp not null,
        operation text not null,
        loaded_at timestamp default current_timestamp
    );
    create table if not exists raw.orders (
        order_id bigint primary key,
        order_number text not null unique,
        customer_id bigint not null,
        order_ts timestamp not null,
        order_status text not null,
        cancellation_stage text,
        payment_method_id bigint not null,
        shipping_service_id bigint not null,
        voucher_id bigint not null,
        sales_channel text not null,
        currency text not null,
        loaded_at timestamp default current_timestamp
    );
    create table if not exists raw.order_items (
        order_item_id bigint primary key,
        order_id bigint not null,
        product_id bigint not null,
        item_number integer not null,
        quantity integer not null,
        unit_price bigint not null,
        subtotal bigint not null,
        discount_amount bigint not null,
        shipping_subsidy bigint not null,
        voucher_amount bigint not null,
        total_payment bigint not null,
        estimated_cost bigint not null,
        profit bigint not null,
        is_returned boolean not null,
        is_cancelled boolean not null,
        loaded_at timestamp default current_timestamp
    );
    create table if not exists raw.payments (
        payment_id bigint primary key,
        order_id bigint not null,
        payment_ts timestamp not null,
        payment_method_id bigint not null,
        payment_status text not null,
        payment_amount bigint not null,
        transaction_reference text not null,
        loaded_at timestamp default current_timestamp
    );
    create table if not exists raw.shipments (
        shipment_id bigint primary key,
        order_id bigint not null,
        shipping_service_id bigint not null,
        checkout_ts timestamp not null,
        shipped_ts timestamp,
        delivered_ts timestamp,
        shipping_fee bigint not null,
        shipping_subsidy bigint not null,
        is_delayed boolean not null,
        shipping_status text not null,
        tracking_number text,
        loaded_at timestamp default current_timestamp
    );
    create table if not exists raw.order_status_events (
        status_event_id bigint primary key,
        order_id bigint not null,
        status text not null,
        status_ts timestamp not null,
        loaded_at timestamp default current_timestamp
    );
    """
    with conn.cursor() as cur:
        cur.execute(ddl)
    conn.commit()



# ---------------------------------------------------------------------------
# Tables that have a natural primary key and should be upserted (idempotent).
# All other tables are transaction tables and use plain INSERT (append-only).
# ---------------------------------------------------------------------------
_UPSERT_TABLES: dict[str, str] = {
    "raw.cities":             "city_id",
    "raw.categories":         "category_id",
    "raw.products":           "product_id",
    "raw.payment_methods":    "payment_method_id",
    "raw.shipping_services":  "shipping_service_id",
    "raw.vouchers":           "voucher_id",
}


def load_dataframe(conn, table: str, df: pd.DataFrame) -> None:
    """Insert rows into *table*.

    Dimension tables (listed in _UPSERT_TABLES) use INSERT … ON CONFLICT DO
    NOTHING so re-running the seed script is always safe.  Transaction tables
    (orders, order_items, payments, shipments, order_status_events,
    customer_profile_events) are plain INSERTs — append-only by design.
    """
    from psycopg2.extras import execute_values

    #  KODE BARU (Mengubah NaT menjadi None/NULL murni)
    values = [tuple(row) for row in df.astype(object).where(pd.notnull(df), None).itertuples(index=False, name=None)]
    if not values:
        return

    columns = ", ".join(df.columns)
    pk = _UPSERT_TABLES.get(table)
    if pk:
        sql = (
            f"insert into {table} ({columns}) values %s "
            f"on conflict ({pk}) do nothing"
        )
    else:
        sql = f"insert into {table} ({columns}) values %s"

    with conn.cursor() as cur:
        execute_values(cur, sql, values, page_size=5000)
    conn.commit()


def _update_watermark(conn, table_name: str, ts: datetime) -> None:
    """Upsert the watermark for *table_name* so the pipeline knows the
    high-water mark of the last successful seed load."""
    with conn.cursor() as cur:
        cur.execute(
            """
            insert into raw._pipeline_watermark (table_name, last_loaded_at)
            values (%s, %s)
            on conflict (table_name) do update
                set last_loaded_at = excluded.last_loaded_at
            """,
            (table_name, ts),
        )
    conn.commit()


def load_to_postgres(data: GeneratedData) -> None:
    with db_connection() as conn:
        create_raw_tables(conn)
        load_order = [
            "cities",
            "categories",
            "products",
            "payment_methods",
            "shipping_services",
            "vouchers",
            "customer_profile_events",
            "orders",
            "order_items",
            "payments",
            "shipments",
            "order_status_events",
        ]
        loaded_at = datetime.utcnow()
        for name in load_order:
            load_dataframe(conn, f"raw.{name}", data.as_dict()[name])
            _update_watermark(conn, name, loaded_at)


def export_csv(data: GeneratedData, output_dir: str) -> None:
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)
    for name, df in data.as_dict().items():
        df.to_csv(path / f"{name}.csv", index=False)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate online retail operational data.")
    parser.add_argument("--min-items", type=int, default=int(os.getenv("MIN_ORDER_ITEMS", DEFAULT_MIN_ITEMS)))
    parser.add_argument("--orders", type=int, default=os.getenv("ORDER_COUNT"))
    parser.add_argument("--customers", type=int, default=int(os.getenv("CUSTOMER_COUNT", DEFAULT_CUSTOMERS)))
    parser.add_argument("--products", type=int, default=int(os.getenv("PRODUCT_COUNT", DEFAULT_PRODUCTS)))
    parser.add_argument("--seed", type=int, default=int(os.getenv("FAKER_SEED", DEFAULT_SEED)))
    parser.add_argument("--start-date", default=os.getenv("DATA_START_DATE", "2022-01-01"))
    parser.add_argument("--end-date", default=os.getenv("DATA_END_DATE", "2025-12-31"))
    parser.add_argument("--export-csv", action="store_true", help="Export generated raw tables to CSV files.")
    parser.add_argument("--csv-dir", default=os.getenv("CSV_EXPORT_DIR", "data/exports"))
    parser.add_argument("--skip-db-load", action="store_true", help="Only generate/export data; do not load PostgreSQL.")
    parser.add_argument(
        "--mode",
        choices=["seed", "append"],
        default=os.getenv("PIPELINE_MODE", "seed"),
        help=(
            "seed   – initial full load (run once).  "
            "append – generate NEW orders only and append them to raw tables; "
            "         --new-orders controls how many orders to add."
        ),
    )
    parser.add_argument(
        "--new-orders",
        type=int,
        default=int(os.getenv("NEW_ORDER_COUNT", "500")),
        help="Number of new orders to generate in append mode (default: 500).",
    )
    return parser.parse_args()


def _max_ids(conn) -> dict[str, int]:
    """Return the current MAX primary-key value for each transaction table so
    the incremental generator can continue the sequence without collisions."""
    queries = {
        "order_id":       "select coalesce(max(order_id), 0) from raw.orders",
        "order_item_id":  "select coalesce(max(order_item_id), 0) from raw.order_items",
        "payment_id":     "select coalesce(max(payment_id), 0) from raw.payments",
        "shipment_id":    "select coalesce(max(shipment_id), 0) from raw.shipments",
        "status_event_id":"select coalesce(max(status_event_id), 0) from raw.order_status_events",
        "customer_event_id": "select coalesce(max(customer_profile_event_id), 0) from raw.customer_profile_events",
    }
    result = {}
    with conn.cursor() as cur:
        for key, sql in queries.items():
            cur.execute(sql)
            result[key] = cur.fetchone()[0]
    return result


def append_new_orders(args: argparse.Namespace) -> None:
    """Generate *args.new_orders* new transaction rows and append them to the
    existing raw tables without touching dimension data.

    The function:
    1. Reads dimension tables from Postgres (so it always uses the real data).
    2. Generates transactions that start after the latest existing order_ts.
    3. Continues primary-key sequences from the current MAX values.
    4. INSERTs only transaction rows (append-only).
    5. Updates the pipeline watermark.
    """
    with db_connection() as conn:
        # ── 1. Load dimension tables from DB ──────────────────────────────
        import pandas.io.sql as psql

        cities            = psql.read_sql("select * from raw.cities", conn)
        categories        = psql.read_sql("select * from raw.categories", conn)
        products          = psql.read_sql("select * from raw.products", conn)
        payment_methods   = psql.read_sql("select * from raw.payment_methods", conn)
        shipping_services = psql.read_sql("select * from raw.shipping_services", conn)
        vouchers          = psql.read_sql("select * from raw.vouchers", conn)
        customers         = psql.read_sql(
            "select distinct on (customer_id) * from raw.customer_profile_events "
            "order by customer_id, effective_at desc",
            conn,
        )

        # ── 2. Determine time window for new orders ───────────────────────
        with conn.cursor() as cur:
            cur.execute("select coalesce(max(order_ts), now() - interval '1 day') from raw.orders")
            latest_order_ts: datetime = cur.fetchone()[0]
        new_start = latest_order_ts + timedelta(seconds=1)
        new_end   = datetime.utcnow()

        # Fix timezone naive vs aware mismatch before comparison
        if hasattr(new_start, 'tzinfo') and new_start.tzinfo is not None:
            new_start = new_start.replace(tzinfo=None)
        if hasattr(new_end, 'tzinfo') and new_end.tzinfo is not None:
            new_end = new_end.replace(tzinfo=None)

        if new_end <= new_start:
            print("No time window available for new orders — skipping append.")
            return

        # ── 3. Get current PK offsets ─────────────────────────────────────
        max_ids = _max_ids(conn)

        # ── 4. Generate transactions in the new window ────────────────────
        random.seed(args.seed + max_ids["order_id"])  # deterministic but distinct

        orders_rows, items_rows, payments_rows, shipments_rows, events_rows = [], [], [], [], []
        order_id    = max_ids["order_id"]       + 1
        item_id     = max_ids["order_item_id"]  + 1
        payment_id  = max_ids["payment_id"]     + 1
        shipment_id = max_ids["shipment_id"]    + 1
        event_id    = max_ids["status_event_id"]+ 1
        loaded_at   = datetime.utcnow()

        product_weights  = [1 / (idx ** 0.85) for idx in range(1, len(products) + 1)]
        product_records  = products.sort_values("product_id").to_dict("records")
        voucher_lookup   = vouchers.set_index("voucher_id").to_dict("index")
        category_lookup  = categories.set_index("category_id")["category_name"].to_dict()
        customer_ids     = customers["customer_id"].tolist()

        for _ in range(args.new_orders):
            order_ts            = random_order_timestamp(new_start, new_end)
            customer_id         = random.choice(customer_ids)
            payment_tuple       = weighted_choice(PAYMENT_METHODS, 2)
            payment_method_id   = int(payment_methods.loc[
                payment_methods["payment_method_name"] == payment_tuple[0], "payment_method_id"
            ].iloc[0])
            shipping_tuple      = weighted_choice(SHIPPING_SERVICES, 3)
            shipping_service_id = int(shipping_services.loc[
                (shipping_services["shipping_provider"] == shipping_tuple[0])
                & (shipping_services["shipping_service"] == shipping_tuple[1]),
                "shipping_service_id",
            ].iloc[0])

            final_status, cancellation_stage = final_order_status(order_ts, new_end)
            item_count       = random.choices([1, 2, 3, 4, 5, 6], [38, 27, 17, 10, 5, 3], k=1)[0]
            selected_products = random.choices(product_records, weights=product_weights, k=item_count)
            order_subtotal   = 0
            electronics_subtotal = 0
            temp_items       = []

            for item_number, product in enumerate(selected_products, start=1):
                quantity       = random.choices([1, 2, 3, 4], [64, 24, 9, 3], k=1)[0]
                unit_price     = money(product["standard_price"] * random.uniform(0.88, 1.10))
                subtotal       = money(unit_price * quantity)
                item_discount  = money(subtotal * random.choice([0, 0, 0.03, 0.05, 0.08, 0.10]))
                estimated_cost = money(product["estimated_unit_cost"] * quantity)
                order_subtotal += subtotal
                cat_name = category_lookup[int(product["category_id"])]
                if cat_name == "Electronics":
                    electronics_subtotal += subtotal
                temp_items.append((item_number, product, cat_name, quantity, unit_price, subtotal, item_discount, estimated_cost))

            voucher_id        = choose_voucher(vouchers, order_subtotal, electronics_subtotal > 0)
            voucher           = voucher_lookup[voucher_id]
            base_shipping_fee = money(random.choice([9000, 12000, 15000, 18000, 25000, 35000, 50000]))
            cashback_pool     = money(order_subtotal * 0.10) if voucher["voucher_code"] == "CASHBACK_10_MIN_200K" else 0
            electronics_discount_pool = min(100_000, electronics_subtotal) if voucher["voucher_code"] == "ELECTRONICS_100K" else 0
            shipping_subsidy_pool     = base_shipping_fee if voucher["voucher_code"] == "FREE_SHIPPING_MIN_50K" else 0

            orders_rows.append({
                "order_id": order_id,
                "order_number": f"ORD-{order_ts:%Y%m%d}-{order_id:08d}",
                "customer_id": customer_id,
                "order_ts": order_ts,
                "order_status": final_status,
                "cancellation_stage": cancellation_stage,
                "payment_method_id": payment_method_id,
                "shipping_service_id": shipping_service_id,
                "voucher_id": voucher_id,
                "sales_channel": "web",
                "currency": "IDR",
                "loaded_at": loaded_at,
            })

            order_total_payment = 0
            for item_number, product, cat_name, quantity, unit_price, subtotal, item_discount, estimated_cost in temp_items:
                allocation          = subtotal / order_subtotal if order_subtotal else 0
                electronics_alloc   = subtotal / electronics_subtotal if electronics_subtotal and cat_name == "Electronics" else 0
                voucher_amount      = money(cashback_pool * allocation + electronics_discount_pool * electronics_alloc)
                shipping_subsidy    = money(shipping_subsidy_pool * allocation)
                total_payment       = money(subtotal - item_discount - voucher_amount)
                profit              = money(total_payment - estimated_cost - shipping_subsidy)
                order_total_payment += total_payment
                items_rows.append({
                    "order_item_id":    item_id,
                    "order_id":         order_id,
                    "product_id":       int(product["product_id"]),
                    "item_number":      item_number,
                    "quantity":         quantity,
                    "unit_price":       unit_price,
                    "subtotal":         subtotal,
                    "discount_amount":  item_discount,
                    "shipping_subsidy": shipping_subsidy,
                    "voucher_amount":   voucher_amount,
                    "total_payment":    total_payment,
                    "estimated_cost":   estimated_cost,
                    "profit":           profit,
                    "is_returned":      final_status == "returned",
                    "is_cancelled":     final_status == "cancelled",
                    "loaded_at":        loaded_at,
                })
                item_id += 1

            st_rows = status_events(order_id, order_ts, final_status, cancellation_stage)
            for row in st_rows:
                events_rows.append({"status_event_id": event_id, **row, "loaded_at": loaded_at})
                event_id += 1

            shipped_ts   = next((r["status_ts"] for r in st_rows if r["status"] == "shipped"), None)
            delivered_ts = next((r["status_ts"] for r in st_rows if r["status"] == "delivered"), None)
            is_delayed   = False
            if shipped_ts and not delivered_ts and final_status not in {"cancelled"}:
                delivered_ts = shipped_ts + timedelta(days=random.randint(shipping_tuple[4], shipping_tuple[5] + 3))
            if delivered_ts and shipped_ts:
                is_delayed = (delivered_ts - shipped_ts).days > shipping_tuple[5] or random.random() < 0.10
                if is_delayed:
                    delivered_ts += timedelta(days=random.randint(1, 5))

            payments_rows.append({
                "payment_id":            payment_id,
                "order_id":              order_id,
                "payment_ts":            order_ts + timedelta(minutes=random.randint(1, 120)),
                "payment_method_id":     payment_method_id,
                "payment_status":        ("cancelled" if final_status == "cancelled" and cancellation_stage == "placed"
                                          else ("refunded" if final_status == "returned" else "paid")),
                "payment_amount":        money(order_total_payment),
                "transaction_reference": f"PAY-{uuid.uuid4().hex[:16].upper()}",
                "loaded_at":             loaded_at,
            })
            payment_id += 1

            shipments_rows.append({
                "shipment_id":       shipment_id,
                "order_id":          order_id,
                "shipping_service_id": shipping_service_id,
                "checkout_ts":       order_ts,
                "shipped_ts":        shipped_ts,
                "delivered_ts":      delivered_ts,
                "shipping_fee":      base_shipping_fee,
                "shipping_subsidy":  shipping_subsidy_pool,
                "is_delayed":        is_delayed,
                "shipping_status":   ("cancelled" if final_status == "cancelled"
                                      else ("delivered" if delivered_ts else "in_progress")),
                "tracking_number":   None if not shipped_ts else f"TRK{random.randint(10_000_000, 99_999_999)}",
                "loaded_at":         loaded_at,
            })
            shipment_id += 1
            order_id    += 1

        # ── 5. Append to Postgres ─────────────────────────────────────────
        for table, rows in [
            ("raw.orders",              orders_rows),
            ("raw.order_items",         items_rows),
            ("raw.payments",            payments_rows),
            ("raw.shipments",           shipments_rows),
            ("raw.order_status_events", events_rows),
        ]:
            load_dataframe(conn, table, pd.DataFrame(rows))
            _update_watermark(conn, table.removeprefix("raw."), loaded_at)

    print(
        f"[append] Inserted {len(orders_rows)} new orders, "
        f"{len(items_rows)} items, window {new_start:%Y-%m-%d %H:%M} → {new_end:%Y-%m-%d %H:%M}."
    )


def main() -> None:
    args = parse_args()

    if args.mode == "append":
        # ── INCREMENTAL MODE ──────────────────────────────────────────────
        # Only appends new transaction rows; skips full data generation.
        if not args.skip_db_load:
            append_new_orders(args)
        else:
            print("--skip-db-load set with --mode=append: nothing to do.")
        return

    # ── SEED MODE (default) ───────────────────────────────────────────────
    args.orders = int(args.orders) if args.orders not in (None, "") else None
    data = generate_data(args)
    if args.export_csv:
        export_csv(data, args.csv_dir)
    if not args.skip_db_load:
        load_to_postgres(data)
    print(
        "Generated data: "
        f"{len(data.orders)} orders, {len(data.order_items)} order items, "
        f"{len(data.customer_profile_events)} customer SCD events, "
        f"{len(data.products)} products, {len(data.cities)} cities."
    )


if __name__ == "__main__":
    main()

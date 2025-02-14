import numpy as np


def save_as_npy(observation):
    output = [
        {
            "rows": order.order_coordinates.rows,
            "columns": order.order_coordinates.columns,
            "wavelength": order.wavelength,
            "intensity": order.intensity,
            "normalized_intensity": order.normalized_intensity,
        }
        for order in observation.orders
    ]
    npy_file = f"{observation.fits_file.split('.fits')[0]}.npy"
    print(f"Saving {npy_file}...")
    np.save(npy_file, output)


def save_comp_as_npy(comp):
    output = {
        "orders": [
            {
                "rows": order.order_coordinates.rows,
                "columns": order.order_coordinates.columns,
                "wavelength": order.wavelength,
                "intensity": order.intensity,
            }
            for order in comp.orders
        ],
        "raw_data": comp.raw_data,
    }
    npy_file = input("Enter output .npy file: ")
    np.save(npy_file, output)

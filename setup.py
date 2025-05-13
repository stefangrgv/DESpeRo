from setuptools import find_packages, setup

setup(
    name="DESpeRo",
    version="1.0",
    packages=find_packages(),
    install_requires=[
        "numpy==1.26.4",
        "astropy==6.0.0",
        "astroscrappy==1.2.0",
        "astropy-iers-data==0.2024.3.18.0.29.47",
        "scipy==1.15.1",
    ],
)

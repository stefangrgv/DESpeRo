from setuptools import find_packages, setup

setup(
    name="ESpeRo DRS",
    version="1.0",
    packages=find_packages(),
    install_requires=[
        "numpy==1.26.4",
        "astropy==6.0.0",
        "astroscrappy==1.2.0",
        "astropy-iers-data==0.2024.3.18.0.29.47",
        "matplotlib==3.8.3",
        "pyraf==2.2.2",
        "scipy==1.15.1",
        "python-dotenv==1.0.1",
    ],
)

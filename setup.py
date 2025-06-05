from setuptools import setup, find_packages

setup(
    name="rm-node",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "click>=7.0",
        "paho-mqtt>=1.5.0",
        "AWSIoTPythonSDK>=1.5.0"
    ],
    entry_points={
        'console_scripts': [
            'rm-node=mqtt_cli.cli:cli',
        ],
    },
)

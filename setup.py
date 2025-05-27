from setuptools import setup, find_packages

setup(
    name="mqtt_cli",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "click>=8.0.0",
        "paho-mqtt>=1.5.0",
        "AWSIoTPythonSDK>=1.4.0"
    ],
    entry_points={
        'console_scripts': [
            'mqtt-cli=mqtt_cli.cli:cli',
        ],
    },
)
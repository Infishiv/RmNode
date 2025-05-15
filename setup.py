from setuptools import setup, find_packages

setup(
    name="mqtt_cli",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        'click',
        'AWSIoTPythonSDK',
    ],
    entry_points={
        'console_scripts': [
            'mqtt-cli = mqtt_cli.cli:cli',
        ],
    },
)
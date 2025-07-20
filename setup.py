from setuptools import setup, find_packages

setup(
    name='fracmaster_toolbox',
    version='1.5.0',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'PyQt5',
        'pandas',
        'openpyxl',
        'jsonschema'  # Add more here if needed
    ],
    entry_points={
        'console_scripts': [
            'fracmaster=fracmaster_toolbox.ui.main_gui:main'
        ]
    },
    author='Zach Calderone',
    description='FracMaster Toolbox for frac job setup, data parsing, and tool integration',
    license='MIT',
    keywords='frac toolbox automation oilgas',
    classifiers=[
        'Programming Language :: Python :: 3',
        'Operating System :: OS Independent',
    ],
)

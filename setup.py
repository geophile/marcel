import setuptools

with open("README.md", "r") as readme:
    long_description = readme.read()

setuptools.setup(
    name='marcel',  
    version='0.6',
    scripts=['marcel'] ,
    author='Jack Orenstein',
    author_email='jao@geophile.com',
    description='A modern shell',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/geophile/marcel',
    packages=setuptools.find_packages('./src'),
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: GPLv3',
        'Operating System :: OS Independent',
    ])

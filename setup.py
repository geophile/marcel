import setuptools

import marcel.version

with open("README.md", "r") as readme:
    long_description = readme.read()

setuptools.setup(
    name='marcel',  
    version=marcel.version.VERSION,
    author='Jack Orenstein',
    author_email='jao@geophile.com',
    description='A modern shell',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/geophile/marcel',
    packages=setuptools.find_packages('.'),
    scripts=['bin/marcel', 'bin/farcel.py'] ,
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Operating System :: POSIX :: Linux'
    ],
    python_requires='>=3.7'
)

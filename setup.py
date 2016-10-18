
from setuptools import find_packages, setup


version = open('facsimile/VERSION').read().strip()
requirements = open('facsimile/requirements.txt').read().split("\n")
test_requirements = open('facsimile/requirements-test.txt').read().split("\n")


setup(
    name='pybird',
    version=version,
    author='20C',
    author_email='code@20c.com',
    description='BIRD interface handler for Python',
    long_description='',
    license='LICENSE.txt',
    classifiers=[
        'Development Status :: 4 - Beta',
        'License :: OSI Approved :: Apache Software License',
    ],
    packages = find_packages(),
    include_package_data=True,
    url='https://github.com/20c/pybird',
    download_url='https://github.com/20c/pybird/%s' % version,

    install_requires=requirements,
    test_requires=test_requirements,

    zip_safe=True
)

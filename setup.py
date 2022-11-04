from setuptools import setup, find_packages

setup(
    name='qtile-extras',
    packages=find_packages(exclude=["test*"]),
    include_package_data=True,
    setup_requires=["setuptools_scm"],
    use_scm_version=True,
    description='Extra items for qtile that are unlikely to be maintained in the main repo.',
    author='elParaguayo',
    url='https://github.com/elparaguayo/qtile-extras',
    license='MIT',
)

import os
from setuptools import setup, find_packages
from setuptools.command.develop import develop as _develop

HERE = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(HERE, 'README.rst')).read()
CHANGES = open(os.path.join(HERE, 'CHANGES.rst')).read()


REQUIRES = [
    'alembic',                          # Database table upgrades
    'humanize',                         # human readable measurements

    'occams',
    'occams_datastore',                 # EAV
    'occams_roster',
    'occams_forms',                     # EAV form renderer
]

EXTRAS = {
    'test': [
        'nose',
        'nose-testconfig',
        'coverage',
        'WebTest',
        'beautifulsoup4',
        'mock',
        'ddt'],
}


def get_version():
    """
    Generates python version from projects git tag
    """
    import os
    from subprocess import Popen, PIPE
    import sys
    here = os.path.abspath(os.path.dirname(__file__))
    version_file = os.path.join(here, 'VERSION')

    # read fallback file
    try:
        with open(version_file, 'r+') as fp:
            version_txt = fp.read().strip()
    except:
        version_txt = None

    # read git version (if available)
    try:
        version_git = (
            Popen(['git', 'describe'], stdout=PIPE, stderr=PIPE, cwd=here)
            .communicate()[0]
            .strip()
            .decode(sys.getdefaultencoding()))
    except:
        version_git = None

    version = version_git or version_txt or '0.0.0'

    # update fallback file if necessary
    if version != version_txt:
        with open(version_file, 'w') as fp:
            fp.write(version)

    return version


class _custom_develop(_develop):
    def run(self):
        _develop.run(self)
        self.execute(_post_develop, [], msg="Running post-develop task")


def _post_develop():
    from subprocess import call
    call(['bower', 'install'], cwd=HERE)


setup(
    name='occams_studies',
    version=get_version(),
    description='occams_studies',
    long_description=README + '\n\n' + CHANGES,
    classifiers=[
        "Programming Language :: Python",
        "Framework :: Pyramid",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
    ],
    author='UCSD BIT Core Team',
    author_email='bitcore@ucsd.edu',
    url='https://bitbutcket.org/ucsdbitcore/occams_studies',
    keywords='web wsgi bfg pylons pyramid',
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    install_requires=REQUIRES,
    extras_require=EXTRAS,
    tests_require=EXTRAS['test'],
    test_suite='nose.collector',
    cmdclass={'develop': _custom_develop},
    entry_points="""\
    [console_scripts]
    os_initdb = occams_studies.scripts.initdb:main
    os_export = occams_studies.scripts.export:main
    """,
)

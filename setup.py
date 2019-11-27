from setuptools import setup, find_packages
import subprocess


def git_version(fallback):
    try:
        version = subprocess.check_output('git describe --tags --match v[0-9].[0-9]*'.split()).strip()
        return version[1:] if version.startswith('v') else version
    except Exception as e:
        print(e)
        return fallback

setup(
    name='prom_redis_exporter',
    version=git_version('0.3.0'),
    author='Felix Ruess',
    author_email='felix.ruess@roboception.de',
    classifieres=[
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3'
        ],
    packages=find_packages(),
    install_requires=['prometheus_client', 'pyyaml', 'redis'],
    entry_points={
        'console_scripts': [
            "prom-redis-exporter = prom_redis_exporter.prom_redis_exporter:main"
        ],
    }
)

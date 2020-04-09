from setuptools import setup

setup(
    name='zubr',
    version='0.2.2',
    description='Zubr exchange SDK',
    long_description=open('README.md', 'r').read(),
    long_description_content_type='text/markdown',
    url='http://github.com/zubr/sdk',
    author='Zubr Exchange Developers',
    author_email='developer@zubr.io',
    license='MIT',
    packages=[
        'zubr',
    ],
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires=">=3.6",
    install_requires=[
        'websocket-client==0.57.0'
    ],
)
